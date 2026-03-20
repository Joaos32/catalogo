"""Schemas de produto para respostas da API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CatalogProductSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    Codigo: str = ""
    Nome: str = ""
    Descricao: str = ""
    Categoria: str = ""
    URLFoto: str = ""
    Especificacoes: str = ""
    FotoBranco: str = ""
    FotoAmbient: str = ""
    FotoMedidas: str = ""
