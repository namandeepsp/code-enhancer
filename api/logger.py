import logging
import logging.config
import os
import json
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for production — every log line is a valid JSON object.
    Designed to be parsed by log aggregators or surfaced to a frontend dashboard.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach extra fields if present
        for key in ("request_id", "task", "language", "technology", "status_code", "cached", "duration_ms"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


class ReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for development.
    """
    LEVEL_COLORS = {
        "DEBUG":    "\033[36m",   # cyan
        "INFO":     "\033[32m",   # green
        "WARNING":  "\033[33m",   # yellow
        "ERROR":    "\033[31m",   # red
        "CRITICAL": "\033[35m",   # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelname, "")
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        base = f"{color}[{record.levelname}]{self.RESET} {ts} {record.name}: {record.getMessage()}"

        extras = []
        for key in ("request_id", "task", "language", "technology", "status_code", "cached", "duration_ms"):
            if hasattr(record, key):
                extras.append(f"{key}={getattr(record, key)}")

        if extras:
            base += f"  ({', '.join(extras)})"

        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)

        return base


def setup_logging() -> None:
    env = os.getenv("ENVIRONMENT", "development")
    level = os.getenv("LOG_LEVEL", "DEBUG" if env == "development" else "INFO").upper()

    formatter = ReadableFormatter() if env == "development" else StructuredFormatter()

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "uvicorn.access", "diskcache"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
