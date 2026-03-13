import os
from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from msal import ConfidentialClientApplication, SerializableTokenCache
from dotenv import load_dotenv

# Carrega variaveis de ambiente do .env, se existir.
load_dotenv()

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
CACHE_FILE = os.path.join(os.getcwd(), "token_cache.bin")

# Cache de token persistido em arquivo.
token_cache = SerializableTokenCache()
if os.path.exists(CACHE_FILE):
    try:
        token_cache.deserialize(open(CACHE_FILE, "r").read())
    except Exception:
        # Ignora cache corrompido.
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
