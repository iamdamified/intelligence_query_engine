import requests
from core.config import settings

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_URL = "https://api.github.com/user"


def exchange_code_for_token(code: str, code_verifier: str) -> str:
    response = requests.post(
        TOKEN_URL,
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
            "code_verifier": code_verifier,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def fetch_github_user(access_token: str) -> dict:
    response = requests.get(
        USER_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()