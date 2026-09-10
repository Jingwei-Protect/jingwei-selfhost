"""CSP must allow blob: connects so the SPA can read object-URL result images."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from api.middleware.security_headers import _CSP


def _csp_directive(csp: str, name: str) -> str:
    for part in csp.split(";"):
        part = part.strip()
        if part == name or part.startswith(name + " "):
            return part[len(name) :].strip()
    raise AssertionError(f"missing CSP directive {name}")


def test_csp_connect_src_allows_blob_object_urls() -> None:
    """ProtectPage stores the result as a blob: URL. 下载闪卡 used to fetch() it.

    ``connect-src 'self'`` blocks blob: fetches in production, which the UI
    mislabels as “start the backend”. img-src already allows blob:; connect-src
    must too.
    """
    tokens = _csp_directive(_CSP, "connect-src").split()
    assert "blob:" in tokens
    assert "'self'" in tokens


def test_api_responses_send_blob_connect_csp() -> None:
    client = TestClient(app)
    res = client.get("/api/public/stats")
    connect = _csp_directive(res.headers["content-security-policy"], "connect-src")
    assert "blob:" in connect.split()
    assert "'self'" in connect.split()
