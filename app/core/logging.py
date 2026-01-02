"""
Logging configuration for the application.

Provides structured logging with configurable levels and formatters.
"""

import logging
import sys
from typing import Optional

from app.core.config import get_settings


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """
    Configure and return the application logger.
    
    Args:
        level: Optional logging level override. Defaults to DEBUG if debug mode,
               otherwise INFO.
    
    Returns:
        Configured logger instance for the application.
    """
    settings = get_settings()
    
    # Determine log level
    if level:
        log_level = getattr(logging, level.upper(), logging.INFO)
    elif settings.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure stream handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Configure application logger
    logger = logging.getLogger("breaking_bad")
    logger.setLevel(log_level)

    # Reduce noise from third-party libraries
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger.info(
        "Logging configured",
        extra={"level": logging.getLevelName(log_level), "debug": settings.debug},
    )
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: The name for the logger, typically __name__ of the calling module.
    
    Returns:
        Logger instance with the specified name.
    """
    return logging.getLogger(f"breaking_bad.{name}")
