from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import sys

# log which python interpreter is running the app
print(f"[startup] using python executable: {sys.executable}")

# CORS middleware is included with FastAPI/Starlette
try:
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    CORSMiddleware = None
    print("WARNING: fastapi CORS middleware not installed; cross-origin requests may fail.")

app = FastAPI()

if CORSMiddleware is not None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    print("CORS support disabled; ensure frontend is served from same origin or install fastapi.")

# import and include API router before static mount
from catalog.routes import router as catalog_router
app.include_router(catalog_router, prefix="/catalog")

# serve frontend static files; html=True makes index.html the fallback
# the router is mounted first so any /catalog/* request is handled by the API
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

if __name__ == "__main__":
    # using uvicorn to start the ASGI server
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, log_level="info")
