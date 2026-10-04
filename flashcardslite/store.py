"""闪卡库的本地 JSON 持久化。

默认存放路径：~/.flashcards_lite/store.json
可用构造参数 data_path 覆盖（测试里传临时文件）。
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date
from typing import Dict, List

from .extractor import Card
from .leiter import due_date

DEFAULT_DATA_DIR = os.path.expanduser("~/.flashcards_lite")
DEFAULT_DATA_FILE = os.path.join(DEFAULT_DATA_DIR, "store.json")


class CardStore:
    """按 deck 分组的闪卡库，读写单个 JSON 文件。"""

    def __init__(self, data_path: str = DEFAULT_DATA_FILE):
        self.data_path = data_path
        self._data: Dict[str, List[dict]] = {}
        self.load()

    # ---------- 读写 ----------
    def load(self) -> None:
        if not os.path.exists(self.data_path):
            self._data = {}
            return
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            self._data = json.loads(content) if content else {}
        except (json.JSONDecodeError, OSError):
            # 文件为空或损坏时，按空库处理，避免启动即崩溃
            self._data = {}

    def save(self) -> None:
        directory = os.path.dirname(self.data_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ---------- 业务 ----------
    def decks(self) -> List[str]:
        return sorted(self._data.keys())

    def cards(self, deck: str) -> List[dict]:
        return self._data.get(deck, [])

    def add_cards(self, deck: str, cards: List[Card], today: date | None = None) -> int:
        """把一批新卡片加入卡组。新卡从 1 号盒开始，立即可复习。"""
        today = today or date.today()
        bucket = self._data.setdefault(deck, [])
        existing = {(c["front"], c["back"]) for c in bucket}
        added = 0
        for card in cards:
            if (card.front, card.back) in existing:
                continue
            bucket.append(
                {
                    "id": uuid.uuid4().hex[:8],
                    "type": card.type,
                    "front": card.front,
                    "back": card.back,
                    "box": 1,
                    "created": today.isoformat(),
                    "last_reviewed": today.isoformat(),
                    "due": today.isoformat(),  # 新卡今天就到期
                    "correct": 0,
                    "wrong": 0,
                }
            )
            added += 1
        return added

    def update_card(self, deck: str, card_id: str, *, box: int, due: date,
                    correct: bool, today: date | None = None) -> None:
        today = today or date.today()
        for c in self._data.get(deck, []):
            if c["id"] == card_id:
                c["box"] = box
                c["due"] = due.isoformat()
                c["last_reviewed"] = today.isoformat()
                c["correct"] = int(c.get("correct", 0)) + (1 if correct else 0)
                c["wrong"] = int(c.get("wrong", 0)) + (0 if correct else 1)
                return
        raise KeyError(f"卡片不存在：{card_id}")
