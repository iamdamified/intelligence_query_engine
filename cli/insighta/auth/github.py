import base64
import hashlib
import secrets
import webbrowser
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from insighta.auth.session import save_tokens


# =========================
# CONFIG
# =========================
BASE_URL = "http://localhost:8000"
REDIRECT_URI = "http://localhost:8765/callback"


# =========================
# PKCE HELPERS
# =========================
def generate_code_verifier():
    return secrets.token_urlsafe(64)


def generate_code_challenge(verifier: str):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().replace("=", "")


# =========================
# LOCAL CALLBACK SERVER
# =========================
class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if "code" in query:
            self.server.auth_code = query["code"][0]

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"You can close this window now.")
        else:
            self.send_response(400)
            self.end_headers()


def start_callback_server():
    server = HTTPServer(("localhost", 8765), CallbackHandler)
    server.auth_code = None

    while server.auth_code is None:
        server.handle_request()

    return server.auth_code


# =========================
# MAIN LOGIN FLOW
# =========================
def login_flow():
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)

    # Step 1: Redirect to backend OAuth endpoint
    auth_url = (
        f"{BASE_URL}/auth/github"
        f"?code_challenge={challenge}"
        f"&redirect_uri={REDIRECT_URI}"
    )

    print("Opening browser for GitHub login...")
    webbrowser.open(auth_url)

    # Step 2: Wait for callback
    print("Waiting for callback...")
    code = start_callback_server()

    # Step 3: Exchange code for tokens
    response = requests.post(
        f"{BASE_URL}/auth/github/callback",
        json={
            "code": code,
            "code_verifier": verifier,
        },
    )

    if response.status_code != 200:
        print("Login failed:", response.text)
        return

    data = response.json()

    # Step 4: Validate expected structure
    tokens = {
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
    }

    if not tokens["access_token"] or not tokens["refresh_token"]:
        print("Invalid token response from backend")
        return

    # Step 5: Save via session manager (single source of truth)
    save_tokens(tokens)

    print("Login successful!")