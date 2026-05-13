import argon2
import sqlite3
from flask import *
from argon2.exceptions import *
import secrets  # imported to help create the secret key
from functools import wraps
from datetime import datetime
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url


def date_time():
    date = datetime.now()
    now = date.strftime("%d/%m/%Y %H:%M")
    return now


# Same function made for admins to prevent url hacking
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin"))

        return f(*args, **kwargs)

    return decorated_function


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


def connect_db():
    connection = sqlite3.connect("instance/shop.db", timeout=10)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


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
            upload = cloudinary.uploader.upload(image, folder="MONO_Products")
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
