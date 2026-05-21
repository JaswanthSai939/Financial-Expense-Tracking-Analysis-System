from urllib.parse import urlencode

import requests

from auth.login import create_session_token
from database.db import (
    create_google_user,
    find_user_by_email,
    find_user_by_google_sub,
    link_google_to_existing_user,
)


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def build_google_auth_url(client_id, redirect_uri, state):
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def fetch_google_user(code, client_id, client_secret, redirect_uri):
    token_response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    token_response.raise_for_status()
    token_data = token_response.json()

    user_response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
        timeout=20,
    )
    user_response.raise_for_status()
    return user_response.json()


def login_or_create_google_user(google_user):
    google_sub = google_user["sub"]
    email = google_user["email"]
    username = google_user.get("name") or email.split("@")[0]

    user = find_user_by_google_sub(google_sub)
    if not user:
        user = find_user_by_email(email)
        if user:
            link_google_to_existing_user(user["id"], google_sub)
            user = find_user_by_email(email)
        else:
            create_google_user(username, email, google_sub)
            user = find_user_by_google_sub(google_sub)

    token = create_session_token(user)
    return user, token
