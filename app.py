from flask import Flask, render_template, redirect, url_for, session, request
import os
from datetime import *
import argon2
import sqlite3
from helpers import *
from flask_session import Session
from dotenv import load_dotenv
import secrets

app = Flask(__name__)


load_dotenv()


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
)

app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.secret_key = os.environ.get("SECRET_KEY")


@app.route("/")
def home():
    title = "Home Page"
    return render_template("pages/home.html", title=title)


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

    return render_template("/pages/account.html", title=title, user=user)


@app.route("/logout")
@login_required
def logout():
    session.clear()
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
            session["user_id"] = user["user_id"]
            session.permanent = True
            return redirect(url_for("account"))
        message = error
    return render_template("/pages/login.html", title=title, message=message)


@app.route("/register", methods=["GET", "POST"])
def register():
    title = "Register A New Account"
    message = " "
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
