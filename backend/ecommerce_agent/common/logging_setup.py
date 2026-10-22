"""Logging setup for the application entrypoints."""
from __future__ import annotations

import logging

_PACKAGE_LOGGER = "ecommerce_agent"


def configure_logging(level: int = logging.INFO) -> None:
    """Send ecommerce_agent logs to stderr.

    Uvicorn only configures its own loggers, so package loggers are silent by
    default. Kept out of ``create_app`` so tests stay quiet.
    """
    logger = logging.getLogger(_PACKAGE_LOGGER)
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
