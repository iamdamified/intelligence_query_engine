from fastapi import Depends, Request
from middleware.rate_limiter import rate_limit
from auth.dependencies import secure_user


def secure_request(request: Request, user: dict = Depends(secure_user)):
    """
    Global security pipeline:
    1. Rate limiting
    2. Authentication (JWT + API version)
    """

    rate_limit(request)

    return user