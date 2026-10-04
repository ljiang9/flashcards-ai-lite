import json
import os
import tempfile
import unittest
from datetime import date, timedelta

from flashcardslite.extractor import Card
from flashcardslite.leiter import apply_answer
from flashcardslite.store import CardStore


class TestCardStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.store = CardStore(self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_add_and_persist(self):
        cards = [
            Card(type="cloze", front="水的化学式是 ____", back="H2O"),
            Card(type="qa", front="什么是光合作用？", back="植物利用光能合成有机物"),
        ]
        added = self.store.add_cards("default", cards, today=date(2026, 1, 1))
        self.assertEqual(added, 2)
        self.store.save()

        # 重新加载，验证 JSON 落盘
        reloaded = CardStore(self.tmp.name)
        self.assertEqual(len(reloaded.cards("default")), 2)
        with open(self.tmp.name, encoding="utf-8") as f:
            raw = json.load(f)
        self.assertIn("default", raw)

    def test_duplicate_cards_skipped(self):
        c = Card(type="qa", front="Q?", back="A")
        self.assertEqual(self.store.add_cards("d1", [c]), 1)
        self.assertEqual(self.store.add_cards("d1", [c]), 0)

    def test_new_card_starts_in_box1_due_today(self):
        self.store.add_cards("d", [Card(type="qa", front="Q", back="A")], today=date(2026, 2, 1))
        card = self.store.cards("d")[0]
        self.assertEqual(card["box"], 1)
        self.assertEqual(card["due"], "2026-02-01")

    def test_update_card_advances_and_records(self):
        self.store.add_cards("d", [Card(type="qa", front="Q", back="A")], today=date(2026, 3, 1))
        card = self.store.cards("d")[0]
        today = date(2026, 3, 1)
        result = apply_answer(box=1, correct=True, last_reviewed=today)
        self.store.update_card("d", card["id"], box=result["box"], due=result["due"],
                               correct=True, today=today)
        updated = self.store.cards("d")[0]
        self.assertEqual(updated["box"], 2)
        self.assertEqual(updated["correct"], 1)
        self.assertEqual(updated["wrong"], 0)
        self.store.save()
        # 落盘后再读
        again = CardStore(self.tmp.name).cards("d")[0]
        self.assertEqual(again["box"], 2)

    def test_update_nonexistent_raises(self):
        with self.assertRaises(KeyError):
            self.store.update_card("x", "nope", box=1, due=date(2026, 1, 1),
                                   correct=True, today=date(2026, 1, 1))

    def test_missing_file_loads_empty(self):
        path = os.path.join(tempfile.gettempdir(), "no_such_file_xyz.json")
        if os.path.exists(path):
            os.unlink(path)
        s = CardStore(path)
        self.assertEqual(s.decks(), [])
        os.path.exists(path) and os.unlink(path)


if __name__ == "__main__":
    unittest.main()
