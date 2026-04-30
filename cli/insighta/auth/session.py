import os
import json
import requests

BASE_URL = "https://intelligence-query-engine.vercel.app"

TOKEN_PATH = os.path.expanduser("~/.insighta/credentials.json")


# =========================
# LOAD TOKENS
# =========================
def load_tokens():
    if not os.path.exists(TOKEN_PATH):
        return None

    with open(TOKEN_PATH, "r") as f:
        return json.load(f)


# =========================
# SAVE TOKENS
# =========================
def save_tokens(tokens: dict):
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)

    with open(TOKEN_PATH, "w") as f:
        json.dump(tokens, f, indent=2)


# =========================
# CLEAR SESSION
# =========================
def clear_session():
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)


# =========================
# GET ACCESS TOKEN
# =========================
def get_access_token():
    tokens = load_tokens()

    if not tokens:
        return None

    return tokens.get("access_token")


# =========================
# REFRESH TOKEN FLOW
# =========================
def refresh_access_token():
    tokens = load_tokens()

    if not tokens or "refresh_token" not in tokens:
        return None

    response = requests.post(
        f"{BASE_URL}/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    if response.status_code != 200:
        return None

    new_tokens = response.json()

    save_tokens(new_tokens)

    return new_tokens["access_token"]