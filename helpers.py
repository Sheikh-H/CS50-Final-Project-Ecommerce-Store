import argon2
import sqlite3
from flask import *
from argon2.exceptions import *
import secrets  # imported to help create the secret key
from functools import wraps
from datetime import datetime


def date_time():
    date = datetime.now()
    now = date.strftime("%d/%m/%Y %H:%M")
    return now


# Same function made for admins to prevent url hacking
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect("/admin")

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
    connection = sqlite3.connect("instance/shop.db")
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
    connection = connect_db()
    cursor = connection.cursor()
    hashed_password = argon2.PasswordHasher().hash(password)
    fname = fname.strip()
    sname = sname.strip()
    fname = fname.lower()
    sname = sname.lower()
    fname = fname.title()
    sname = sname.title()
    try:
        cursor.execute(
            """INSERT INTO users (firstname, surname, email, password, address) VALUES (?, ?, ?, ?, ?);""",
            (fname, sname, email, hashed_password, address),
        )
        connection.commit()
        return True, "Account Registered, please login!"
    except VerifyMismatchError:
        return False, "Existing Account or Invalid Details, Try again or login"
    finally:
        connection.close()


# print(secrets.token_hex(32)) - this is the function used to generate a random key
