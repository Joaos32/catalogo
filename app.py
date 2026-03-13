from catalog.bootstrap import create_app
from catalog.core import load_settings


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = load_settings()
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
