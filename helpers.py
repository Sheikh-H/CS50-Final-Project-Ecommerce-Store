import argon2

# import sqlite3
from flask import *
from argon2.exceptions import *
import secrets  # imported to help create the secret key
from functools import wraps
from datetime import datetime
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import os

# import shutil
import stripe

# from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# from supabase import create_client, Client
from extensions.supabase_client import supabase

load_dotenv()


# def connect_db():
#     connection = sqlite3.connect("instance/shop.db", timeout=10)
#     connection.execute("PRAGMA foreign_keys = ON")
#     connection.row_factory = sqlite3.Row
#     return connection


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

    try:
        # Fetch user from Supabase
        response = supabase.table("users").select("*").eq("user_id", user_id).execute()

        user_data = response.data

        if not user_data:
            return False, "User not found."

        user = user_data[0]

        ph = argon2.PasswordHasher()

        update_payload = {
            "firstname": fname,
            "surname": sname,
            "email": email,
            "address": address,
        }

        # If password is being changed
        if new_password and new_password.strip():

            if not old_password or not old_password.strip():
                return False, "Current password is required."

            try:
                ph.verify(user["password"], old_password)

            except VerifyMismatchError:
                return False, "Current password is incorrect."

            update_payload["password"] = ph.hash(new_password)

        # Update user in Supabase
        supabase.table("users").update(update_payload).eq("user_id", user_id).execute()

        return True, "Account details updated successfully."

    except Exception as e:
        return False, f"Error updating account: {e}"


def update_customer(user_id, fname, sname, email, password, address):

    try:
        update_payload = {
            "firstname": fname,
            "surname": sname,
            "email": email,
            "address": address,
        }

        # Only update password if provided
        if password and password.strip():
            ph = argon2.PasswordHasher()
            update_payload["password"] = ph.hash(password)

        supabase.table("users").update(update_payload).eq("user_id", user_id).execute()

        return True, "Customer Details Updated!"

    except Exception as e:
        print(e)
        return False, "Unable to modify customer details"


def existing_customers():

    try:
        response = supabase.table("users").select("*").execute()

        return True, response.data

    except Exception as e:
        print(e)
        return False, "Unable to retrieve data"


def update_admin(admin_id, name, role, password):

    # Role validation (keep this BEFORE DB call)
    if role not in ["owner", "admin"]:
        return False, "Please enter correct role"

    try:
        update_payload = {
            "name": name,
            "role": role,
        }

        # Only update password if provided
        if password and password.strip():
            ph = argon2.PasswordHasher()
            update_payload["password"] = ph.hash(password)

        supabase.table("admins").update(update_payload).eq(
            "admin_id", admin_id
        ).execute()

        return True, "Admin Details Updated!"

    except Exception as e:
        print(e)
        return False, "Unable to update admin"


def existing_admins():

    try:
        response = supabase.table("admins").select("*").execute()

        return response.data

    except Exception as e:
        print(e)
        return False


# Same function made for admins to prevent url hacking
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin"))

        return f(*args, **kwargs)

    return decorated_function


def add_admin_function(role, name, username, password):

    try:
        now = date_time()

        # 1. Check if username already exists
        existing = (
            supabase.table("admins")
            .select("admin_id")
            .eq("username", username)
            .execute()
        )

        if existing.data:
            return False, "Username Already Taken"

        # 2. Hash password
        ph = argon2.PasswordHasher()
        hashed_password = ph.hash(password)

        # 3. Insert new admin
        supabase.table("admins").insert(
            {
                "role": role,
                "name": name,
                "username": username,
                "password": hashed_password,
                "admin_created_at": now,
            }
        ).execute()

        return True, "Admin has been added!"

    except Exception as e:
        print(e)
        return False, "Unable to add admin"


def admin_login_function(username, password):

    try:
        # Fetch admin by username
        response = (
            supabase.table("admins").select("*").eq("username", username).execute()
        )

        admin_data = response.data

        if not admin_data:
            return None, "Username incorrect"

        admin = admin_data[0]

        # Verify password
        ph = argon2.PasswordHasher()

        try:
            ph.verify(admin["password"], password)
            return admin, "Logged in"

        except VerifyMismatchError:
            return None, "Password Incorrect"

    except Exception as e:
        print(e)
        return None, "Login error"


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


def user_login(email, password):

    try:
        # Fetch user by email
        response = supabase.table("users").select("*").eq("email", email).execute()

        user_data = response.data

        if not user_data:
            return None, "Email not found, please sign up or try again"

        user = user_data[0]

        # Verify password
        ph = argon2.PasswordHasher()

        try:
            ph.verify(user["password"], password)
            return user, "Logged in"

        except VerifyMismatchError:
            return None, "Password Incorrect"

    except Exception as e:
        print(e)
        return None, "Login error"


def add_new_user(fname, sname, email, password, address):

    try:
        ph = argon2.PasswordHasher()
        hashed_password = ph.hash(password)

        # Optional: check if email already exists
        existing = (
            supabase.table("users").select("user_id").eq("email", email).execute()
        )

        if existing.data:
            return False, "Existing Account or Invalid Details! Try again or login."

        # Insert new user
        supabase.table("users").insert(
            {
                "firstname": fname,
                "surname": sname,
                "email": email,
                "password": hashed_password,
                "address": address,
                "user_created_at": date_time(),
            }
        ).execute()

        return True, "Account Registered, please login!"

    except Exception as e:
        print(e)
        return False, "Error registering account"


# print(secrets.token_hex(32)) - this is the function used to generate a random key


def add_product(name, description, gender, category, price, brand, qty, images):

    try:
        # 1. Insert product first
        product_response = (
            supabase.table("products")
            .insert(
                {
                    "product_name": name,
                    "product_description": description,
                    "product_price": price,
                    "product_category": category,
                    "product_brand": brand,
                    "product_stock_qty": qty,
                    "product_gender": gender,
                    "product_created_at": date_time(),
                }
            )
            .select("product_id")
            .execute()
        )

        if not product_response.data:
            return False, "Unable to add product!"

        product_id = product_response.data[0]["product_id"]

        # 2. Upload images + insert into product_images
        for index, image in enumerate(images):

            if not image or image.filename == "":
                continue

            is_primary = 1 if index == 0 else 0

            upload = cloudinary.uploader.upload(image, folder="MONO_Products")

            image_url = upload["secure_url"]

            supabase.table("product_images").insert(
                {
                    "product_id": product_id,
                    "image_url": image_url,
                    "is_primary": is_primary,
                }
            ).execute()

        return True, "Product Added!"

    except Exception as e:
        print(e)
        return False, "Unable to add product!"


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
        supabase.table("products").update(
            {
                "product_name": name,
                "product_description": description,
                "product_price": price,
                "product_category": category,
                "product_brand": brand,
                "product_stock_qty": qty,
                "product_gender": gender,
            }
        ).eq("product_id", product_id).execute()

        return True, "Product Updated Successfully!"

    except Exception as e:
        print(e)
        return False, "Unable to update product!"
