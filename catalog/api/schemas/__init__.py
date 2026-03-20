"""Schemas tipados da API do catalogo."""

from .catalog import CatalogProductSchema
from .media import ProductImageSchema, ProductImagesResponseSchema, ProductPhotosSchema

__all__ = [
    "CatalogProductSchema",
    "ProductImageSchema",
    "ProductImagesResponseSchema",
    "ProductPhotosSchema",
]
