"""VT-07: headers de seguridad en todas las respuestas HTTP."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient as StarletteTestClient

from app.shared.security.security_headers_middleware import SecurityHeadersMiddleware


async def _ok(request):
    return PlainTextResponse("ok")


@pytest.fixture
def minimal_app_no_hsts():
    app = Starlette(routes=[Route("/", _ok)])
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=False)
    return app


@pytest.fixture
def minimal_app_hsts():
    app = Starlette(routes=[Route("/", _ok)])
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True)
    return app


def _assert_core_security_headers(headers):
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in headers
    assert "camera=()" in headers["Permissions-Policy"]
    csp = headers.get("Content-Security-Policy", "")
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


def test_middleware_without_hsts(minimal_app_no_hsts):
    client = StarletteTestClient(minimal_app_no_hsts)
    r = client.get("/")
    assert r.status_code == 200
    _assert_core_security_headers(r.headers)
    assert "Strict-Transport-Security" not in r.headers


def test_middleware_with_hsts(minimal_app_hsts):
    client = StarletteTestClient(minimal_app_hsts)
    r = client.get("/")
    assert r.status_code == 200
    _assert_core_security_headers(r.headers)
    hsts = r.headers.get("Strict-Transport-Security", "")
    assert "max-age=63072000" in hsts
    assert "includeSubDomains" in hsts


def test_fastapi_stack_includes_security_headers():
    """Misma pila que `app.main` (FastAPI + middleware) sin cargar la app real."""
    app = FastAPI()

    @app.get("/")
    def _root():
        return {"ok": True}

    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=False)
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    _assert_core_security_headers(r.headers)
    assert "Strict-Transport-Security" not in r.headers
