"""Tests: ai.shared.utils.seed — deterministic RNG seeding."""
import os
import random
import unittest

from ai.shared.utils.seed import DEFAULT_SEED, seed_everything


class TestSeedEverything(unittest.TestCase):

    def test_returns_the_applied_seed(self):
        self.assertEqual(seed_everything(123), 123)

    def test_default_seed_is_used_when_omitted(self):
        self.assertEqual(seed_everything(), DEFAULT_SEED)

    def test_stdlib_random_becomes_deterministic(self):
        seed_everything(7)
        first = [random.random() for _ in range(5)]
        seed_everything(7)
        second = [random.random() for _ in range(5)]
        self.assertEqual(first, second)

    def test_different_seeds_give_different_sequences(self):
        seed_everything(1)
        first = [random.random() for _ in range(5)]
        seed_everything(2)
        second = [random.random() for _ in range(5)]
        self.assertNotEqual(first, second)

    def test_pythonhashseed_env_var_is_set(self):
        seed_everything(99)
        self.assertEqual(os.environ.get("PYTHONHASHSEED"), "99")


if __name__ == "__main__":
    unittest.main()
