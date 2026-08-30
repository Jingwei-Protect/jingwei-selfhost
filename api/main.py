"""Jingwei self-host API: protect, verify, optional adv-protect."""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.security_headers import SecurityHeadersMiddleware
from api.routes import adv_protect, protect, verify
from api.services.limits import max_upload_bytes

_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.is_file():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())

_TEMP_DIR = Path(tempfile.gettempdir()) / "jingwei_selfhost_api"
_TEMP_DIR.mkdir(exist_ok=True)
atexit.register(lambda: shutil.rmtree(_TEMP_DIR, ignore_errors=True))

_ENV = os.environ.get("APP_ENV", "dev").strip().lower()
_IS_PROD = _ENV == "production"

_dev_origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080", "http://127.0.0.1:8080"]
_extra_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
_allow_origins = _extra_origins if _IS_PROD else (_dev_origins + _extra_origins)


def _configure_form_parsers() -> None:
    cap = max_upload_bytes()
    try:
        from starlette.formparsers import FormParser, MultiPartParser

        MultiPartParser.max_part_size = cap
        if hasattr(FormParser, "max_part_size"):
            FormParser.max_part_size = cap
    except Exception:
        pass


_configure_form_parsers()

app = FastAPI(
    title="Jingwei self-host",
    version="1.0.0",
    docs_url=None if _IS_PROD else "/api/docs",
    redoc_url=None,
    openapi_url=None if _IS_PROD else "/api/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)
app.add_middleware(SecurityHeadersMiddleware)
app.include_router(protect.router, prefix="/api")
app.include_router(verify.router, prefix="/api")
app.include_router(adv_protect.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"ok": "true", "service": "jingwei-selfhost"}


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
SPA_FALLBACK_PATHS = frozenset({
    "protect",
    "verify",
    "adv-protect",
    "protocol",
    "privacy",
    "terms",
    "guide/watermark-matrix",
})


def is_spa_fallback_path(normalized: str) -> bool:
    if not normalized:
        return True
    return normalized in SPA_FALLBACK_PATHS


if FRONTEND_DIR.is_dir():
    from fastapi import HTTPException, Request
    from fastapi.responses import FileResponse, HTMLResponse

    _frontend_root = FRONTEND_DIR.resolve()

    def _serve_404():
        not_found = FRONTEND_DIR / "404.html"
        if not_found.is_file():
            return FileResponse(not_found, status_code=404)
        raise HTTPException(status_code=404)

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    async def serve_spa(request: Request, full_path: str = ""):
        normalized = full_path.strip("/")
        if normalized == "api" or normalized.startswith("api/"):
            raise HTTPException(status_code=404)
        if normalized:
            target = (FRONTEND_DIR / normalized).resolve()
            try:
                target.relative_to(_frontend_root)
            except ValueError:
                return _serve_404()
            if target.is_file():
                return FileResponse(target)
            if not is_spa_fallback_path(normalized):
                return _serve_404()
        index = FRONTEND_DIR / "index.html"
        if index.is_file():
            return HTMLResponse(index.read_text(encoding="utf-8"), media_type="text/html")
        return _serve_404()
