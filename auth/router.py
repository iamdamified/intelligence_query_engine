import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from core.config import settings
from auth.tokens import create_access_token
from auth.oauth.github import exchange_code_for_token, fetch_github_user
from auth.oauth.state import save_state, validate_state, pop_verifier
from users.service import get_or_create_github_user
from users.models import RefreshToken
from auth.oauth.pkce import generate_code_verifier, generate_code_challenge
from auth.session import rotate_refresh_token, revoke_token


router = APIRouter(prefix="/auth", tags=["auth"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
SCOPES = "read:user user:email"

# =========================
# OAuth (Third-party login)
# =========================

@router.get("/github")
def github_login():
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

    url = f"{GITHUB_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@router.get("/github/callback")
def github_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    if not validate_state(state):
        raise HTTPException(400, "Invalid or expired OAuth state")

    code_verifier = pop_verifier(state)

    if not code_verifier:
        raise HTTPException(400, "Missing PKCE verifier")

    github_token = exchange_code_for_token(code, code_verifier)
    github_user = fetch_github_user(github_token)

    user = get_or_create_github_user(db, github_user)

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role}
    )

    refresh_token_value = secrets.token_urlsafe(48)

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_value,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
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
def refresh_access_token(payload: dict, db: Session = Depends(get_db)):
    refresh_token = payload.get("refresh_token")

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
def logout(payload: dict, db: Session = Depends(get_db)):
    refresh_token = payload.get("refresh_token")

    revoke_token(db, refresh_token)

    return {
        "status": "success",
        "message": "Logged out successfully",
    }