from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from math import ceil

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from starlette.types import ASGIApp


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    method: str
    path: str
    max_requests: int
    window_seconds: int


@dataclass
class _RateLimitBucket:
    count: int
    reset_at: float


class InMemoryRateLimiter:
    def __init__(self, *, now: Callable[[], float] = time.monotonic) -> None:
        self._now = now
        self._buckets: dict[tuple[str, str], _RateLimitBucket] = {}

    def check(self, *, rule: RateLimitRule, identity: str) -> tuple[bool, int]:
        now = self._now()
        key = (rule.name, identity)
        bucket = self._buckets.get(key)

        if bucket is None or bucket.reset_at <= now:
            self._buckets[key] = _RateLimitBucket(
                count=1,
                reset_at=now + rule.window_seconds,
            )
            return True, rule.window_seconds

        retry_after = max(1, ceil(bucket.reset_at - now))
        if bucket.count >= rule.max_requests:
            return False, retry_after

        bucket.count += 1
        return True, retry_after


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        rules: tuple[RateLimitRule, ...],
        enabled: bool = True,
        limiter: InMemoryRateLimiter | None = None,
    ) -> None:
        super().__init__(app)
        self._rules = rules
        self._enabled = enabled
        self._limiter = limiter or InMemoryRateLimiter()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rule = self._matching_rule(request)
        if self._enabled and rule is not None:
            allowed, retry_after = self._limiter.check(
                rule=rule,
                identity=_rate_limit_identity(request),
            )
            if not allowed:
                return JSONResponse(
                    {"detail": "Rate limit exceeded"},
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(rule.max_requests),
                        "X-RateLimit-Window": str(rule.window_seconds),
                    },
                )

        return await call_next(request)

    def _matching_rule(self, request: Request) -> RateLimitRule | None:
        request_path = request.url.path.rstrip("/") or "/"
        request_method = request.method.upper()
        for rule in self._rules:
            if rule.method.upper() == request_method and rule.path == request_path:
                return rule
        return None


def _rate_limit_identity(request: Request) -> str:
    authorization = request.headers.get("authorization")
    if authorization:
        return f"authorization:{authorization}"

    session_cookie = (
        request.cookies.get("better-auth.session_token")
        or request.cookies.get("__Secure-better-auth.session_token")
    )
    if session_cookie:
        return f"session:{session_cookie}"

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return f"ip:{forwarded_for.split(',', maxsplit=1)[0].strip()}"

    if request.client is not None:
        return f"ip:{request.client.host}"

    return "anonymous"
