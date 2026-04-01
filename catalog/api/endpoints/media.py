"""Endpoints de fotos, imagens e recursos de midia do catalogo."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..errors import internal_server_error_response
from ..schemas import ProductImagesResponseSchema, ProductPhotosSchema
from ...services import get_product_images_payload, get_product_photos_payload


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/photos", response_model=ProductPhotosSchema)
async def photos(shareUrl: str | None = None, code: str | None = None):
    """Retorna URLs de fotos categorizadas do OneDrive local ou Microsoft Graph."""
    try:
        return get_product_photos_payload(code=code, share_url=shareUrl)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:
        logger.exception("Error fetching photos: %s", exc)
        return internal_server_error_response()


@router.get("/produtos/{codigo}/imagens", response_model=ProductImagesResponseSchema)
async def product_images(codigo: str, shareUrl: str | None = None):
    """Retorna todas as variacoes de imagem para um codigo de produto."""
    try:
        return get_product_images_payload(codigo, share_url=shareUrl)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:
        logger.exception("Error searching product images: %s", exc)
        return internal_server_error_response()
