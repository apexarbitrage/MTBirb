"""Structured application logging.

The app previously used bare loggers with no configuration, so log level/format weren't tunable
and production had no machine-readable logs. `configure_logging()` wires a single stdout handler
via dictConfig; LOG_FORMAT=json emits one JSON object per line (for a log aggregator), the default
"plain" is human-readable for local dev. Called once at startup (app/main.py). Uvicorn's own
loggers keep their handlers - we only own the root + our app loggers.
"""

from __future__ import annotations

import json
import logging
from logging.config import dictConfig

from app.config import get_settings


class JsonFormatter(logging.Formatter):
    """One JSON object per record: ts, level, logger, message, and the traceback when present."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    settings = get_settings()
    level = settings.log_level.upper()
    if settings.log_format.lower() == "json":
        formatter = {"()": "app.logging_config.JsonFormatter"}
    else:
        formatter = {"format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s"}

    dictConfig(
        {
            "version": 1,
            # Don't clobber uvicorn's / third-party loggers - just (re)configure the root.
            "disable_existing_loggers": False,
            "formatters": {"default": formatter},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"handlers": ["console"], "level": level},
        }
    )
