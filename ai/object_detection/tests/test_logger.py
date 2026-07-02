"""Tests: ai.shared.utils.logger — namespace, handler reuse, isolation."""
import logging
import unittest

from ai.shared.utils.logger import get_logger


class TestGetLogger(unittest.TestCase):

    def test_root_logger_name(self):
        self.assertEqual(get_logger().name, "firerescue.ai")

    def test_child_logger_name(self):
        self.assertEqual(get_logger("training").name, "firerescue.ai.training")

    def test_handler_is_not_duplicated_across_calls(self):
        # Compare counts rather than assert an absolute number: pytest's
        # logging plugin attaches its own capture handlers to
        # non-propagating loggers.
        get_logger("a")
        root = logging.getLogger("firerescue.ai")
        before = len(root.handlers)
        get_logger("b")
        get_logger("a")
        self.assertEqual(len(root.handlers), before)

    def test_namespace_root_does_not_propagate(self):
        get_logger()
        self.assertFalse(logging.getLogger("firerescue.ai").propagate)

    def test_level_is_applied_to_namespace_root(self):
        get_logger(level=logging.DEBUG)
        self.assertEqual(logging.getLogger("firerescue.ai").level, logging.DEBUG)

    def test_same_name_returns_same_logger_instance(self):
        self.assertIs(get_logger("training"), get_logger("training"))


if __name__ == "__main__":
    unittest.main()
