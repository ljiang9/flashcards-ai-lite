"""Leitner 盒间隔复习系统。

卡片放在 1..MAX_BOX 号盒子里：
- 答对：升入下一盒（封顶 MAX_BOX），下次复习间隔变长；
- 答错：打回 1 盒，重新开始积累。

各盒间隔（天）：盒子越大，记得越牢，间隔越久。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List

MAX_BOX = 5
# 盒号 -> 距离上次复习多少天后再次到期
BOX_INTERVALS: Dict[int, int] = {
    1: 1,
    2: 3,
    3: 7,
    4: 14,
    5: 30,
}


def interval_for_box(box: int) -> int:
    """某号盒子对应的复习间隔（天）。越界时夹到合法区间。"""
    box = max(1, min(box, MAX_BOX))
    return BOX_INTERVALS[box]


def next_box_on_correct(box: int) -> int:
    """答对后升到的盒号。"""
    return min(box + 1, MAX_BOX)


def due_date(box: int, last_reviewed: date) -> date:
    """根据上次复习日期和所在盒号，算出下次到期日。"""
    return last_reviewed + timedelta(days=interval_for_box(box))


def apply_answer(box: int, correct: bool, last_reviewed: date) -> dict:
    """根据一次答题对错更新盒号与到期日。

    返回 {"box": 新盒号, "due": 新到期日}。
    """
    if correct:
        new_box = next_box_on_correct(box)
    else:
        new_box = 1
    return {"box": new_box, "due": due_date(new_box, last_reviewed)}


def is_due(box: int, due: date, today: date) -> bool:
    """该卡片今天是否到期该复习。"""
    return due <= today


def bucket_summary(cards: List[dict], today: date) -> Dict[int, dict]:
    """统计各盒数量与到期数量。"""
    summary: Dict[int, dict] = {
        b: {"total": 0, "due": 0} for b in range(1, MAX_BOX + 1)
    }
    for c in cards:
        b = max(1, min(int(c.get("box", 1)), MAX_BOX))
        summary[b]["total"] += 1
        due = date.fromisoformat(c["due"]) if isinstance(c.get("due"), str) else c["due"]
        if due <= today:
            summary[b]["due"] += 1
    return summary
