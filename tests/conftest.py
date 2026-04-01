import os
import shutil
import sys
from pathlib import Path
from uuid import uuid4

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


LOCAL_TMP_ROOT = ROOT_DIR / ".pytest_tmp_local"
LOCAL_TMP_ROOT.mkdir(parents=True, exist_ok=True)

# Mantem os temporarios do pytest dentro do proprio projeto para evitar
# problemas com diretorios globais bloqueados em ambientes Windows.
for env_key in ("TMP", "TEMP", "TMPDIR", "PYTEST_DEBUG_TEMPROOT"):
    os.environ.setdefault(env_key, str(LOCAL_TMP_ROOT))


@pytest.fixture
def tmp_path():
    path = LOCAL_TMP_ROOT / f"case-{uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(autouse=True)
def isolate_runtime_environment(monkeypatch):
    for env_key in (
        "CATALOG_LOCAL_PRODUCTS_PATH",
        "CATALOG_CADASTRO_HTML",
        "CATALOG_STOCK_REPORT_PATH",
        "CATALOG_STOCK_PHOTOS_ROOT",
        "CATALOG_ERP_JSON_PATH",
        "CATALOG_ERP_INBOX_DIR",
        "CATALOG_ERP_SOURCE_DIRS",
        "CATALOG_ERP_ADMIN_TOKEN",
        "CATALOG_ERP_MAX_UPLOAD_BYTES",
        "CATALOG_ENABLE_API_DOCS",
        "CATALOG_EXPORT_MAX_REMOTE_IMAGE_BYTES",
        "OneDrive",
        "OneDriveCommercial",
        "OneDriveConsumer",
    ):
        monkeypatch.delenv(env_key, raising=False)

    monkeypatch.setenv("CATALOG_ERP_AUTO_DISCOVERY", "false")
    monkeypatch.setenv("CATALOG_STOCK_REPORT_AUTO_DISCOVERY", "false")
    monkeypatch.setenv("CATALOG_LOCAL_PRODUCTS_HOME_FALLBACK", "false")
    monkeypatch.setenv("CATALOG_STOCK_PHOTOS_HOME_FALLBACK", "false")
    monkeypatch.setenv(
        "CATALOG_ERP_JSON_PATH",
        str(LOCAL_TMP_ROOT / "disabled-erp.json"),
    )

    from catalog.cache import cache

    cache.store.clear()
    yield
    cache.store.clear()
