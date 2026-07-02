"""
Centralized logging configuration.

Call setup_logging() once at startup. All modules then use
logging.getLogger('firerescue.<module>') to write structured log lines.
"""
import logging
import sys

from backend.config.settings import settings

_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)-28s %(message)s"
_DATE_FORMAT = "%H:%M:%S"


def setup_logging() -> logging.Logger:
    """Configure the root logger and return the application root logger."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level, logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)

    return logging.getLogger("firerescue")


logger = setup_logging()
