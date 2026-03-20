"""Servicos de leitura de produtos do catalogo."""

from __future__ import annotations

import logging
from typing import Dict, List

from ..spreadsheet import fetch_sheet


logger = logging.getLogger(__name__)


def list_catalog_products() -> List[Dict]:
    from .. import onedrive

    return onedrive.list_local_products()


def fetch_sheet_or_local_products(url: str) -> List[Dict]:
    try:
        dataframe = fetch_sheet(url)
        return dataframe.to_dict(orient="records")
    except ValueError as exc:
        logger.warning("Sheet fetch failed, trying local fallback: %s", exc, exc_info=True)
        try:
            local_products = list_catalog_products()
            if local_products:
                return local_products
        except Exception as local_exc:
            logger.exception("Local products fallback failed after sheet fetch error: %s", local_exc)
        return []
