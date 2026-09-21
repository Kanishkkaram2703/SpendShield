"""Small centralized logging setup for the backend."""

from __future__ import annotations

import logging

LOGGER_NAME = "spendshield"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(level: str) -> None:
    """Configure standard-library logging with a consistent safe format."""

    logging.basicConfig(
        level=level.upper(),
        format=LOG_FORMAT,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger below the SpendShield namespace."""

    suffix = name.removeprefix(LOGGER_NAME).lstrip(".")
    return logging.getLogger(f"{LOGGER_NAME}.{suffix}" if suffix else LOGGER_NAME)


__all__ = ["configure_logging", "get_logger"]
