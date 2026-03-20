"""Servicos de leitura de fotos e galerias do catalogo."""

from __future__ import annotations

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def get_product_photos_payload(code: str | None = None, share_url: str | None = None) -> Dict:
    from .. import onedrive

    if code:
        try:
            local_photos = onedrive.categorize_local_photos(code=code)
            if any(local_photos.values()):
                return local_photos
            if onedrive.resolve_local_products_root():
                return local_photos
        except Exception as local_exc:
            logger.warning(
                "Local photo lookup failed, trying Graph fallback: %s",
                local_exc,
                exc_info=True,
            )

    if not share_url:
        raise ValueError("missing shareUrl query parameter")

    try:
        items = onedrive.list_shared_items(share_url)
        return onedrive.categorize_photos(items, code=code)
    except (EnvironmentError, ValueError) as exc:
        logger.warning("Photos disabled due to environment issue: %s", exc, exc_info=True)
        demo = {
            "white_background": "https://placehold.co/150x150?text=Branco",
            "ambient": "https://placehold.co/150x150?text=Ambient",
            "measures": "https://placehold.co/150x150?text=Medidas",
        }
        if code:
            demo = {key: value + f"+{code}" for key, value in demo.items()}
        return demo


def get_product_images_payload(code: str, share_url: str | None = None) -> Dict:
    from .. import onedrive

    try:
        local_images = onedrive.find_local_images_for_code(code)
        if local_images or onedrive.resolve_local_products_root():
            return {"codigo": code, "imagens": local_images}
    except Exception as local_exc:
        logger.warning(
            "Local image lookup failed, trying Graph fallback: %s",
            local_exc,
            exc_info=True,
        )

    if not share_url:
        raise ValueError("missing shareUrl query parameter")

    images = onedrive.find_images_for_code(share_url, code)
    return {"codigo": code, "imagens": images}
