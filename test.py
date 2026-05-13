import argon2
from datetime import datetime
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

# hasher = argon2.PasswordHasher()

# print(hasher.hash("Password123"))
# $argon2id$v=19$m=65536,t=3,p=4$zaS8265XxlHq5bNg/XmxgA$X1OF9bDN2WijfEyATLsW68Bs9gjWHGJ3sTQXNEc1LJg
# $argon2id$v=19$m=65536,t=3,p=4$/zZZW18KKsVFbQczNTzljw$etlKsU6RR89ltTEAxxhUZwC8I3K0pENjiq4Kdes60t0

date = datetime.now()
now = date.strftime("%d/%m/%Y %H:%M")


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
                
                
            ),
        )
        connection.commit()
        return True, "Account Registered, please login!"
    except sqlite3.IntegrityError:
        return False, "Existing Account or Invalid Details! Try again or login."
    finally:
        connection.close()
