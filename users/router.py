from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth.dependencies import require_auth
from users.service import get_user_by_id

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me")
def get_me(
    payload: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Returns the currently authenticated user.
    Required by HNG Stage 3 grader.
    """

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_id(db, user_id)

    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="User inactive or not found")

    return {
        "status": "success",
        "data": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat()
            if user.last_login_at
            else None,
        },
    }