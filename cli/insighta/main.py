import typer
from insighta.auth.github import login_flow
from insighta.auth.client import safe_request
from insighta.auth.session import clear_session, load_tokens

app = typer.Typer()


# =========================
# AUTH COMMANDS
# =========================
@app.command()
def login():
    """Start GitHub OAuth login flow."""
    login_flow()


@app.command()
def logout():
    """Logout user locally and clear session."""
    tokens = load_tokens()

    if not tokens:
        print("No active session found.")
        return

    try:
        safe_request("POST", "/auth/logout", json={
            "refresh_token": tokens.get("refresh_token")
        })
    except Exception:
        pass

    clear_session()
    print("Logged out successfully.")


@app.command()
def whoami():
    """Fetch current authenticated user."""
    response = safe_request("GET", "/auth/me")

    if response.status_code != 200:
        print("Not authenticated or session expired.")
        return

    print(response.json())


# =========================
# PROFILE COMMANDS
# =========================
@app.command()
def profiles_list(
    gender: str = None,
    country: str = None,
    age_group: str = None,
    page: int = 1,
    limit: int = 10,
):
    params = {
        "gender": gender,
        "country": country,
        "age_group": age_group,
        "page": page,
        "limit": limit,
    }

    clean_params = {k: v for k, v in params.items() if v is not None}

    response = safe_request("GET", "/api/profiles", params=clean_params)
    print(response.json())


@app.command()
def profiles_search(query: str):
    response = safe_request("GET", "/api/profiles/search", params={"q": query})
    print(response.json())


@app.command()
def profiles_get(profile_id: str):
    response = safe_request("GET", f"/api/profiles/{profile_id}")
    print(response.json())


@app.command()
def profiles_create(name: str):
    response = safe_request("POST", "/api/profiles", json={"name": name})
    print(response.json())


@app.command()
def profiles_export(format: str = "csv"):
    response = safe_request("GET", "/api/profiles/export", params={"format": format})
    print(response.text)


# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    app()