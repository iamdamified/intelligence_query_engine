import typer
from insighta.auth.github import login_flow
from insighta.auth.client import safe_request

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
    print("Logging out... (to be implemented in Step 6.12)")


@app.command()
def whoami():
    print("Fetching current user... (to be implemented in Step 6.12)")


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

    response = safe_request(
        "GET",
        "/api/profiles",
        params={k: v for k, v in params.items() if v is not None},
    )

    print(response.json())


@app.command()
def profiles_search(query: str):
    response = safe_request(
        "GET",
        "/api/profiles/search",
        params={"q": query},
    )

    print(response.json())


@app.command()
def profiles_get(profile_id: str):
    response = safe_request(
        "GET",
        f"/api/profiles/{profile_id}",
    )

    print(response.json())


@app.command()
def profiles_create(name: str):
    response = safe_request(
        "POST",
        "/api/profiles",
        json={"name": name},
    )

    print(response.json())


@app.command()
def profiles_export(format: str = "csv"):
    response = safe_request(
        "GET",
        "/api/profiles/export",
        params={"format": format},
    )

    # CSV is plain text, not JSON
    print(response.text)


# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    app()