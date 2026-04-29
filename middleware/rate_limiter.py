import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status

# -----------------------------
# RATE LIMIT STORAGE
# -----------------------------
auth_requests = defaultdict(deque)
api_requests = defaultdict(deque)

AUTH_LIMIT = 10
API_LIMIT = 60
WINDOW = 60  # seconds


def _cleanup(queue: deque, now: float):
    while queue and now - queue[0] > WINDOW:
        queue.popleft()


def rate_limit(request: Request):
    """
    Simple per-IP rate limiter.
    """

    ip = request.client.host
    path = request.url.path
    now = time.time()

    # choose bucket
    if path.startswith("/auth"):
        bucket = auth_requests[ip]
        limit = AUTH_LIMIT
    else:
        bucket = api_requests[ip]
        limit = API_LIMIT

    _cleanup(bucket, now)

    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
        )

    bucket.append(now)