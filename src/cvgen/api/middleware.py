"""API middleware for rate limiting and request logging."""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter
_request_counts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 60  # requests per minute
RATE_WINDOW = 60  # seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware.

    Limits requests per IP to RATE_LIMIT per RATE_WINDOW seconds.
    Skips rate limiting for health check endpoints.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip health checks
        if request.url.path == "/api/v1/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old entries
        _request_counts[client_ip] = [
            t for t in _request_counts[client_ip] if now - t < RATE_WINDOW
        ]

        if len(_request_counts[client_ip]) >= RATE_LIMIT:
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type="application/json",
            )

        _request_counts[client_ip].append(now)
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs incoming requests with timing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        logger.info(
            f"{request.method} {request.url.path} "
            f"→ {response.status_code} ({duration_ms:.1f}ms)"
        )

        return response
