"""HTTP security headers for API responses and SPA static assets."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Google Fonts are loaded from CSS @import in index.css — allow those hosts only.
_CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'self'; "
    "object-src 'none'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob:; "
    "media-src 'self' blob:; "
    "connect-src 'self' blob:;"
)

_SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    ("Content-Security-Policy", _CSP),
    ("X-Frame-Options", "SAMEORIGIN"),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("Cross-Origin-Resource-Policy", "same-site"),
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for name, value in _SECURITY_HEADERS:
            if name not in response.headers:
                response.headers[name] = value
        return response
