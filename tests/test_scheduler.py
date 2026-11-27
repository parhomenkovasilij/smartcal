import unittest
from datetime import datetime, timedelta

from smartcal.models import Block, FixedEvent, Settings, Task
from smartcal.scheduler import find_free_windows, plan, split_task

NOW = datetime(2026, 3, 2, 8, 0)  # понеділок
S = Settings()


class FreeWindowsTest(unittest.TestCase):
    def test_event_cuts_window(self):
        busy = [(datetime(2026, 3, 2, 10, 0), datetime(2026, 3, 2, 12, 0))]
        w = find_free_windows(busy, NOW, datetime(2026, 3, 2, 23, 0), S)
        self.assertEqual(w, [(NOW, datetime(2026, 3, 2, 10, 0)),
                             (datetime(2026, 3, 2, 12, 0), datetime(2026, 3, 2, 22, 0))])


class SplitTest(unittest.TestCase):
    def test_sum_of_blocks_equals_duration(self):
        task = Task("Презентація", datetime(2026, 3, 4, 20, 0), 5, 1, id=1)
        windows = find_free_windows([], NOW, task.deadline, S)
        blocks, deficit = split_task(task, 5, windows, S)
        self.assertAlmostEqual(sum(b.hours for b in blocks), 5)
        self.assertEqual(deficit, 0)
        self.assertTrue(all(S.min_block_h <= b.hours <= S.max_block_h for b in blocks))

    def test_last_block_not_longer_than_remaining(self):
        """Регресійний тест для DEF-001: останній блок не перевищує залишок годин."""
        task = Task("Звіт", datetime(2026, 3, 4, 20, 0), 3, 2, id=1)
        blocks, _ = split_task(task, 3, find_free_windows([], NOW, task.deadline, S), S)
        self.assertEqual([b.hours for b in blocks], [2, 1])

    def test_deficit_when_deadline_too_close(self):
        task = Task("Курсова", NOW + timedelta(hours=3), 10, 1, id=1)
        result = plan([task], [], NOW, S)
        self.assertIn(1, result.deficits)
        self.assertGreater(result.deficits[1], 7)

    def test_blocks_do_not_overlap_events(self):
        ev = FixedEvent("Лекція", datetime(2026, 3, 2, 8, 30), datetime(2026, 3, 2, 10, 0), 1)
        task = Task("Лаба", datetime(2026, 3, 2, 22, 0), 3, 2, id=1)
        result = plan([task], [ev], NOW, S)
        for b in result.blocks:
            self.assertFalse(ev.overlaps(b.start, b.end))


class ReplanTest(unittest.TestCase):
    def test_done_hours_are_subtracted(self):
        task = Task("Звіт", datetime(2026, 3, 5, 20, 0), 4, 2, id=1)
        done = [Block(1, NOW, NOW + timedelta(hours=2), "done", 1)]
        result = plan([task], [], NOW + timedelta(hours=3), S, done)
        self.assertAlmostEqual(sum(b.hours for b in result.blocks), 2)

    def test_skipped_hours_are_rescheduled(self):
        task = Task("Звіт", datetime(2026, 3, 5, 20, 0), 4, 2, id=1)
        skipped = [Block(1, NOW, NOW + timedelta(hours=2), "skipped", 1)]
        result = plan([task], [], NOW + timedelta(hours=3), S, skipped)
        self.assertAlmostEqual(sum(b.hours for b in result.blocks), 4)
        self.assertTrue(all(b.start >= NOW + timedelta(hours=3) for b in result.blocks))

    def test_skipped_slot_is_not_reused(self):
        """Регресійний тест для DEF-002: пропущений слот не займається повторно."""
        task = Task("Звіт", datetime(2026, 3, 5, 20, 0), 4, 2, id=1)
        skipped = Block(1, NOW, NOW + timedelta(hours=2), "skipped", 1)
        result = plan([task], [], NOW, S, [skipped])
        for b in result.blocks:
            self.assertFalse(b.start < skipped.end and skipped.start < b.end)


if __name__ == "__main__":
    unittest.main()
