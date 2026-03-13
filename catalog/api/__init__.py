"""Composicao da interface HTTP da aplicacao de catalogo."""

from .frontend import register_frontend_routes
from .router import register_api_routes

__all__ = ["register_api_routes", "register_frontend_routes"]
