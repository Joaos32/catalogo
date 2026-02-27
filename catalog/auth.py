import os
from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from msal import ConfidentialClientApplication, SerializableTokenCache
from dotenv import load_dotenv

# load environment variables from .env if present
load_dotenv()

# constants / env
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
REDIRECT_URI = os.getenv("AZURE_REDIRECT_URI")

# determine whether we actually have usable credentials; a placeholder
# string like "seu-tenant-id" or an empty value should disable auth.
AUTH_CONFIGURED = all([CLIENT_ID, CLIENT_SECRET, TENANT_ID, REDIRECT_URI])
if AUTH_CONFIGURED:
    # simple sanity check against obvious dummy values
    for val in (CLIENT_ID, CLIENT_SECRET, TENANT_ID):
        if "seu" in val.lower() or val.lower() == "none":
            AUTH_CONFIGURED = False
            break

if not AUTH_CONFIGURED:
    # authentication will be disabled; callers should handle EnvironmentError
    AUTHORITY = None
else:
    AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

SCOPES = ["Files.Read", "offline_access"]
CACHE_FILE = os.path.join(os.getcwd(), "token_cache.bin")

# token cache that persists to a file
token_cache = SerializableTokenCache()
if os.path.exists(CACHE_FILE):
    try:
        token_cache.deserialize(open(CACHE_FILE, "r").read())
    except Exception:
        # ignore corrupted cache
        token_cache = SerializableTokenCache()


def _save_cache():
    if token_cache.has_state_changed:
        with open(CACHE_FILE, "w") as f:
            f.write(token_cache.serialize())


def _build_msal_app() -> ConfidentialClientApplication:
    if not AUTH_CONFIGURED:
        raise OSError("Azure credentials not set or invalid")
    return ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
        token_cache=token_cache,
    )


def get_access_token(scopes: List[str] = SCOPES) -> str:
    """Return a valid access token, acquiring silently or raising 401.

    If authentication is disabled (no credentials), raise OSError so the
    caller can fall back to placeholders instead of spamming logs with MSAL
    errors.
    """
    if not AUTH_CONFIGURED:
        raise OSError("Azure credentials not configured")
    app = _build_msal_app()
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]
    raise HTTPException(status_code=401, detail="User login required")


auth_router = APIRouter()


@auth_router.get("/auth/login")
def login():
    app = _build_msal_app()
    auth_url = app.get_authorization_request_url(
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    return RedirectResponse(auth_url)


@auth_router.get("/auth/callback")
def callback(code: str = None, error: str = None):
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    app = _build_msal_app()
    result = app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    _save_cache()
    if "access_token" in result:
        return JSONResponse({"success": True})
    else:
        raise HTTPException(status_code=400, detail=str(result))