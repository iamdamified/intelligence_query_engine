from fastapi import Depends, HTTPException, status
from auth.dependencies import require_auth


def require_role(*allowed_roles: str):
    """
    Role-based access control dependency.
    """

    def role_checker(payload: dict = Depends(require_auth)):
        role = payload.get("role")

        if not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User role missing in token payload",
            )

        role = str(role).lower()
        allowed = [r.lower() for r in allowed_roles]

        if role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return payload

    return role_checker