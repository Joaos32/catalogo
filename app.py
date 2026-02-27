from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import sys
from dotenv import load_dotenv

# load .env early (auth module also does this, but load here for completeness)
load_dotenv()

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
from catalog.auth import auth_router

app.include_router(auth_router)
app.include_router(catalog_router, prefix="/catalog")

# serve frontend files manually to avoid swallowing API routes
# the API routers are included above, so they take precedence over these
from fastapi.responses import FileResponse
import os

@app.get("/")
def index():
    return FileResponse(os.path.join("frontend", "index.html"))

@app.get("/{full_path:path}")
def spa(full_path: str):
    # if the requested file exists under frontend, serve it; otherwise return index
    full_path = os.path.join("frontend", full_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return FileResponse(full_path)
    return FileResponse(os.path.join("frontend", "index.html"))

if __name__ == "__main__":
    # using uvicorn to start the ASGI server
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, log_level="info")
