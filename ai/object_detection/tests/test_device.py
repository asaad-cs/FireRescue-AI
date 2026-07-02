"""Tests: ai.shared.utils.device — device resolution without requiring a GPU."""
import unittest
from unittest.mock import patch

from ai.shared.utils.device import cuda_available, select_device


class TestSelectDevice(unittest.TestCase):

    def test_cpu_is_always_allowed(self):
        self.assertEqual(select_device("cpu"), "cpu")

    def test_auto_picks_cuda_when_available(self):
        with patch("ai.shared.utils.device.cuda_available", return_value=True):
            self.assertEqual(select_device("auto"), "cuda")

    def test_auto_falls_back_to_cpu(self):
        with patch("ai.shared.utils.device.cuda_available", return_value=False):
            self.assertEqual(select_device("auto"), "cpu")

    def test_explicit_cuda_without_gpu_raises(self):
        with patch("ai.shared.utils.device.cuda_available", return_value=False):
            with self.assertRaises(ValueError):
                select_device("cuda")

    def test_cuda_index_with_gpu_is_returned(self):
        with patch("ai.shared.utils.device.cuda_available", return_value=True):
            self.assertEqual(select_device("0"), "0")

    def test_unknown_device_raises(self):
        with self.assertRaises(ValueError):
            select_device("tpu")

    def test_request_is_case_insensitive(self):
        self.assertEqual(select_device(" CPU "), "cpu")


class TestCudaAvailable(unittest.TestCase):

    def test_returns_a_bool(self):
        self.assertIsInstance(cuda_available(), bool)


if __name__ == "__main__":
    unittest.main()
