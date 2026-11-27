import unittest
from datetime import datetime

from smartcal.models import FixedEvent, Task
from smartcal.validation import ValidationError, parse_dt, validate_event, validate_task

NOW = datetime(2026, 3, 2, 8, 0)


class ValidationTest(unittest.TestCase):
    def test_parse_date(self):
        self.assertEqual(parse_dt("02.03.2026 14:30"), datetime(2026, 3, 2, 14, 30))
        with self.assertRaises(ValidationError):
            parse_dt("2026-03-02")

    def test_overlapping_event_rejected(self):
        a = FixedEvent("Лекція", datetime(2026, 3, 2, 10), datetime(2026, 3, 2, 12), 1)
        b = FixedEvent("Тренування", datetime(2026, 3, 2, 11), datetime(2026, 3, 2, 13))
        with self.assertRaises(ValidationError):
            validate_event(b, [a])

    def test_task_deadline_in_past(self):
        with self.assertRaises(ValidationError):
            validate_task(Task("X", datetime(2026, 3, 1, 10), 2), NOW)

    def test_task_duration_range(self):
        with self.assertRaises(ValidationError):
            validate_task(Task("X", datetime(2026, 3, 5, 10), 0), NOW)
        validate_task(Task("X", datetime(2026, 3, 5, 10), 0.5), NOW)


if __name__ == "__main__":
    unittest.main()
