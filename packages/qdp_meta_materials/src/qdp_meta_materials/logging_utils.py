from __future__ import annotations

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure package logging once per process."""

    root_logger = logging.getLogger("mmm_studio")
    if root_logger.handlers:
        return
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced package logger."""

    configure_logging()
    return logging.getLogger(f"mmm_studio.{name}")
