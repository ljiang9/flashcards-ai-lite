"""规则式闪卡抽取：无 API key 时也能完整工作。

两类卡片：
- cloze（填空卡）：在关键句中遮蔽一个术语，正面是带 ____ 的句子，背面是术语。
- qa（问答卡）：从「X 是指 Y / X is Y」这类定义句式中抽取，正面提问，背面是解释。

全部为启发式规则，目的是在没有 LLM 的情况下也能产出可用闪卡。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import List

CLOZE_BLANK = "____"


@dataclass
class Card:
    type: str          # "cloze" 或 "qa"
    front: str         # 正面（题目）
    back: str          # 背面（答案）

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Card":
        return Card(type=d["type"], front=d["front"], back=d["back"])


# ---------- 句子切分 ----------

_SENT_SPLIT = re.compile(r"(?<=[。！？!?；;\n])")


def split_sentences(text: str) -> List[str]:
    """把文本切分成句子，中英文标点都认。"""
    parts = _SENT_SPLIT.split(text)
    out = []
    for p in parts:
        s = p.strip()
        if len(s) >= 6:  # 太短的碎片忽略
            out.append(s)
    return out


# ---------- 候选术语提取 ----------

# 引号包裹的术语：中文「」“” 与英文单双引号
_QUOTED = re.compile(r"[“\"「『『']([^”\"」』』'\n]{1,20})[”\"」』』']")

# 中文定义句式： 术语 + 是/是指/指的是/即/定义为 + 解释
_CN_DEF = re.compile(
    r"^(?P<term>[一-龥A-Za-z0-9（）()·]{2,15}?)\s*(?:是指|指的是|是一种|定义为|即|是|叫作|称为)\s*(?P<def>.+)$"
)

# 英文定义句式： Term is / refers to / is defined as ...
_EN_DEF = re.compile(
    r"^(?P<term>[A-Z][A-Za-z]+(?:\s+[A-Z][a-z]+){0,2})\s+(?:is defined as|refers to|is called|is)\s+(?P<def>.+)$"
)

# 句中大写开头的英文词组（句首除外），当作专有术语
_EN_PROPER = re.compile(r"(?<![。！？\s])\b([A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]+){0,2})")

_CJK = re.compile(r"[一-龥]")


def _has_cjk(s: str) -> bool:
    return bool(_CJK.search(s))


def _candidate_terms(sentence: str) -> List[str]:
    """从一个句子里找出值得挖空的候选术语。"""
    terms: List[str] = []
    # 1) 引号里的词优先级最高
    for m in _QUOTED.finditer(sentence):
        t = m.group(1).strip()
        if 2 <= len(t) <= 20:
            terms.append(t)
    # 2) 中文：取定义句里的术语
    m = _CN_DEF.match(sentence)
    if m:
        terms.append(m.group("term"))
    # 3) 英文专有名词（排除句首第一个大写词）
    offset = 0
    stripped = sentence.lstrip()
    offset = len(sentence) - len(stripped)
    for m in _EN_PROPER.finditer(sentence):
        if m.start() == offset:
            continue  # 句首词不算
        t = m.group(1).strip()
        if 3 <= len(t.split()[0]) <= 20:
            terms.append(t)
    # 去重保序
    seen, out = set(), []
    for t in terms:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


# ---------- 卡片生成 ----------

def _make_cloze(sentence: str, term: str) -> Card | None:
    """把术语在句中遮蔽成填空卡；术语在句中只出现一次才生成。"""
    if sentence.count(term) != 1:
        return None
    front = sentence.replace(term, CLOZE_BLANK, 1)
    return Card(type="cloze", front=front, back=term)


def _make_qa_from_def(sentence: str) -> Card | None:
    """从定义句式生成问答卡。"""
    m = _CN_DEF.match(sentence)
    if m:
        term, definition = m.group("term").strip(), m.group("def").strip().rstrip("。")
        if len(term) >= 2 and len(definition) >= 3:
            return Card(type="qa", front=f"什么是「{term}」？", back=definition)
    m = _EN_DEF.match(sentence)
    if m:
        term, definition = m.group("term").strip(), m.group("def").strip().rstrip(".")
        if len(term) >= 3 and len(definition) >= 5:
            return Card(type="qa", front=f"What is {term}?", back=definition)
    return None


def extract_cards(text: str, max_cards: int = 40) -> List[Card]:
    """对一段文本跑规则式抽取，返回去重后的卡片列表。"""
    cards: List[Card] = []
    seen = set()

    def add(c: Card | None) -> None:
        if c is None:
            return
        key = (c.type, c.front)
        if key in seen:
            return
        seen.add(key)
        cards.append(c)

    for sent in split_sentences(text):
        if len(cards) >= max_cards:
            break
        # 先尝试定义句 → 问答卡
        add(_make_qa_from_def(sent))
        # 再对候选术语做挖空
        for term in _candidate_terms(sent):
            if len(cards) >= max_cards:
                break
            add(_make_cloze(sent, term))
    return cards[:max_cards]
