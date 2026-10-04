import unittest
from datetime import date, timedelta

from flashcardslite import leiter
from flashcardslite.leiter import (
    MAX_BOX,
    apply_answer,
    due_date,
    interval_for_box,
    is_due,
    next_box_on_correct,
    bucket_summary,
)


class TestIntervals(unittest.TestCase):
    def test_intervals_monotonic_increasing(self):
        prev = 0
        for box in range(1, MAX_BOX + 1):
            iv = interval_for_box(box)
            self.assertGreater(iv, prev)
            prev = iv

    def test_interval_clamps_out_of_range(self):
        self.assertEqual(interval_for_box(0), interval_for_box(1))
        self.assertEqual(interval_for_box(99), interval_for_box(MAX_BOX))


class TestBoxMovement(unittest.TestCase):
    def test_correct_advances_box(self):
        self.assertEqual(next_box_on_correct(1), 2)
        self.assertEqual(next_box_on_correct(2), 3)

    def test_correct_caps_at_max(self):
        self.assertEqual(next_box_on_correct(MAX_BOX), MAX_BOX)
        self.assertEqual(next_box_on_correct(MAX_BOX - 1), MAX_BOX)

    def test_wrong_returns_to_box_one(self):
        today = date(2026, 1, 1)
        result = apply_answer(box=4, correct=False, last_reviewed=today)
        self.assertEqual(result["box"], 1)

    def test_correct_moves_up_and_extends_due(self):
        today = date(2026, 1, 1)
        r1 = apply_answer(box=1, correct=True, last_reviewed=today)
        self.assertEqual(r1["box"], 2)
        # 升到 2 盒，间隔应为 interval_for_box(2) 天
        self.assertEqual(r1["due"], today + timedelta(days=interval_for_box(2)))


class TestDueCalculation(unittest.TestCase):
    def test_due_date_adds_interval(self):
        last = date(2026, 3, 1)
        self.assertEqual(due_date(1, last), date(2026, 3, 2))
        self.assertEqual(due_date(3, last), last + timedelta(days=interval_for_box(3)))

    def test_is_due(self):
        due = date(2026, 5, 1)
        self.assertTrue(is_due(box=1, due=due, today=date(2026, 5, 1)))
        self.assertTrue(is_due(box=1, due=due, today=date(2026, 5, 10)))
        self.assertFalse(is_due(box=1, due=due, today=date(2026, 4, 30)))


class TestSummary(unittest.TestCase):
    def test_bucket_summary_counts(self):
        today = date(2026, 6, 1)
        cards = [
            {"box": 1, "due": "2026-05-30"},   # 到期
            {"box": 1, "due": "2026-06-10"},   # 未到期
            {"box": 3, "due": "2026-06-01"},   # 到期
            {"box": 5, "due": "2026-07-01"},
        ]
        s = bucket_summary(cards, today)
        self.assertEqual(s[1]["total"], 2)
        self.assertEqual(s[1]["due"], 1)
        self.assertEqual(s[3]["total"], 1)
        self.assertEqual(s[3]["due"], 1)
        self.assertEqual(s[5]["due"], 0)


if __name__ == "__main__":
    unittest.main()
