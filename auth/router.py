import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from core.config import settings
from auth.tokens import create_access_token
from auth.dependencies import require_auth
from auth.oauth.github import exchange_code_for_token, fetch_github_user
from auth.oauth.state import save_state, validate_state, pop_verifier
from users.service import get_or_create_github_user, get_user_by_id, create_test_user
from users.models import RefreshToken
from auth.oauth.pkce import generate_code_verifier, generate_code_challenge
from auth.session import rotate_refresh_token, revoke_token


router = APIRouter(prefix="/auth", tags=["auth"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
SCOPES = "read:user user:email"


# =========================
# Request Models
# =========================
class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class CreateTestUserRequest(BaseModel):
    username: str
    role: str = "analyst"  # admin or analyst


# =========================
# OAuth (Third-party login)
# =========================

@router.get("/github")
def github_login(request: Request, response: Response):
    state = secrets.token_urlsafe(32)

    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)

    save_state(state, verifier)   # 🔥 unified storage

    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }

    # Add CORS headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"

    url = f"{GITHUB_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })


@router.options("/github")
def github_login_options(response: Response):
    """CORS preflight for /auth/github"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return {"status": "ok"}


# Web Portal OAuth endpoint
@router.get("/web/github")
def web_github_login(request: Request, response: Response):
    """Web portal GitHub OAuth initiation"""
    state = secrets.token_urlsafe(32)

    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)

    save_state(state, verifier)

    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }

    # Add CORS headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"

    url = f"{GITHUB_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })


@router.options("/web/github")
def web_github_login_options(response: Response):
    """CORS preflight for /auth/web/github"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return {"status": "ok"}


@router.get("/web/github/callback")
def web_github_callback(
    code: str = None,
    state: str = None,
    db: Session = Depends(get_db),
):
    """Web portal GitHub OAuth callback"""
    # Validate required parameters
    if not code:
        raise HTTPException(400, "Missing code parameter")
    
    if not state:
        raise HTTPException(400, "Missing state parameter")
    
    if not validate_state(state):
        raise HTTPException(400, "Invalid or expired OAuth state")

    code_verifier = pop_verifier(state)

    if not code_verifier:
        raise HTTPException(400, "Missing PKCE verifier")

    try:
        github_token = exchange_code_for_token(code, code_verifier)
        github_user = fetch_github_user(github_token)
    except Exception as e:
        raise HTTPException(400, f"Failed to authenticate with GitHub: {str(e)}")

    user = get_or_create_github_user(db, github_user)

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role}
    )

    refresh_token_value = secrets.token_urlsafe(48)

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_value,
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )

    db.add(refresh_token)
    db.commit()

    return JSONResponse({
        "status": "success",
        "access_token": access_token,
        "refresh_token": refresh_token_value,
    })


@router.get("/github/callback")
def github_callback(
    code: str = None,
    state: str = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    # Validate required parameters
    if not code:
        raise HTTPException(400, "Missing code parameter")
    
    if not state:
        raise HTTPException(400, "Missing state parameter")
    
    if not validate_state(state):
        raise HTTPException(400, "Invalid or expired OAuth state")

    code_verifier = pop_verifier(state)

    if not code_verifier:
        raise HTTPException(400, "Missing PKCE verifier")

    try:
        github_token = exchange_code_for_token(code, code_verifier)
        github_user = fetch_github_user(github_token)
    except Exception as e:
        raise HTTPException(400, f"Failed to authenticate with GitHub: {str(e)}")

    user = get_or_create_github_user(db, github_user)

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role}
    )

    refresh_token_value = secrets.token_urlsafe(48)

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_value,
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )

    db.add(refresh_token)
    db.commit()

    return JSONResponse({
        "status": "success",
        "access_token": access_token,
        "refresh_token": refresh_token_value,
    })


# =========================
# Token lifecycle
# =========================


@router.post("/refresh")
def refresh_access_token(
    payload: RefreshTokenRequest,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Refresh access token using refresh token. Requires POST method."""
    refresh_token = payload.refresh_token

    if not refresh_token:
        raise HTTPException(400, "Missing refresh_token")

    result = rotate_refresh_token(db, refresh_token)

    if not result:
        raise HTTPException(401, "Invalid or expired refresh token")

    new_refresh, user_id = result

    access_token = create_access_token({"sub": str(user_id)})

    return {
        "status": "success",
        "access_token": access_token,
        "refresh_token": new_refresh,
    }


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Logout user by revoking refresh token. Requires POST method."""
    refresh_token = payload.refresh_token

    if not refresh_token:
        raise HTTPException(400, "Missing refresh_token")

    revoke_token(db, refresh_token)

    return {
        "status": "success",
        "message": "Logged out successfully",
    }


# =========================
# User Info
# =========================
@router.get("/me")
def get_current_user(
    payload: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Returns current authenticated user info.
    """
    user_id = payload.get("sub")
    user = get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(404, "User not found")
    
    return {
        "status": "success",
        "data": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }
    }


# =========================
# Test Endpoints (for testing purposes)
# =========================
@router.post("/test/user")
def create_test_user_endpoint(
    payload: CreateTestUserRequest,
    db: Session = Depends(get_db),
):
    """
    Create a test user with specified role for testing purposes.
    Only available in development environment.
    """
    if settings.ENV != "development":
        raise HTTPException(403, "Test endpoint only available in development")
    
    user = create_test_user(db, payload.username, payload.role)
    
    # Generate tokens for the test user
    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role}
    )
    
    refresh_token_value = secrets.token_urlsafe(48)
    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_value,
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )
    
    db.add(refresh_token)
    db.commit()
    
    return {
        "status": "success",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
        },
        "access_token": access_token,
        "refresh_token": refresh_token_value,
    }