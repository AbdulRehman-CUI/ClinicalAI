"""Central logging configuration for the backend service."""

from __future__ import annotations

import logging.config

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure structured console logging for local and container runtime."""
    settings = get_settings()
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": settings.log_format,
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                }
            },
            "root": {
                "handlers": ["console"],
                "level": settings.log_level.upper(),
            },
        }
    )

