import logging

from django.test import SimpleTestCase

from core.logging import JSONFormatter


class JSONFormatterTest(SimpleTestCase):
    def test_formats_basic_log(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        self.assertIn('"message": "Test message"', result)
        self.assertIn('"level": "INFO"', result)
        self.assertIn('"timestamp":', result)

    def test_formats_with_request_id(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.request_id = "req-123"

        result = formatter.format(record)

        self.assertIn('"request_id": "req-123"', result)

    def test_formats_with_exception(self):
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)

        self.assertIn('"exception":', result)
        self.assertIn("ValueError", result)
