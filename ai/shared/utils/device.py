"""Compute device selection.

torch is imported lazily so config validation and tests never require
the ML stack to be installed.
"""


def cuda_available() -> bool:
    """Return True if torch is installed and reports a usable CUDA device."""
    try:
        import torch
    except ImportError:
        return False
    return torch.cuda.is_available()


def select_device(requested: str = "auto") -> str:
    """Resolve a device request to a concrete device string.

    Args:
        requested: 'auto', 'cpu', 'cuda', or an explicit CUDA index
            such as '0'. 'auto' picks 'cuda' when available, else 'cpu'.

    Returns:
        The device string to pass to Ultralytics ('cpu', 'cuda', or index).

    Raises:
        ValueError: If a CUDA device is requested but none is available.
    """
    requested = requested.strip().lower()
    if requested == "auto":
        return "cuda" if cuda_available() else "cpu"
    if requested == "cpu":
        return "cpu"
    if requested == "cuda" or requested.isdigit():
        if not cuda_available():
            raise ValueError(
                f"Device '{requested}' requested but CUDA is not available. "
                "Use 'auto' or 'cpu'."
            )
        return requested
    raise ValueError(f"Unknown device '{requested}'. Use 'auto', 'cpu', 'cuda', or an index.")
