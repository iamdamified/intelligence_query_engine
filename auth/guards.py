from fastapi import Depends, Request, HTTPException, status
from middleware.rate_limiter import rate_limit
from auth.dependencies import require_auth


def secure_request(
    request: Request,
    user: dict = Depends(require_auth)
):
    """
    Global security pipeline:
    1. Rate limiting
    2. Authentication (JWT validation)
    3. API version check (for /api/* endpoints)
    """

    # Check API version for /api/* endpoints
    if request.url.path.startswith("/api/"):
        api_version = request.headers.get("X-API-Version")
        if api_version != "1":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API version header required",
            )

    rate_limit(request, user_id=user.get("sub"))

    return user



# from fastapi import Depends, Request
# from middleware.rate_limiter import rate_limit
# from auth.dependencies import secure_user


# def secure_request(request: Request, user: dict = Depends(secure_user)):
#     """
#     Global security pipeline:
#     1. Rate limiting
#     2. Authentication (JWT + API version)
#     """

#     rate_limit(request)

#     return user