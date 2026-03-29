"""Console logging for HyperCore."""

from __future__ import annotations

import logging
import sys
from typing import Final

from hypercore.core.config import CORE_DEBUG, LOG_LEVEL

_LOGGER_NAME: Final[str] = "hypercore"
_RESET: Final[str] = "\033[0m"
_COLORS: Final[dict[int, str]] = {
    logging.DEBUG: "\033[36m",
    logging.INFO: "\033[32m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[35m",
}


class _ColorFormatter(logging.Formatter):
    def __init__(self, use_color: bool) -> None:
        super().__init__(datefmt="%Y-%m-%d %H:%M:%S")
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, self.datefmt)
        level_name = record.levelname.ljust(8)
        message = record.getMessage()
        if self._use_color:
            color = _COLORS.get(record.levelno, "")
            level_name = f"{color}{level_name}{_RESET}"
        return f"{timestamp} | {level_name} | {record.name} | {message}"


def _supports_color() -> bool:
    stream = getattr(sys, "stderr", None)
    return bool(stream and hasattr(stream, "isatty") and stream.isatty())


def configure_logging() -> logging.Logger:
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(_ColorFormatter(use_color=_supports_color()))
    root_logger.addHandler(handler)

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = True

    # Keep third-party transport logs from spamming the console or leaking tokens.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    return logger


def log_exception(logger: logging.Logger, message: str, exc: Exception) -> None:
    if CORE_DEBUG:
        logger.exception(message)
    else:
        logger.error("%s: %s", message, exc)


__all__ = ["configure_logging", "log_exception"]
