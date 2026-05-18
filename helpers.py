import argon2
from flask import *
from argon2.exceptions import *
import secrets
from functools import wraps
from datetime import datetime
import cloudinary.uploader
import os
import stripe
from dotenv import load_dotenv

from extensions.supabase_client import supabase

load_dotenv()


# -------------------------
# Helpers
# -------------------------
def date_time():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


# -------------------------
# ACCOUNT DETAILS
# -------------------------
def update_account_details_function(
    user_id,
    fname,
    sname,
    email,
    old_password,
    new_password,
    address,
):

    user_res = supabase.table("users").select("*").eq("user_id", user_id).execute()
    user = user_res.data[0] if user_res.data else None

    if not user:
        return False, "User not found."

    try:
        if new_password.strip():

            if not old_password.strip():
                return False, "Current password is required."

            try:
                argon2.PasswordHasher().verify(user["password"], old_password)
            except VerifyMismatchError:
                return False, "Current password is incorrect."

            hashed_password = argon2.PasswordHasher().hash(new_password)

            supabase.table("users").update(
                {
                    "firstname": fname,
                    "surname": sname,
                    "email": email,
                    "password": hashed_password,
                    "address": address,
                }
            ).eq("user_id", user_id).execute()

        else:

            supabase.table("users").update(
                {
                    "firstname": fname,
                    "surname": sname,
                    "email": email,
                    "address": address,
                }
            ).eq("user_id", user_id).execute()

        return True, "Account details updated successfully."

    except Exception as e:
        return False, f"Error updating account: {e}"


# -------------------------
# ORDERS
# -------------------------
def order_details_function(order_id):
    res = (
        supabase.table("order_items")
        .select("*, products(*, product_images(*))")
        .eq("order_id", order_id)
        .execute()
    )

    return res.data


def order_history_function(user_id):
    res = (
        supabase.table("orders")
        .select("*, order_items(*, products(*, product_images(*)))")
        .eq("user_id", user_id)
        .order("order_id", desc=True)
        .execute()
    )

    return res.data


# -------------------------
# PRODUCTS
# -------------------------
def load_products():
    try:
        res = (
            supabase.table("products")
            .select("*, product_images(*)")
            .eq("product_images.is_primary", 1)
            .execute()
        )

        return True, res.data

    except Exception as e:
        print(e)
        return False, None


# -------------------------
# CUSTOMER ADMIN
# -------------------------
def update_customer(user_id, fname, sname, email, password, address):
    try:
        if password != "":
            hashed_password = argon2.PasswordHasher().hash(password)

            supabase.table("users").update(
                {
                    "firstname": fname,
                    "surname": sname,
                    "email": email,
                    "password": hashed_password,
                    "address": address,
                }
            ).eq("user_id", user_id).execute()

        else:
            supabase.table("users").update(
                {
                    "firstname": fname,
                    "surname": sname,
                    "email": email,
                    "address": address,
                }
            ).eq("user_id", user_id).execute()

        return True, "Customer Details Updated!"

    except Exception as e:
        print(e)
        return False, "Unable to moify customer details"


def existing_customers():
    try:
        res = supabase.table("users").select("*").execute()
        return True, res.data
    except Exception as e:
        print(e)
        return False, "Unable to retrieve data"


# -------------------------
# ADMINS
# -------------------------
def update_admin(admin_id, name, role, password):
    if role not in ["owner", "admin"]:
        return False, "Please enter correct role"

    try:
        if password != "":
            hashed_password = argon2.PasswordHasher().hash(password)

            supabase.table("admins").update(
                {
                    "name": name,
                    "role": role,
                    "password": hashed_password,
                }
            ).eq("admin_id", admin_id).execute()
        else:
            supabase.table("admins").update(
                {
                    "name": name,
                    "role": role,
                }
            ).eq("admin_id", admin_id).execute()

        return True, "Admin Details Updated!"

    except Exception as e:
        print(e)
        return False, "Unable to update admin"


def existing_admins():
    try:
        res = supabase.table("admins").select("*").execute()
        return res.data
    except Exception as e:
        print(e)
        return False


def add_admin_function(role, name, username, password):
    now = date_time()

    existing = supabase.table("admins").select("*").eq("username", username).execute()

    if existing.data:
        return False, "Username Already Taken"

    try:
        hashed_password = argon2.PasswordHasher().hash(password)

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
        res = supabase.table("admins").select("*").eq("username", username).execute()

        admin = res.data[0] if res.data else None

        if not admin:
            return None, "Username incorrect"

        argon2.PasswordHasher().verify(admin["password"], password)
        return admin, "Logged in"

    except VerifyMismatchError:
        return None, "Password Incorrect"


# -------------------------
# AUTH DECORATORS
# -------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin"))
        return f(*args, **kwargs)

    return decorated_function


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


# -------------------------
# USER AUTH
# -------------------------
def user_login(email, password):
    try:
        res = supabase.table("users").select("*").eq("email", email).execute()

        user = res.data[0] if res.data else None

        if not user:
            return None, "Email not found, please sign up or try again"

        argon2.PasswordHasher().verify(user["password"], password)
        return user, "Logged in"

    except VerifyMismatchError:
        return None, "Password Incorrect"


def add_new_user(fname, sname, email, password, address):
    hashed_password = argon2.PasswordHasher().hash(password)

    try:
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

    except Exception:
        return False, "Existing Account or Invalid Details! Try again or login."


# -------------------------
# PRODUCTS
# -------------------------
def add_product(name, description, gender, category, price, brand, qty, images):
    try:
        product_res = (
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
            .execute()
        )

        product_id = product_res.data[0]["product_id"]

        for index, image in enumerate(images):
            if image.filename == "":
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
