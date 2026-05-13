from flask import Flask, render_template, redirect, url_for, session, request
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

app = Flask(__name__)

date_now = date_time()

load_dotenv()

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
    SESSION_COOKIE_SECURE=True,
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


@app.route("/admin", methods=["GET", "POST"])
def admin():
    title = "Admin page"
    message = ""
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        admin, error = admin_login_function(username, password)
        if admin:
            session.clear()
            session.modified = True
            session["admin_id"] = admin["admin_id"]
            session.permanent = True
            return redirect(url_for("dashboard"))
        message = error
    return render_template("pages/admin_login.html", title=title, message=message)


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
        images = request.files.getlist("image")
        success, message = add_product(
            name, description, gender, category, price, brand, qty, images
        )
    return render_template("pages/add_new_products.html", title=title, message=message)


@app.route("/modify_products", methods=["GET", "POST"])
@admin_required
def modify_products():
    title = "Modify products"
    message = ""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT DISTINCT
        product_images.image_url, 
        products.product_id, 
        products.product_name, 
        products.product_description, 
        products.product_price, 
        products.product_category, 
        products.product_is_active, 
        products.product_brand, 
        products.product_stock_qty, 
        products.product_gender, 
        products.product_created_at 
        FROM products 
        JOIN product_images 
        ON 
        products.product_id = product_images.product_id;
        """)
    products = cursor.fetchall()
    connection.close()
    return render_template("pages/modify_products.html", title=title, products=products)


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
        "pages/dashboard.html", title=title, username=admin["username"]
    )


@app.route("/about")
def about():
    title = "About Us"
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
    return render_template("/pages/account.html", title=title, user=user)


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
    return render_template("/pages/login.html", title=title, message=message)


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
    return render_template("/pages/register.html", title=title, message=message)


if __name__ == "__main__":
    port = os.environ.get("PORT", 5000)
    app.run(debug=True, host="127.0.0.1", port=port)
