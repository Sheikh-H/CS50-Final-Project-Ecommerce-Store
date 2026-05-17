from flask import Flask, render_template, redirect, url_for, session, request, flash
import os
from datetime import *
import argon2
import sqlite3
from helpers import *
from flask_session import Session
from dotenv import load_dotenv
import secrets
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import stripe
import shutil

# if not os.path.exists("/data/shop.db"):
#     shutil.copy("instance/shop.db", "/data/shop.db")


load_dotenv()

app = Flask(__name__)

date_now = date_time()


stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")

# This is for uploading all images like product images which are then pulled from online source allowing for admin users to create and add new products
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


# this is cookies and cache control, it allows for the website to always keep them clear and load the page from server each time (useful for small web applications)
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# This is for session management and ensuring a timelimit of user inactivity on browser or once logged in.
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
)
# This is the type of session (i would still wnat to practice using these a little as there are signed and unsigned versions and depending on what sort of application being developed each has its own pros and cons)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.secret_key = os.environ.get("SECRET_KEY")


@app.route("/")
def home():
    title = "Home Page"
    return render_template("pages/home.html", title=title)


@app.route("/order_details/<int:order_id>", methods=["GET", "POST"])
@login_required
def order_details(order_id):
    title = "Order History"
    user_id = session["user_id"]
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        """SELECT * FROM users WHERE user_id = ?;""",
        (user_id,),
    )
    user = cursor.fetchone()
    connection.close()
    order = order_details_function(order_id)
    return render_template(
        "pages/customer/order_info.html", title=title, user=user, order=order
    )


@app.route("/order_history", methods=["GET", "POST"])
@login_required
def order_history():
    title = "Order History"
    user_id = session["user_id"]
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        """SELECT * FROM users WHERE user_id = ?;""",
        (user_id,),
    )
    user = cursor.fetchone()

    connection.close()
    orders = order_history_function(user_id)
    return render_template(
        "pages/customer/orders.html", title=title, orders=orders, user=user
    )


@app.route("/success")
@login_required
def success():
    order_id = request.args.get("session_id")

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE orders
        SET order_status = 'paid',
            payment_status = 'paid',
            paid_at = datetime('now')
        WHERE order_id = ?
    """,
        (order_id,),
    )

    connection.commit()
    connection.close()

    session.pop("cart", None)

    flash("Payment successful — order placed.")
    return redirect(url_for("account"))


@app.route("/cancel")
@login_required
def cancel():
    flash("Payment unsuccessful, order not placed.")
    return redirect(url_for("account"))


@app.route("/create_checkout_session", methods=["POST"])
@login_required
def create_checkout_session():
    cart = session.get("cart", {})

    if not cart:
        flash("Cart is empty.")
        return redirect(url_for("cart"))

    connection = connect_db()
    cursor = connection.cursor()

    total = sum(item["price"] * item["quantity"] for item in cart.values())

    # 1. create order FIRST
    cursor.execute(
        """
        INSERT INTO orders (
            user_id,
            order_total_price,
            order_status,
            order_created_at
        )
        VALUES (?, ?, ?, datetime('now'))
    """,
        (session["user_id"], total, "pending"),
    )

    order_id = cursor.lastrowid

    # 2. store order items immediately (optional but recommended)
    for item in cart.values():
        cursor.execute(
            """
            INSERT INTO order_items (
                order_id,
                product_id,
                order_items_qty,
                order_items_price
            )
            VALUES (?, ?, ?, ?)
        """,
            (order_id, item["product_id"], item["quantity"], item["price"]),
        )

    connection.commit()
    connection.close()

    # 3. create Stripe session
    line_items = []
    for item in cart.values():
        line_items.append(
            {
                "price_data": {
                    "currency": "gbp",
                    "product_data": {"name": item["product_name"]},
                    "unit_amount": int(item["price"] * 100),
                },
                "quantity": item["quantity"],
            }
        )

    stripe_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=f"{BASE_URL}/success?session_id={order_id}",
        cancel_url=f"{BASE_URL}/cart",
    )

    # 4. store stripe session id in DB
    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE orders
        SET stripe_session_id = ?
        WHERE order_id = ?
    """,
        (stripe_session.id, order_id),
    )

    connection.commit()
    connection.close()

    return redirect(stripe_session.url)


@app.route("/add_to_cart/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """ SELECT * FROM products JOIN product_images ON products.product_id = product_images.product_id AND product_images.is_primary = 1 WHERE products.product_id = ?;""",
        (product_id,),
    )

    product = cursor.fetchone()
    connection.close()

    if not product:
        return "Product Not Found", 404

    if "cart" not in session:
        session["cart"] = {}

    cart = session["cart"]

    quantity = request.form.get("quantity", type=int, default=1)

    try:
        quantity = int(quantity)
    except ValueError:
        quantity = 1

    if quantity < 1:
        quantity = 1

    product_id_str = str(product_id)

    if product_id_str in cart:
        cart[product_id_str]["quantity"] += quantity
    else:
        cart[product_id_str] = {
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "quantity": quantity,
            "image_url": product["image_url"],
            "price": product["product_price"],
        }

    session["cart"] = cart
    session.modified = True

    return redirect(url_for("cart"))


@app.route("/cart", methods=["GET", "POST"])
@login_required
def cart():
    title = "Shopping Cart"
    cart = session.get("cart", {}).values()
    cart_total = 0
    for product in cart:
        cart_total += product["price"] * product["quantity"]
    return render_template(
        "pages/cart.html", title=title, cart=cart, cart_total=cart_total
    )


@app.route("/product_info/<int:product_id>", methods=["GET", "POST"])
def product_page(product_id):
    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """SELECT * FROM products WHERE product_id = ?;""",
        (product_id,),
    )

    product = cursor.fetchone()

    cursor.execute(
        """ SELECT image_url FROM product_images WHERE product_id = ?;""",
        (product_id,),
    )

    images = cursor.fetchall()

    connection.close()

    title = product["product_name"]

    return render_template(
        "pages/product_page.html", product=product, images=images, title=title
    )


@app.route("/all_products", methods=["GET", "POST"])
def all_products():
    title = "All products"
    success, products = load_products()
    return render_template("pages/all_products.html", title=title, products=products)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if session.get("admin_id"):
        return redirect(url_for("dashboard"))
    title = "Admin Login"
    message = ""
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        admin, error = admin_login_function(username, password)
        if admin:
            session.clear()
            session.modified = True
            session["admin_id"] = admin["admin_id"]
            session["admin_role"] = admin["role"]
            session.permanent = True
            return redirect(url_for("dashboard"))
        message = error
    return render_template("pages/admin/admin_login.html", title=title, message=message)


@app.route("/add_admin", methods=["GET", "POST"])
@admin_required
def add_admin():
    title = "Add new admin"
    message = ""
    if session["admin_role"] != "owner":
        message = "Restricted Access"
    if request.method == "POST":
        role = request.form.get("role").strip().lower()
        name = request.form.get("name").strip()
        username = request.form.get("username").strip().lower()
        password = request.form.get("password").strip()
        success, message = add_admin_function(role, name, username, password)
    return render_template("pages/admin/add_admin.html", title=title, message=message)


@app.route("/modify_admins", methods=["GET", "POST"])
@admin_required
def modify_admins():
    message = ""
    title = "Modify Admin"
    if session["admin_role"] != "owner":
        message = "Restricted Access"
    admins = existing_admins()
    if request.method == "POST":
        admin_id = request.form.get("admin_id")
        name = request.form.get("name").title().strip()
        role = request.form.get("role").lower()
        password = request.form.get("password", "").strip()
        success, message = update_admin(admin_id, name, role, password)
    return render_template(
        "pages/admin/modify_admin.html", title=title, admins=admins, message=message
    )


@app.route("/modify_customer", methods=["GET", "POST"])
@admin_required
def modify_customers():
    message = ""
    title = "Modify customers"
    success, customers = existing_customers()
    if request.method == "POST":
        user_id = request.form.get("user_id")
        fname = request.form.get("firstname").strip().title()
        sname = request.form.get("surname").strip().title()
        email = request.form.get("email").strip()
        password = request.form.get("password", "").strip()
        address = request.form.get("address").strip()
        success, message = update_customer(
            user_id, fname, sname, email, password, address
        )
    return render_template(
        "pages/admin/modify_customers.html",
        title=title,
        customers=customers,
        message=message,
    )


@app.route("/update_cart/<int:product_id>", methods=["POST"])
@login_required
def update_cart(product_id):
    cart = session.get("cart", {})
    quantity = request.form.get("quantity", type=int)
    product_id = str(product_id)
    if product_id in cart:
        cart[product_id]["quantity"] = quantity
    session["cart"] = cart
    session.modified = True
    return redirect(url_for("cart"))


@app.route("/delete_cart_item/<int:product_id>", methods=["POST"])
@login_required
def delete_cart_item(product_id):
    cart = session.get("cart", {})
    product_id = str(product_id)
    if product_id in cart:
        cart.pop(product_id)
    session["cart"] = cart
    session.modified = True
    return redirect(url_for("cart"))


# This function was built with the help of AI
@app.route("/delete_a_product/<int:product_id>", methods=["POST"])
@admin_required
def delete_product(product_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        """DELETE FROM products WHERE product_id = ?;""",
        (product_id,),
    )
    connection.commit()
    connection.close()
    return redirect(url_for("modify_products"))


@app.route("/delete_image/<int:product_id>/<int:image_id>", methods=["POST"])
@admin_required
def delete_image(product_id, image_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        """DELETE FROM product_images WHERE image_id = ?;""",
        (image_id,),
    )
    connection.commit()
    connection.close()
    return redirect(url_for("modify_a_product", product_id=product_id))


@app.route("/add_new_products", methods=["GET", "POST"])
@admin_required
def add_new_products():
    title = "Add new products"
    message = ""
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        gender = request.form.get("gender")
        category = request.form.get("category")
        price = request.form.get("price")
        brand = request.form.get("brand")
        qty = request.form.get("quantity")
        images = request.files.getlist("images")
        valid_images = [image for image in images if image.filename != ""]
        if not valid_images:
            message = "Please insert at least one image"
            title = "Add new products"
            return render_template(
                "pages/admin/add_new_products.html", title=title, message=message
            )
        success, message = add_product(
            name,
            description,
            gender,
            category,
            price,
            brand,
            qty,
            images,
        )
    return render_template(
        "pages/admin/add_new_products.html", title=title, message=message
    )


@app.route("/modify_products/<int:product_id>", methods=["GET", "POST"])
@admin_required
def modify_a_product(product_id):
    message = ""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(""" SELECT * FROM products WHERE product_id = ?;""", (product_id,))
    product = cursor.fetchone()
    cursor.execute(
        """ SELECT * FROM product_images WHERE product_id = ?;""", (product_id,)
    )
    images = cursor.fetchall()
    title = f"Modify {product['product_name']}"
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        category = request.form.get("category")
        gender = request.form.get("gender")
        price = request.form.get("price")
        brand = request.form.get("brand")
        qty = request.form.get("quantity")
        primary = request.form.get("is_primary")
        success, message = update_product(
            name,
            description,
            price,
            category,
            brand,
            qty,
            gender,
            product_id,
        )

        if primary:
            primary = int(primary)
            cursor.execute(
                """UPDATE product_images SET is_primary = 0 WHERE product_id = ?;""",
                (product_id,),
            )
            cursor.execute(
                """UPDATE product_images SET is_primary = 1 WHERE product_id = ? AND image_id = ?;""",
                (
                    product_id,
                    primary,
                ),
            )
        new_images = request.files.getlist("images")
        valid_images = [image for image in new_images if image.filename != ""]
        if valid_images:
            for image in valid_images:
                upload = cloudinary.uploader.upload(image, folder="MONO_Products")
                image_url = upload["secure_url"]
                cursor.execute(
                    """ INSERT INTO product_images (product_id, image_url) VALUES (?, ?);""",
                    (
                        product_id,
                        image_url,
                    ),
                )
        connection.commit()
        connection.close()
        if not success:
            return render_template(
                "pages/admin/modify_product.html",
                title=title,
                product=product,
                images=images,
                message=message,
            )
    return render_template(
        "pages/admin/modify_product.html",
        title=title,
        product=product,
        images=images,
        message=message,
    )


@app.route("/modify_products", methods=["GET", "POST"])
@admin_required
def modify_products():
    title = "Modify products"
    message = ""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(""" SELECT DISTINCT * FROM products;""")
    products = cursor.fetchall()
    cursor.execute(""" SELECT * FROM product_images;""")
    images = cursor.fetchall()
    connection.close()
    return render_template(
        "pages/admin/modify_products.html",
        title=title,
        products=products,
        images=images,
    )


@app.route("/dashboard", methods=["GET", "POST"])
@admin_required
def dashboard():
    title = "Admin Dashboard"
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        """SELECT * FROM admins WHERE admin_id = ?;""", (session["admin_id"],)
    )
    admin = cursor.fetchone()
    connection.close()
    return render_template(
        "pages/admin/dashboard.html", title=title, username=admin["username"]
    )


@app.route("/about")
def about():
    title = "About MONO"
    return render_template("pages/about.html", title=title)


@app.route("/account")
@login_required
def account():
    title = "My Account"
    user_id = session["user_id"]
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""SELECT * FROM users WHERE user_id = ?;""", (user_id,))
    user = cursor.fetchone()
    connection.close()
    return render_template("pages/customer/account.html", title=title, user=user)


@app.route("/admin_logout")
@admin_required
def admin_logout():
    session.clear()
    session.modified = True
    return redirect(url_for("admin"))


@app.route("/logout")
@login_required
def logout():
    session.clear()
    session.modified = True
    return redirect(url_for("home"))


@app.route("/login", methods=["GET", "POST"])
def login():
    title = "Login To Your Account"
    message = ""
    if request.method == "POST":
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()
        user, error = user_login(email, password)
        if user:
            session.clear()
            session.modified = True
            session["user_id"] = user["user_id"]
            session.permanent = True
            return redirect(url_for("account"))
        message = error
    return render_template("pages/login.html", title=title, message=message)


@app.route("/register", methods=["GET", "POST"])
def register():
    title = "Register A New Account"
    message = ""
    if request.method == "POST":
        firstname = request.form.get("fname")
        surname = request.form.get("sname")
        email = request.form.get("email")
        password = request.form.get("password")
        address = request.form.get("address")
        succes, message = add_new_user(firstname, surname, email, password, address)
    return render_template("pages/customer/register.html", title=title, message=message)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # app.run(debug=True, host="127.0.0.1", port=port) - for production
    app.run(debug=True, host="0.0.0.0", port=port)  # For upload to render
