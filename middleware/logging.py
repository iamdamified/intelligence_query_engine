import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Configure logging
logger = logging.getLogger("insighta")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Log all requests with:
        - Method
        - Endpoint
        - Status code
        - Response time (milliseconds)
        """
        start_time = time.time()

        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        # Log the request
        logger.info(
            f"{request.method} {request.url.path} | Status: {response.status_code} | Time: {process_time:.2f}ms"
        )

        return response
