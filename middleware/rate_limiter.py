import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status

# -----------------------------
# RATE LIMIT STORAGE
# auth_requests: IP-based (no auth needed)
# api_requests: User-based (authenticated)
# -----------------------------
auth_requests = defaultdict(deque)  # IP -> deque of timestamps
api_requests = defaultdict(deque)   # user_id -> deque of timestamps

AUTH_LIMIT = 10
API_LIMIT = 60
WINDOW = 60  # seconds


def _cleanup(queue: deque, now: float):
    while queue and now - queue[0] > WINDOW:
        queue.popleft()


def rate_limit(request: Request, user_id: str = None):
    """
    Rate limiter:
    - Auth endpoints: 10 req/min per IP
    - API endpoints: 60 req/min per user
    """

    path = request.url.path
    now = time.time()

    # Auth endpoints: limit by IP
    if path.startswith("/auth"):
        ip = request.client.host
        bucket = auth_requests[ip]
        limit = AUTH_LIMIT

        _cleanup(bucket, now)

        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
            )

        bucket.append(now)

    # API endpoints: limit by user
    elif path.startswith("/api"):
        if not user_id:
            # Unauthenticated access (shouldn't happen, but fallback to IP)
            ip = request.client.host
            bucket = api_requests[ip]
        else:
            bucket = api_requests[user_id]

        limit = API_LIMIT

        _cleanup(bucket, now)

        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
            )

        bucket.append(now)