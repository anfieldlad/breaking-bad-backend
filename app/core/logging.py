"""
Logging configuration for the application.

Every record carries the current request ID (see `app.api.middleware`).
Use `LOG_FORMAT=json` in production to emit one JSON object per line,
including any `extra={...}` fields, for log aggregation.
"""

import json
import logging
import sys
from contextvars import ContextVar

from app.core.config import Settings

#: ID of the HTTP request being handled ("-" outside of a request).
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s:%(lineno)d - %(message)s"
# Attributes every LogRecord has; anything else was passed via `extra=`.
_STANDARD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "request_id"}


class RequestIdFilter(logging.Filter):
    """Attach the current request ID to every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Format records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        payload.update({k: v for k, v in vars(record).items() if k not in _STANDARD_ATTRS})
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(settings: Settings) -> None:
    """Configure the root logger from settings (idempotent)."""
    level = logging.DEBUG if settings.debug else settings.log_level.upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        JsonFormatter()
        if settings.log_format == "json"
        else logging.Formatter(_TEXT_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    for noisy in ("pymongo", "urllib3", "httpx", "httpcore", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger namespaced under the application logger."""
    return logging.getLogger(f"breaking_bad.{name}")
