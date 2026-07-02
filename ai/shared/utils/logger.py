"""Logging for the AI module.

Standalone by design: does not import backend settings, so training
scripts can run without the FastAPI application installed or configured.
Loggers live under the 'firerescue.ai' namespace to stay consistent
with the backend's 'firerescue' hierarchy.
"""
import logging
import sys

_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)-28s %(message)s"
_DATE_FORMAT = "%H:%M:%S"
_ROOT_NAME = "firerescue.ai"


def get_logger(name: str = "", level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger under the 'firerescue.ai' namespace.

    The first call attaches a stdout handler to the namespace root;
    subsequent calls reuse it, so handlers are never duplicated.

    Args:
        name: Child name appended to 'firerescue.ai' (e.g. 'training').
              Empty string returns the namespace root itself.
        level: Log level applied to the namespace root.

    Returns:
        The requested logger.
    """
    root = logging.getLogger(_ROOT_NAME)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT))
        root.addHandler(handler)
        root.propagate = False
    root.setLevel(level)

    return logging.getLogger(f"{_ROOT_NAME}.{name}") if name else root
