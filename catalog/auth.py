import os
import logging
import secrets
from typing import List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from msal import ConfidentialClientApplication, SerializableTokenCache
from dotenv import load_dotenv

# Carrega variaveis de ambiente do .env, se existir.
load_dotenv()
logger = logging.getLogger(__name__)

# Constantes de ambiente.
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
REDIRECT_URI = os.getenv("AZURE_REDIRECT_URI")

# Determina se as credenciais sao realmente utilizaveis; valores de placeholder
# como "seu-tenant-id" ou vazios devem desabilitar a autenticacao.
AUTH_CONFIGURED = all([CLIENT_ID, CLIENT_SECRET, TENANT_ID, REDIRECT_URI])
if AUTH_CONFIGURED:
    # Validacao simples para evitar valores ficticios evidentes.
    for val in (CLIENT_ID, CLIENT_SECRET, TENANT_ID):
        if "seu" in val.lower() or val.lower() == "none":
            AUTH_CONFIGURED = False
            break

if not AUTH_CONFIGURED:
    # A autenticacao sera desativada; chamadores devem tratar EnvironmentError.
    AUTHORITY = None
else:
    AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

SCOPES = ["Files.Read", "offline_access"]
STATE_COOKIE_NAME = "catalog_oauth_state"


def _resolve_cache_file() -> str:
    explicit = os.getenv("CATALOG_TOKEN_CACHE_FILE", "").strip()
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))

    app_data_root = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
    if app_data_root:
        return os.path.join(app_data_root, "catalogo", "token_cache.bin")
    return os.path.join(os.path.expanduser("~"), ".catalogo", "token_cache.bin")


def _ensure_cache_directory() -> None:
    cache_dir = os.path.dirname(CACHE_FILE)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)


def _cache_cookie_secure() -> bool:
    return bool(REDIRECT_URI and REDIRECT_URI.lower().startswith("https://"))


CACHE_FILE = _resolve_cache_file()

# Cache de token persistido em arquivo.
token_cache = SerializableTokenCache()
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as cache_handle:
            token_cache.deserialize(cache_handle.read())
    except Exception:
        # Ignora cache corrompido.
        logger.warning("Ignoring corrupted token cache at %s", CACHE_FILE, exc_info=True)
        token_cache = SerializableTokenCache()


def _save_cache():
    if token_cache.has_state_changed:
        _ensure_cache_directory()
        with open(CACHE_FILE, "w", encoding="utf-8") as cache_handle:
            cache_handle.write(token_cache.serialize())
        try:
            os.chmod(CACHE_FILE, 0o600)
        except OSError:
            # No Windows o chmod e limitado; mantemos best-effort.
            pass


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
    """Retorna um access token valido, adquirindo silenciosamente ou gerando 401.

    Se a autenticacao estiver desativada (sem credenciais), gera OSError para
    que o chamador use fallback com placeholders em vez de poluir logs com
    erros do MSAL.
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
    try:
        app = _build_msal_app()
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Azure authentication not configured") from exc
    state = secrets.token_urlsafe(32)
    auth_url = app.get_authorization_request_url(
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI,
    )
    response = RedirectResponse(auth_url)
    response.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        samesite="lax",
        secure=_cache_cookie_secure(),
        max_age=600,
    )
    return response


@auth_router.get("/auth/callback")
def callback(request: Request, code: str = None, state: str = None, error: str = None):
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    cookie_state = request.cookies.get(STATE_COOKIE_NAME)
    if not state or not cookie_state or not secrets.compare_digest(state, cookie_state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    try:
        app = _build_msal_app()
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Azure authentication not configured") from exc
    result = app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    _save_cache()
    if "access_token" in result:
        response = JSONResponse({"success": True})
        response.delete_cookie(
            STATE_COOKIE_NAME,
            httponly=True,
            samesite="lax",
            secure=_cache_cookie_secure(),
        )
        return response
    logger.warning("OAuth token exchange failed: %s", result)
    raise HTTPException(status_code=400, detail="OAuth token exchange failed")
