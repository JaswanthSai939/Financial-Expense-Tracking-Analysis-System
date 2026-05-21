import bcrypt
import mysql.connector

from database.db import create_user, find_user_by_email


def register_user(username, email, password):
    if not username or not email or not password:
        return False, "Please enter username, email, and password."

    if find_user_by_email(email):
        return False, "An account with this email already exists."

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    try:
        create_user(username, email, hashed_password)
    except mysql.connector.Error as exc:
        return False, f"Registration failed: {exc}"

    return True, "Registration successful. You can now log in."
