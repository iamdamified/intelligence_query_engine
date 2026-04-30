import requests
from insighta.auth.session import get_access_token, refresh_access_token

BASE_URL = "https://intelligence-query-engine.vercel.app"


# =========================
# AUTH HEADER BUILDER
# =========================
def auth_headers():
    token = get_access_token()

    if not token:
        raise Exception("Not authenticated. Run 'insighta login'.")

    return {
        "Authorization": f"Bearer {token}",
        "X-API-Version": "1",
    }


# =========================
# SAFE REQUEST (AUTO REFRESH)
# =========================
def safe_request(method, url, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.update(auth_headers())

    # Ensure full URL
    if not url.startswith("http"):
        url = f"{BASE_URL}{url}"

    response = requests.request(method, url, headers=headers, **kwargs)

    # Token expired → try refresh
    if response.status_code == 401:
        new_token = refresh_access_token()

        if not new_token:
            raise Exception("Session expired. Please login again.")

        headers["Authorization"] = f"Bearer {new_token}"

        response = requests.request(method, url, headers=headers, **kwargs)

    return response