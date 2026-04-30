import time
from collections import defaultdict, deque
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import status

# Rate limit storage
auth_requests = defaultdict(deque)  # IP -> deque of timestamps
api_requests = defaultdict(deque)   # user_id -> deque of timestamps

AUTH_LIMIT = 10
API_LIMIT = 60
WINDOW = 60  # seconds


def _cleanup(queue: deque, now: float):
    while queue and now - queue[0] > WINDOW:
        queue.popleft()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        now = time.time()

        # Auth endpoints: limit by IP
        if path.startswith("/auth"):
            ip = request.client.host if request.client else "unknown"
            bucket = auth_requests[ip]
            limit = AUTH_LIMIT

            _cleanup(bucket, now)

            if len(bucket) >= limit:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many requests"},
                )

            bucket.append(now)

        response = await call_next(request)
        return response
