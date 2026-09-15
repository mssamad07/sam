"""
Structured, centralized logging for Project Sam.
Supports correlation IDs, secret masking, and standard Python logging integration.
"""
import contextvars
import logging
import re
import sys
from pathlib import Path

# Context variable for tracing request / correlation IDs across async calls
correlation_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)

# Regex patterns for masking sensitive values
SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(api[-_]?key|secret|token|password|bearer\s+)['\":=\s]*([a-zA-Z0-9_\-\.]{8,})"),
]


def set_correlation_id(cid: str) -> None:
    """Set the current async context's correlation ID."""
    correlation_id_ctx.set(cid)


def get_correlation_id() -> str | None:
    """Retrieve the active correlation ID for the current context."""
    return correlation_id_ctx.get()


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    correlation_id_ctx.set(None)


def mask_sensitive_data(message: str) -> str:
    """Mask credentials and tokens in log strings."""
    if not isinstance(message, str):
        return message
    masked = message
    for pattern in SENSITIVE_PATTERNS:
        masked = pattern.sub(r"\1=***MASKED***", masked)
    return masked


class StructuredLogRecord(logging.LogRecord):
    """Custom LogRecord that automatically masks secrets and attaches correlation_id."""

    def getMessage(self) -> str:
        msg = super().getMessage()
        return mask_sensitive_data(msg)


class CorrelationIdFilter(logging.Filter):
    """Filter that injects the active correlation_id into the log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        cid = get_correlation_id()
        record.correlation_id = f"[{cid}] " if cid else ""
        return True


class StructuredFormatter(logging.Formatter):
    """Color-coded development formatter for console output."""

    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        cid = getattr(record, "correlation_id", "")
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level_str = f"{color}{record.levelname:<8}{self.RESET}"
        origin = f"{record.name}:{record.funcName}:{record.lineno}"
        msg = record.getMessage()

        return f"{timestamp} | {level_str} | {cid}{origin} - {msg}"


def setup_logging(
    level: str = "INFO",
    logs_dir: Path | None = None,
    log_to_file: bool = True,
) -> logging.Logger:
    """
    Initialize and configure the centralized logging system.
    """
    logging.setLogRecordFactory(StructuredLogRecord)
    root_logger = logging.getLogger("sam")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    console_handler.addFilter(CorrelationIdFilter())
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)

    # Optional File Handler
    if log_to_file and logs_dir:
        logs_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(logs_dir / "sam.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.addFilter(CorrelationIdFilter())
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(correlation_id)s%(name)s:%(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Retrieve a namespaced logger under the 'sam' hierarchy."""
    if name.startswith("sam.") or name == "sam":
        return logging.getLogger(name)
    return logging.getLogger(f"sam.{name}")
