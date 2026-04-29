import typer
import json
from insighta.auth.github import login_flow
from insighta.auth.client import safe_request
from insighta.auth.session import clear_session, load_tokens

app = typer.Typer(help="Insighta Labs CLI - Profile Intelligence Query Engine")

# Create subcommands for profiles
profiles_app = typer.Typer(help="Manage profiles")
app.add_command(profiles_app, name="profiles")


# =========================
# AUTH COMMANDS
# =========================
@app.command()
def login():
    """Start GitHub OAuth login flow."""
    login_flow()
    print("✓ Login successful!")


@app.command()
def logout():
    """Logout user locally and clear session."""
    tokens = load_tokens()

    if not tokens:
        print("ℹ No active session found.")
        return

    try:
        safe_request("POST", "/auth/logout", json={
            "refresh_token": tokens.get("refresh_token")
        })
    except Exception:
        pass

    clear_session()
    print("✓ Logged out successfully.")


@app.command()
def whoami():
    """Fetch current authenticated user."""
    try:
        response = safe_request("GET", "/auth/me")

        if response.status_code != 200:
            print("✗ Not authenticated or session expired.")
            return

        data = response.json()
        if data.get("status") == "success":
            user = data.get("data", {})
            print(f"\n  👤 {user.get('username', 'Unknown')}")
            print(f"     Email: {user.get('email', 'N/A')}")
            print(f"     Role: {user.get('role', 'N/A')}")
            print(f"     ID: {user.get('id', 'N/A')}\n")
        else:
            print("✗ Failed to fetch user info")
    except Exception as e:
        print(f"✗ Error: {str(e)}")


# =========================
# PROFILE COMMANDS
# =========================
@profiles_app.command("list")
def profiles_list(
    gender: str = typer.Option(None, "--gender", help="Filter by gender (male/female)"),
    country: str = typer.Option(None, "--country", help="Filter by country code (e.g., NG, US)"),
    age_group: str = typer.Option(None, "--age-group", help="Filter by age group (child/teenager/adult/senior)"),
    min_age: int = typer.Option(None, "--min-age", help="Minimum age"),
    max_age: int = typer.Option(None, "--max-age", help="Maximum age"),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort by field (age/created_at/gender_probability)"),
    order: str = typer.Option("asc", "--order", help="Sort order (asc/desc)"),
    page: int = typer.Option(1, "--page", help="Page number"),
    limit: int = typer.Option(10, "--limit", help="Results per page"),
):
    """List profiles with optional filters."""
    params = {
        "gender": gender,
        "country": country,
        "country_id": country,  # API uses country_id
        "age_group": age_group,
        "min_age": min_age,
        "max_age": max_age,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "limit": limit,
    }

    clean_params = {k: v for k, v in params.items() if v is not None}
    
    # Remove duplicate country key
    if "country" in clean_params:
        del clean_params["country"]

    try:
        response = safe_request("GET", "/api/profiles", params=clean_params)
        data = response.json()
        
        if data.get("status") == "success":
            profiles = data.get("data", [])
            pagination = {
                "page": data.get("page"),
                "limit": data.get("limit"),
                "total": data.get("total"),
                "total_pages": data.get("total_pages"),
            }
            
            print(f"\n  📊 Profiles (Page {pagination['page']}/{pagination['total_pages']}, Total: {pagination['total']})\n")
            
            if profiles:
                for i, p in enumerate(profiles, 1):
                    print(f"  {i}. {p['name'].title()}")
                    print(f"     Gender: {p['gender']} ({p['gender_probability']:.2%})")
                    print(f"     Age: {p['age']} ({p['age_group']})")
                    print(f"     Country: {p['country_name']} ({p['country_probability']:.2%})")
                    print(f"     ID: {p['id']}\n")
            else:
                print("  No profiles found.\n")
        else:
            print(f"✗ Error: {data.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")


@profiles_app.command("search")
def profiles_search(
    query: str = typer.Argument(..., help="Natural language search query (e.g., 'male adults from Nigeria')"),
    page: int = typer.Option(1, "--page", help="Page number"),
    limit: int = typer.Option(10, "--limit", help="Results per page"),
):
    """Search profiles using natural language."""
    params = {
        "q": query,
        "page": page,
        "limit": limit,
    }

    try:
        response = safe_request("GET", "/api/profiles/search", params=params)
        data = response.json()
        
        if data.get("status") == "success":
            profiles = data.get("data", [])
            pagination = {
                "page": data.get("page"),
                "limit": data.get("limit"),
                "total": data.get("total"),
                "total_pages": data.get("total_pages"),
            }
            
            print(f"\n  🔍 Search Results: '{query}' (Page {pagination['page']}/{pagination['total_pages']}, Total: {pagination['total']})\n")
            
            if profiles:
                for i, p in enumerate(profiles, 1):
                    print(f"  {i}. {p['name'].title()}")
                    print(f"     Gender: {p['gender']} ({p['gender_probability']:.2%})")
                    print(f"     Age: {p['age']} ({p['age_group']})")
                    print(f"     Country: {p['country_name']} ({p['country_probability']:.2%})")
                    print(f"     ID: {p['id']}\n")
            else:
                print("  No results found.\n")
        else:
            print(f"✗ Error: {data.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")


@profiles_app.command("get")
def profiles_get(
    profile_id: str = typer.Argument(..., help="Profile ID (UUID)"),
):
    """Get a single profile by ID."""
    try:
        response = safe_request("GET", f"/api/profiles/{profile_id}")
        data = response.json()
        
        if data.get("status") == "success":
            p = data.get("data", {})
            print(f"\n  📋 Profile Details\n")
            print(f"     Name: {p.get('name', 'N/A').title()}")
            print(f"     Gender: {p.get('gender', 'N/A')} ({p.get('gender_probability', 0):.2%})")
            print(f"     Age: {p.get('age', 'N/A')} ({p.get('age_group', 'N/A')})")
            print(f"     Country: {p.get('country_name', 'N/A')} ({p.get('country_probability', 0):.2%})")
            print(f"     ID: {p.get('id', 'N/A')}")
            print(f"     Created: {p.get('created_at', 'N/A')}\n")
        else:
            print(f"✗ Error: {data.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")


@profiles_app.command("create")
def profiles_create(
    name: str = typer.Argument(..., help="Person's name"),
):
    """Create a new profile (admin only)."""
    try:
        response = safe_request("POST", "/api/profiles", json={"name": name})
        data = response.json()
        
        if data.get("status") == "success":
            p = data.get("data", {})
            print(f"\n  ✓ Profile created successfully!\n")
            print(f"     Name: {p.get('name', 'N/A').title()}")
            print(f"     Gender: {p.get('gender', 'N/A')} ({p.get('gender_probability', 0):.2%})")
            print(f"     Age: {p.get('age', 'N/A')} ({p.get('age_group', 'N/A')})")
            print(f"     Country: {p.get('country_name', 'N/A')} ({p.get('country_probability', 0):.2%})")
            print(f"     ID: {p.get('id', 'N/A')}\n")
        else:
            print(f"✗ Error: {data.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")


@profiles_app.command("export")
def profiles_export(
    format: str = typer.Option("csv", "--format", help="Export format (csv)"),
    gender: str = typer.Option(None, "--gender", help="Filter by gender"),
    country: str = typer.Option(None, "--country", help="Filter by country code"),
):
    """Export profiles to CSV file."""
    params = {
        "format": format,
        "gender": gender,
        "country_id": country,
    }

    clean_params = {k: v for k, v in params.items() if v is not None}

    try:
        response = safe_request("GET", "/api/profiles/export", params=clean_params)
        
        if response.status_code == 200:
            # Save to file
            filename = f"profiles_export.csv"
            with open(filename, "w") as f:
                f.write(response.text)
            print(f"✓ Profiles exported to {filename}")
        else:
            data = response.json() if response.text else {}
            print(f"✗ Error: {data.get('message', 'Export failed')}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")


# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    app()