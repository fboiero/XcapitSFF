"""Structured logging setup for XcapitSFF."""

import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """JSON-like structured formatter for production environments."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        request_id = getattr(record, "request_id", "-")
        log_entry = (
            f'{{"timestamp": "{timestamp}", '
            f'"level": "{record.levelname}", '
            f'"module": "{record.module}", '
            f'"message": "{record.getMessage()}", '
            f'"request_id": "{request_id}"}}'
        )
        if record.exc_info and record.exc_info[0] is not None:
            exc_text = self.formatException(record.exc_info)
            log_entry = log_entry[:-1] + f', "exception": "{exc_text}"}}'
        return log_entry


class DevFormatter(logging.Formatter):
    """Human-readable formatter for development environments."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        request_id = getattr(record, "request_id", "-")
        base = f"{timestamp} [{record.levelname:<8}] {record.module}: {record.getMessage()}"
        if request_id != "-":
            base = f"{timestamp} [{record.levelname:<8}] [{request_id}] {record.module}: {record.getMessage()}"
        if record.exc_info and record.exc_info[0] is not None:
            base += "\n" + self.formatException(record.exc_info)
        return base


def setup_logging(level: str = "INFO", environment: str = "development") -> None:
    """Configure root logging with the appropriate formatter.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        environment: 'production' for JSON output, anything else for readable output.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if environment == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(DevFormatter())

    root_logger = logging.getLogger()
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.WARNING if environment == "production" else log_level
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the given name.

    Convenience wrapper so modules can do::

        from xcapitsff.logging_config import get_logger
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)
