"""Deterministic seeding for reproducible experiments.

Seeds Python's stdlib RNG always, and numpy / torch when they are
installed. Neither library is a dependency of this module.
"""
import importlib.util
import os
import random

DEFAULT_SEED = 42


def seed_everything(seed: int = DEFAULT_SEED) -> int:
    """Seed every available random number generator.

    Args:
        seed: The seed value applied to all RNGs.

    Returns:
        The seed that was applied, so callers can log it.
    """
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)

    if importlib.util.find_spec("numpy") is not None:
        import numpy

        numpy.random.seed(seed)

    if importlib.util.find_spec("torch") is not None:
        import torch

        torch.manual_seed(seed)

    return seed
