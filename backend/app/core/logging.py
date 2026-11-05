"""Central logging configuration for the backend service."""

from __future__ import annotations

import logging.config
import json

from app.core.config import get_settings


class JsonFormatter(logging.Formatter):
    """Support the documented JSON logging mode using only the standard library."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {"time": self.formatTime(record), "level": record.levelname, "logger": record.name, "message": record.getMessage()}
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """Configure structured console logging for local and container runtime."""
    settings = get_settings()
    formatter = {"()": JsonFormatter} if settings.log_format.strip().lower() == "json" else {"format": settings.log_format}
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": formatter
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

