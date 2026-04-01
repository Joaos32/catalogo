import importlib
import os

from fastapi.testclient import TestClient

import catalog.auth as auth_module
from catalog.bootstrap import SECURITY_HEADERS, create_app
from catalog.core.settings import load_settings


def test_load_settings_uses_safe_local_cors_defaults():
    settings = load_settings()

    assert "*" not in settings.cors_allow_origins
    assert "http://127.0.0.1:5173" in settings.cors_allow_origins
    assert "http://localhost:8000" in settings.cors_allow_origins


def test_load_settings_exposes_optional_security_flags(monkeypatch):
    monkeypatch.setenv("CATALOG_ENABLE_API_DOCS", "false")
    monkeypatch.setenv("CATALOG_ERP_ADMIN_TOKEN", "super-secret-token")

    settings = load_settings()

    assert settings.api_docs_enabled is False
    assert settings.erp_admin_token == "super-secret-token"


def test_security_headers_are_present():
    client = TestClient(create_app())
    response = client.get("/")

    for header, value in SECURITY_HEADERS.items():
        assert response.headers.get(header.lower()) == value


def test_hsts_header_is_added_on_https():
    client = TestClient(create_app(), base_url="https://testserver")
    response = client.get("/")

    assert response.headers.get("strict-transport-security") == "max-age=63072000; includeSubDomains"


def test_api_docs_can_be_disabled(monkeypatch):
    monkeypatch.setenv("CATALOG_ENABLE_API_DOCS", "false")

    client = TestClient(create_app())

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_erp_routes_require_admin_token_when_configured(monkeypatch):
    monkeypatch.setenv("CATALOG_ERP_ADMIN_TOKEN", "super-secret-token")

    client = TestClient(create_app())

    missing = client.get("/catalog/erp/status")
    assert missing.status_code == 401
    assert missing.json() == {"detail": "ERP admin token required"}

    invalid = client.get(
        "/catalog/erp/status",
        headers={"X-Catalog-Admin-Token": "wrong-token"},
    )
    assert invalid.status_code == 403
    assert invalid.json() == {"detail": "Invalid ERP admin token"}

    valid = client.get(
        "/catalog/erp/status",
        headers={"X-Catalog-Admin-Token": "super-secret-token"},
    )
    assert valid.status_code == 200
    assert "products_loaded" in valid.json()


def test_erp_routes_accept_bearer_admin_token(monkeypatch):
    monkeypatch.setenv("CATALOG_ERP_ADMIN_TOKEN", "super-secret-token")

    client = TestClient(create_app())
    response = client.get(
        "/catalog/erp/status",
        headers={"Authorization": "Bearer super-secret-token"},
    )

    assert response.status_code == 200
    assert "products_loaded" in response.json()


def test_auth_cache_file_can_be_overridden(monkeypatch, tmp_path):
    target_cache = tmp_path / "secure-cache" / "token_cache.bin"
    monkeypatch.setenv("CATALOG_TOKEN_CACHE_FILE", str(target_cache))

    reloaded = importlib.reload(auth_module)
    try:
        assert reloaded.CACHE_FILE == os.path.abspath(str(target_cache))
    finally:
        monkeypatch.delenv("CATALOG_TOKEN_CACHE_FILE", raising=False)
        importlib.reload(auth_module)
