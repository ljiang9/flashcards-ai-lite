"""可选的 LLM 闪卡生成：用标准库 urllib 调用 OpenAI 兼容接口。

读取环境变量：
- OPENAI_API_KEY：没有则视为不可用，调用方应降级到规则式；
- OPENAI_BASE_URL：默认 https://api.openai.com/v1；
- OPENAI_MODEL：默认 gpt-4o-mini。

要求 LLM 输出 JSON 数组，失败时抛异常，由上层降级处理。
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import List

from .extractor import Card

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"

_PROMPT = (
    "请把下面的学习文本提炼成高效记忆闪卡。只输出 JSON 数组，不要任何解释。"
    "每个元素形如 {\"type\": \"cloze\" 或 \"qa\", \"front\": \"正面\", \"back\": \"背面\"}。"
    "cloze 卡：正面是句子中的关键术语替换为 ____，背面是该术语；"
    "qa 卡：正面是问题，背面是简洁答案。只保留真正值得记忆的要点。\n\n文本：\n"
)


def is_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _extract_json_array(raw: str) -> list:
    """容忍模型在 JSON 外套 ```json ``` 代码块。"""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lstrip().lower().startswith("json"):
            raw = raw.lstrip()[4:]
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("LLM 输出中未找到 JSON 数组")
    return json.loads(raw[start : end + 1])


def generate_cards(text: str, max_cards: int = 40) -> List[Card]:
    """调用 LLM 生成闪卡；任何异常都向上抛，由调用方降级。"""
    api_key = os.environ["OPENAI_API_KEY"]
    base_url = os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个把学习文本转成记忆闪卡的助手，只输出 JSON。"},
            {"role": "user", "content": _PROMPT + text},
        ],
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    content = body["choices"][0]["message"]["content"]

    cards = []
    for item in _extract_json_array(content)[:max_cards]:
        t = item.get("type", "qa")
        if t not in ("cloze", "qa"):
            t = "qa"
        if item.get("front") and item.get("back"):
            cards.append(Card(type=t, front=str(item["front"]), back=str(item["back"])))
    return cards
