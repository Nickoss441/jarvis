"""Tests for structured logging utility."""
import logging

from jarvis.logging_util import setup_logging, get_logger
from jarvis.config import Config


def test_setup_logging_creates_jarvis_logger(tmp_path, monkeypatch):
    """Test that setup_logging initializes the logging system."""
    audit_db = tmp_path / "audit.db"
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))

    config = Config.from_env()
    logger = setup_logging(config)

    assert logger.name == "jarvis"
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 2  # console + audit


def test_get_logger_returns_child_logger():
    """Test that get_logger returns a properly named child logger."""
    logger = get_logger("test_module")

    assert logger.name == "jarvis.test_module"
    assert isinstance(logger, logging.Logger)


def test_logging_to_audit_handler(tmp_path, monkeypatch, capsys):
    """Test that logs are written to both console and audit log."""
    audit_db = tmp_path / "audit.db"
    approval_db = tmp_path / "approvals.db"
    monkeypatch.setenv("JARVIS_AUDIT_DB", str(audit_db))
    monkeypatch.setenv("JARVIS_APPROVAL_DB", str(approval_db))

    config = Config.from_env()
    logger = setup_logging(config)

    logger.info("Test info message")
    logger.warning("Test warning message")

    out = capsys.readouterr().out
    assert "Test info message" in out
    assert "Test warning message" in out

    from jarvis.audit import AuditLog
    audit_log = AuditLog(audit_db)
    log_events = audit_log.recent(limit=100, kind="log_info")
    assert len(log_events) >= 1
