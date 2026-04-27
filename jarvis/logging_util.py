"""Structured logging integration with audit log."""
import json
import logging
import sys
from pathlib import Path
from typing import Any

from .audit import AuditLog
from .config import Config


class AuditLogHandler(logging.Handler):
    """Send logs to both audit log and console."""

    def __init__(self, audit_log: AuditLog):
        super().__init__()
        self.audit_log = audit_log

    def emit(self, record: logging.LogRecord) -> None:
        try:
            event_type = f"log_{record.levelname.lower()}"
            payload = {
                "logger": record.name,
                "message": record.getMessage(),
                "level": record.levelname,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            if record.exc_info:
                payload["exception"] = self.format(record)

            self.audit_log.append(event_type, payload)
        except Exception:
            self.handleError(record)


def setup_logging(config: Config | None = None) -> logging.Logger:
    """Configure structured logging with audit integration.
    
    Returns a logger that writes to both console and audit log.
    """
    if config is None:
        config = Config.from_env()

    config.audit_db.parent.mkdir(parents=True, exist_ok=True)
    audit_log = AuditLog(config.audit_db)

    # Create root logger
    logger = logging.getLogger("jarvis")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Console handler (INFO level for user-facing output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Audit handler (DEBUG level for complete tracing)
    audit_handler = AuditLogHandler(audit_log)
    audit_handler.setLevel(logging.DEBUG)
    logger.addHandler(audit_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a named logger (must call setup_logging first)."""
    return logging.getLogger(f"jarvis.{name}")
