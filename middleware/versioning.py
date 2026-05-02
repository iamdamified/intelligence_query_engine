from fastapi import Request, HTTPException

def require_api_version(request: Request):
    # Auth endpoints are exempt
    if request.url.path.startswith("/auth"):
        return

    if request.headers.get("X-API-Version") != "1":
        raise HTTPException(
            status_code=400,
            detail="API version header required"
        )