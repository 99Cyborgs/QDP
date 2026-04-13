"""Run logger configuration."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logger(log_path: str | Path, append: bool = False) -> logging.Logger:
    """Create a logger that writes to stdout and the run log."""

    logger = logging.getLogger(f"tdgl_rf.{Path(log_path).resolve()}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_path, mode="a" if append else "w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger


def close_logger(logger: logging.Logger | None) -> None:
    """Flush and close handlers so temporary run directories can be cleaned up."""

    if logger is None:
        return
    handlers = list(logger.handlers)
    for handler in handlers:
        try:
            handler.flush()
        finally:
            handler.close()
        logger.removeHandler(handler)

