"""Dependencias e utilitarios de seguranca da API."""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

from catalog.core import load_settings


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def require_erp_admin(
    x_catalog_admin_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Protege rotas de ERP com token administrativo opcional."""
    configured_token = load_settings().erp_admin_token
    if not configured_token:
        return

    provided_token = x_catalog_admin_token or _extract_bearer_token(authorization)
    if not provided_token:
        raise HTTPException(status_code=401, detail="ERP admin token required")
    if not secrets.compare_digest(provided_token, configured_token):
        raise HTTPException(status_code=403, detail="Invalid ERP admin token")
