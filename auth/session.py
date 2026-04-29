from datetime import datetime, timedelta, timezone
import secrets

from users.models import RefreshToken
from core.config import settings


# -----------------------------
# CREATE REFRESH TOKEN RECORD
# -----------------------------
def create_refresh_token(db, user_id: str):
    token_value = secrets.token_urlsafe(48)

    token = RefreshToken(
        user_id=user_id,
        token=token_value,
        is_revoked=False,
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )

    db.add(token)
    db.commit()

    return token_value


# -----------------------------
# ROTATE REFRESH TOKEN
# -----------------------------
def rotate_refresh_token(db, old_token: str):
    record = db.query(RefreshToken).filter_by(token=old_token).first()

    if not record or record.is_revoked:
        return None

    if record.expires_at < datetime.now(timezone.utc):
        return None

    # revoke old token
    record.is_revoked = True

    # issue new token
    new_token = create_refresh_token(db, record.user_id)

    db.commit()

    return new_token, record.user_id


# -----------------------------
# REVOKE TOKEN (LOGOUT)
# -----------------------------
def revoke_token(db, token: str):
    record = db.query(RefreshToken).filter_by(token=token).first()

    if record:
        record.is_revoked = True
        db.commit()