"""Configuracao central de logging da aplicacao."""

from __future__ import annotations

import logging
import os


DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def _resolve_level(raw_value: str | None) -> int:
    level_name = str(raw_value or DEFAULT_LOG_LEVEL).strip().upper()
    return getattr(logging, level_name, logging.INFO)


def configure_logging() -> None:
    """Inicializa logging basico e ajusta o nivel global da aplicacao."""
    level = _resolve_level(os.getenv("CATALOG_LOG_LEVEL"))
    log_format = os.getenv("CATALOG_LOG_FORMAT", DEFAULT_LOG_FORMAT).strip() or DEFAULT_LOG_FORMAT
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        logging.basicConfig(level=level, format=log_format)
        return

    root_logger.setLevel(level)

