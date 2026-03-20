"""Schemas de fotos e galerias para respostas da API."""

from __future__ import annotations

from pydantic import BaseModel


class ProductPhotosSchema(BaseModel):
    white_background: str | None = None
    ambient: str | None = None
    measures: str | None = None


class ProductImageSchema(BaseModel):
    name: str = ""
    variant: int = 0
    url: str = ""


class ProductImagesResponseSchema(BaseModel):
    codigo: str
    imagens: list[ProductImageSchema]
