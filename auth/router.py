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
from users.service import (
    get_or_create_github_user,
    get_user_by_id,
    create_test_user,
)
from users.models import RefreshToken
from auth.oauth.pkce import generate_code_verifier, generate_code_challenge
from auth.session import rotate_refresh_token, revoke_token
from utils import uuid7, utc_now   # ✅ required for test bypass

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
    role: str = "analyst"


# =========================
# OAuth (Third-party login)
# =========================
@router.get("/github")
def github_login(request: Request, response: Response):
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

    url = f"{GITHUB_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@router.get("/github/callback")
def github_callback(
    code: str = None,
    state: str = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    if not code:
        raise HTTPException(400, "Missing code parameter")

    # --------------------------------------------------
    # 🔥 HNG STAGE 3 TEST OAUTH BYPASS (REQUIRED)
    # --------------------------------------------------

    # ADMIN TEST TOKEN
    if code == "test_code_admin":
        user = create_test_user(db, username="test_admin", role="admin")

        access_token = create_access_token({
            "sub": str(user.id),
            "role": "admin",
        })

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
            "access_token": access_token,
            "refresh_token": refresh_token_value,
        }

    # ANALYST TEST TOKEN
    if code == "test_code_analyst":
        user = create_test_user(db, username="test_analyst", role="analyst")

        access_token = create_access_token({
            "sub": str(user.id),
            "role": "analyst",
        })

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
            "access_token": access_token,
            "refresh_token": refresh_token_value,
        }

    # DEFAULT TEST USER (legacy)
    if code == "test_code":
        user = create_test_user(db, username="test_user", role="admin")

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
            "access_token": access_token,
            "refresh_token": refresh_token_value,
        }

    # --------------------------------------------------
    # REAL GITHUB OAUTH FLOW
    # --------------------------------------------------
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

    return {
        "status": "success",
        "access_token": access_token,
        "refresh_token": refresh_token_value,
    }


# =========================
# Token lifecycle
# =========================
@router.post("/refresh")
def refresh_access_token(
    payload: RefreshTokenRequest,
    request: Request = None,
    db: Session = Depends(get_db),
):
    refresh_token = payload.refresh_token
    if not refresh_token:
        raise HTTPException(400, "Missing refresh_token")

    result = rotate_refresh_token(db, refresh_token)

    if not result:
        raise HTTPException(401, "Invalid or expired refresh token")

    new_refresh, user = result

    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
    })

    return {
        "status": "success",
        "access_token": access_token,
        "refresh_token": new_refresh,
    }


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    db: Session = Depends(get_db),
):
    if not payload.refresh_token:
        raise HTTPException(400, "Missing refresh_token")

    token_exists = revoke_token(db, payload.refresh_token)

    if token_exists is False:
        raise HTTPException(401, "Invalid refresh token")

    return {"status": "success"}


# =========================
# User Info
# =========================
@router.get("/me")
def get_current_user(
    payload: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
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
        },
    }