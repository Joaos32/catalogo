"""Exportacoes publicas do pacote de catalogo.

Nota de compatibilidade:
`catalog_router` e mantido como alias para `catalog.routes.router` para que
imports legados continuem funcionando com registro explicito de rotas.
"""

from .routes import router as catalog_router


def create_app():
    from .bootstrap import create_app as _create_app

    return _create_app()


__all__ = ["create_app", "catalog_router"]
