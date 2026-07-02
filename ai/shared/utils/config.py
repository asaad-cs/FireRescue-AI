"""Generic YAML configuration machinery shared by all AI modules.

Module-specific config schemas (dataclasses and loaders) live in the
owning module, such as ai/object_detection/config.py.
"""
from pathlib import Path

import yaml


class ConfigError(ValueError):
    """A configuration file is missing, malformed, or inconsistent."""


def load_yaml(path: Path) -> dict:
    """Load a YAML file into a dict.

    Args:
        path: File to read.

    Returns:
        The parsed mapping.

    Raises:
        ConfigError: If the file is missing or not a YAML mapping.
    """
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ConfigError(f"Config file is not a YAML mapping: {path}")
    return data


def require(data: dict, key: str, source: str) -> object:
    """Return data[key] or raise ConfigError naming the file and key.

    Args:
        data: Parsed YAML mapping.
        key: Required key.
        source: Label for error messages (usually the file name).

    Returns:
        The value at data[key].

    Raises:
        ConfigError: If the key is absent.
    """
    if key not in data:
        raise ConfigError(f"{source}: missing required key '{key}'")
    return data[key]
