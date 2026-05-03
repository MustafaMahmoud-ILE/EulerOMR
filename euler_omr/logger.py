"""Centralized structlog/logging setup; rotating file handler + Qt signal handler for UI log panel."""

import logging
import logging.handlers
import os
import sys

import structlog
from PySide6.QtCore import QObject, Signal, QStandardPaths


class QtLogSignalEmitter(QObject):
    """Emits Qt signals for each log record so the UI log panel can display them."""
    log_record = Signal(str, str)  # (formatted_message, level_name)


class QtLogSignalHandler(logging.Handler):
    """Custom logging.Handler that emits a Qt signal per record."""

    def __init__(self, emitter: QtLogSignalEmitter):
        super().__init__()
        self.emitter = emitter

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.emitter.log_record.emit(msg, record.levelname)
        except Exception:
            self.handleError(record)


# Global signal emitter — connect to LogPanelWidget.append_log
_qt_emitter = QtLogSignalEmitter()


def get_qt_log_emitter() -> QtLogSignalEmitter:
    """Return the global Qt log signal emitter."""
    return _qt_emitter


def setup_logging():
    """Configure structlog + standard logging with rotating file and Qt signal handlers."""
    # Determine log directory
    data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    log_dir = os.path.join(data_dir, "EulerOMR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "euler_omr.log")

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Rotating file handler — JSON lines
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Qt signal handler
    qt_handler = QtLogSignalHandler(_qt_emitter)
    qt_handler.setLevel(logging.DEBUG)
    qt_formatter = logging.Formatter("[%(levelname)s] %(asctime)s | %(message)s")
    qt_handler.setFormatter(qt_formatter)
    root_logger.addHandler(qt_handler)

    # Console handler for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
