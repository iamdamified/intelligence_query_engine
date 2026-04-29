from fastapi import Depends, HTTPException, status
from auth.dependencies import require_auth


def require_role(*allowed_roles: str):
    """
    RBAC dependency factory.

    Usage:
        Depends(require_role("admin"))
        Depends(require_role("admin", "analyst"))
    """

    def role_checker(payload: dict = Depends(require_auth)):
        role = payload.get("role")

        if not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User role missing in token payload",
            )

        if not isinstance(role, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid role format in token",
            )

        role = role.lower()

        allowed = [r.lower() for r in allowed_roles]

        if role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return payload

    return role_checker