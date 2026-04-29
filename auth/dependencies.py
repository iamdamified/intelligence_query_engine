from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from core.config import settings

# -------------------------
# TOKEN SCHEME
# -------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/github")


# -------------------------
# AUTHENTICATION LAYER
# -------------------------
def require_auth(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Validates JWT access token and returns payload.
    Single source of truth for authentication.
    """

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        user_id = payload.get("sub")
        role = payload.get("role")

        if not user_id or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


# -------------------------
# API VERSION ENFORCEMENT
# -------------------------
def require_api_version(
    x_api_version: str = Header(None)
):
    """
    Enforces required API version header for all /api/* routes.
    """

    if x_api_version != "1":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API version header required",
        )


# -------------------------
# COMPOSITE SECURITY LAYER
# -------------------------
def secure_user(
    payload: dict = Depends(require_auth),
    _version: str = Depends(require_api_version),
):
    """
    Unified security gate:
    - Auth check
    - API version check
    """

    return payload