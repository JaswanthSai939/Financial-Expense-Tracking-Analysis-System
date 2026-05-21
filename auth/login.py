from datetime import datetime, timedelta
import os

import bcrypt
import jwt

from database.db import find_user_by_email


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "expense_secret_key")


def create_session_token(user):
    return jwt.encode(
        {
            "user_id": user["id"],
            "email": user["email"],
            "exp": datetime.utcnow() + timedelta(hours=2),
        },
        SECRET_KEY,
        algorithm="HS256",
    )


def authenticate_user(email, password):
    user = find_user_by_email(email)
    if not user:
        return None, None, "User not found."

    stored_password = user["password"]
    if not stored_password:
        return None, None, "This account uses Google login. Please continue with Google."

    if not bcrypt.checkpw(password.encode("utf-8"), stored_password.encode("utf-8")):
        return None, None, "Incorrect password."

    token = create_session_token(user)

    return user, token, "Login successful."
