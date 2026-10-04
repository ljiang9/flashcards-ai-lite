import unittest

from flashcardslite.extractor import (
    Card,
    extract_cards,
    split_sentences,
    _make_cloze,
    _make_qa_from_def,
)


class TestSplitSentences(unittest.TestCase):
    def test_split_chinese_and_english(self):
        text = "光合作用是植物利用光能的过程。它把二氧化碳转成糖！Photosynthesis is key."
        sents = split_sentences(text)
        self.assertGreaterEqual(len(sents), 3)
        self.assertTrue(any("光合作用" in s for s in sents))

    def test_too_short_sentences_ignored(self):
        sents = split_sentences("好。今天学习。光合作用是植物利用光能合成有机物的过程。")
        # "好。" 只有两个字符会被过滤
        self.assertFalse(any(s == "好。" for s in sents))


class TestCloze(unittest.TestCase):
    def test_cloze_masks_term_once(self):
        sent = "光合作用是植物利用光能合成有机物的过程。"
        card = _make_cloze(sent, "光合作用")
        self.assertIsNotNone(card)
        self.assertEqual(card.type, "cloze")
        self.assertIn("____", card.front)
        self.assertEqual(card.back, "光合作用")

    def test_cloze_skip_when_term_repeated(self):
        sent = "光合作用让植物进行光合作用，很重要。"
        self.assertIsNone(_make_cloze(sent, "光合作用"))

    def test_extract_quoted_terms(self):
        text = "我们学习「间隔重复」这个记忆方法。它能显著提升长期记忆效果。"
        cards = extract_cards(text)
        cloze = [c for c in cards if c.type == "cloze"]
        self.assertTrue(any(c.back == "间隔重复" for c in cloze))


class TestQA(unittest.TestCase):
    def test_chinese_definition_qa(self):
        card = _make_qa_from_def("机器学习是一门让计算机从数据中学习规律的学科。")
        self.assertIsNotNone(card)
        self.assertEqual(card.type, "qa")
        self.assertIn("机器学习", card.front)
        self.assertIn("从数据中学习", card.back)

    def test_english_definition_qa(self):
        card = _make_qa_from_def("Photosynthesis is the process by which plants convert light into energy.")
        self.assertIsNotNone(card)
        self.assertEqual(card.type, "qa")
        self.assertEqual(card.front, "What is Photosynthesis?")

    def test_extract_dedup_and_limit(self):
        text = (
            "人工智能是研究让机器具备智能的学科。"
            "机器学习是人工智能的一个分支。"
            "深度学习是机器学习的一种方法。"
        )
        cards = extract_cards(text, max_cards=2)
        self.assertLessEqual(len(cards), 2)
        fronts = [c.front for c in cards]
        self.assertEqual(len(fronts), len(set(fronts)))  # 无重复


if __name__ == "__main__":
    unittest.main()
