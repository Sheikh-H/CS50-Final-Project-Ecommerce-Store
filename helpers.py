import sqlite3
from flask import *
from argon2.exceptions import *
from functools import wraps
from datetime import datetime
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import os
import stripe

def connect_db():
    connection = sqlite3.connect("instance/shop.db", timeout=10)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


def date_time():
    date = datetime.now()
    now = date.strftime("%d/%m/%Y %H:%M")
    return now


def update_account_details_function(
    user_id,
    fname,
    sname,
    email,
    old_password,
    new_password,
    address,
):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """SELECT * FROM users WHERE user_id = ?;""",
        (user_id,),
    )

    user = cursor.fetchone()

    if not user:
        connection.close()
        return False, "User not found."

    try:

        # User wants to change password
        if new_password.strip():

            # Old password required
            if not old_password.strip():
                connection.close()
                return False, "Current password is required."

            try:
                argon2.PasswordHasher().verify(user["password"], old_password)

            except VerifyMismatchError:
                connection.close()
                return False, "Current password is incorrect."

            hashed_password = argon2.PasswordHasher().hash(new_password)

            cursor.execute(
                """
                UPDATE users
                SET firstname = ?,
                    surname = ?,
                    email = ?,
                    password = ?,
                    address = ?
                WHERE user_id = ?;
                """,
                (
                    fname,
                    sname,
                    email,
                    hashed_password,
                    address,
                    user_id,
                ),
            )

        else:

            # No password update
            cursor.execute(
                """
                UPDATE users
                SET firstname = ?,
                    surname = ?,
                    email = ?,
                    address = ?
                WHERE user_id = ?;
                """,
                (
                    fname,
                    sname,
                    email,
                    address,
                    user_id,
                ),
            )

        connection.commit()
        connection.close()

        return True, "Account details updated successfully."

    except Exception as e:

        connection.rollback()
        connection.close()

        return False, f"Error updating account: {e}"


def order_details_function(order_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        """
    SELECT *
    FROM order_items
    JOIN products
        ON products.product_id = order_items.product_id
    LEFT JOIN product_images
        ON product_images.product_id = products.product_id
        AND product_images.is_primary = 1
    WHERE order_items.order_id = ?;
""",
        (order_id,),
    )
    order = cursor.fetchall()
    connection.close()
    return order


def order_history_function(user_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        """
    SELECT *
    FROM orders
    JOIN order_items
        ON orders.order_id = order_items.order_id
    JOIN products
        ON order_items.product_id = products.product_id
    LEFT JOIN product_images
        ON product_images.product_id = products.product_id
        AND product_images.is_primary = 1
    WHERE orders.user_id = ?
    ORDER BY orders.order_id DESC;
""",
        (user_id,),
    )
    orders = cursor.fetchall()
    connection.close()
    return orders


def load_products():
    connection = connect_db()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT DISTINCT * FROM products JOIN product_images ON products.product_id = product_images.product_id AND product_images.is_primary == 1;"""
        )
        products = cursor.fetchall()
        return True, products
    except Exception as e:
        print(e)
        return False, None
    finally:
        connection.close()


def update_customer(user_id, fname, sname, email, password, address):
    connection = connect_db()
    cursor = connection.cursor()
    try:
        hashed_password = argon2.PasswordHasher().hash(password)
        if password != "":
            cursor.execute(
                """UPDATE users SET firstname = ?, surname = ?, email = ?, password = ?, address = ? WHERE user_id = ?;""",
                (
                    fname,
                    sname,
                    email,
                    hashed_password,
                    address,
                    user_id,
                ),
            )
            connection.commit()
        else:
            cursor.execute(
                """UPDATE users SET firstname = ?, surname = ?, email = ?, address = ? WHERE user_id = ?;""",
                (
                    fname,
                    sname,
                    email,
                    address,
                    user_id,
                ),
            )
            connection.commit()
        return True, "Customer Details Updated!"
    except Exception as e:
        print(e)
        return False, "Unable to moify customer details"
    finally:
        connection.close()


def existing_customers():
    connection = connect_db()
    cursor = connection.cursor()
    try:
        cursor.execute("""SELECT * FROM users;""")
        customers = cursor.fetchall()
        return True, customers
    except Exception as e:
        print(e)
        return False, "Unable to retrieve data"
    finally:
        connection.close()


def update_admin(admin_id, name, role, password):
    connection = connect_db()
    cursor = connection.cursor()
    if role not in ["owner", "admin"]:
        return False, "Please enter correct role"
    try:
        if password != "":
            hashed_password = argon2.PasswordHasher().hash(password)
            cursor.execute(
                """UPDATE admins SET name = ?, role = ?, password = ? WHERE admin_id = ?;""",
                (
                    name,
                    role,
                    hashed_password,
                    admin_id,
                ),
            )
            connection.commit()
            return True, "Admin Details Updated!"
        else:
            cursor.execute(
                """UPDATE admins SET name = ?, role = ? WHERE admin_id = ?;""",
                (
                    name,
                    role,
                    admin_id,
                ),
            )
            connection.commit()
            return True, "Admin Details Updated!"
    except Exception as e:
        print(e)
        return False, "Unable to update admin"
    finally:
        connection.close()


def existing_admins():
    connection = connect_db()
    cursor = connection.cursor()
    try:
        cursor.execute("""SELECT * FROM admins;""")
        admins = cursor.fetchall()
        return admins
    except Exception as e:
        print(e)
        return False
    finally:
        connection.close()


# Same function made for admins to prevent url hacking
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin"))

        return f(*args, **kwargs)

    return decorated_function


def add_admin_function(role, name, username, password):
    username = username
    connection = connect_db()
    cursor = connection.cursor()
    now = date_time()
    cursor.execute(""" SELECT * FROM admins WHERE username = ?; """, (username,))
    existing_username = cursor.fetchone()

    if existing_username:
        return False, "Username Already Taken"

    hashed_password = argon2.PasswordHasher().hash(password)

    try:
        cursor.execute(
            """INSERT INTO admins (role, name, username, password, admin_created_at) VALUES (?, ?, ?, ?, ?);""",
            (
                role,
                name,
                username,
                hashed_password,
                now,
            ),
        )
        connection.commit()
        return True, "Admin has been added!"
    except Exception as e:
        print(e)
        return False, "Unable to add admin"
    finally:
        connection.close()


def admin_login_function(username, password):
    connection = connect_db()
    cursor = connection.cursor()
    verify = argon2.PasswordHasher().verify
    cursor.execute(
        """ SELECT * FROM admins WHERE username = ?; """,
        (username,),
    )
    admin = cursor.fetchone()
    if not admin:
        return None, "Username incorrect"
    try:
        verify(admin["password"], password)
        return admin, "Logged in"
    except VerifyMismatchError:
        return None, "Password Incorrect"
    finally:
        connection.close()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


def user_login(email, password):
    connection = connect_db()
    cursor = connection.cursor()

    verify = argon2.PasswordHasher().verify
    cursor.execute(
        """SELECT * FROM users WHERE email = ?;""",
        (email,),
    )

    user = cursor.fetchone()

    if not user:
        return None, "Email not found, please sign up or try again"
    try:
        verify(user["password"], password)
        return user, "Logged in"
    except VerifyMismatchError:
        return None, "Password Incorrect"
    finally:
        connection.close()


def add_new_user(fname, sname, email, password, address):
    hashed_password = argon2.PasswordHasher().hash(password)
    try:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO users (firstname, surname, email, password, address, user_created_at) VALUES (?, ?, ?, ?, ?, ?);""",
            (
                fname,
                sname,
                email,
                hashed_password,
                address,
                date_time(),
            ),
        )
        connection.commit()
        return True, "Account Registered, please login!"
    except sqlite3.IntegrityError:
        return False, "Existing Account or Invalid Details! Try again or login."
    finally:
        connection.close()

    # print(secrets.token_hex(32)) - this is the function used to generate a random key


def add_product(name, description, gender, category, price, brand, qty, images):
    try:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO products (product_name, product_description, product_price, product_category, product_brand, product_stock_qty, product_gender, product_created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
            (
                name,
                description,
                price,
                category,
                brand,
                qty,
                gender,
                date_time(),
            ),
        )
        product_id = cursor.lastrowid
        for index, image in enumerate(images):
            if image.filename == "":
                continue
            is_primary = 1 if index == 0 else 0
            upload = cloudinary.uploader.upload(
                image, folder="MONO_Products"
            )  # This is the function that uploads an image to cloudinary and then returns the url of it's location which is then used for each image.
            image_url = upload["secure_url"]
            cursor.execute(
                """INSERT INTO product_images (product_id, image_url, is_primary) VALUES (?, ?, ?);""",
                (
                    product_id,
                    image_url,
                    is_primary,
                ),
            )
        connection.commit()
    except Exception as e:
        print(e)
        return False, "Unable to add product!"
    finally:
        connection.close()
    return True, "Product Added!"


def update_product(
    name,
    description,
    price,
    category,
    brand,
    qty,
    gender,
    product_id,
):
    try:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE products SET product_name = ?, product_description = ?, product_price = ?, product_category = ?, product_brand = ?, product_stock_qty = ?, product_gender = ? WHERE product_id = ?;""",
            (name, description, price, category, brand, qty, gender, product_id),
        )
        connection.commit()
        return True, "Product Updated Successfully!"
    except Exception as e:
        print(e)
        return False, "Unable to update product!"
    finally:
        connection.close()
