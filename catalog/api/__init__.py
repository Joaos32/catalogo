"""Composicao da interface HTTP da aplicacao de catalogo."""


def register_api_routes(app):
    from .router import register_api_routes as _register_api_routes

    return _register_api_routes(app)


def register_frontend_routes(app, frontend_dir, index_file):
    from .frontend import register_frontend_routes as _register_frontend_routes

    return _register_frontend_routes(
        app,
        frontend_dir=frontend_dir,
        index_file=index_file,
    )


__all__ = ["register_api_routes", "register_frontend_routes"]
