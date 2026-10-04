"""命令行入口：build / review / stats。

用法：
    python3 -m flashcardslite build --file note.txt
    python3 -m flashcardslite review
    python3 -m flashcardslite stats
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from . import extractor, leiter, llm
from .store import CardStore, DEFAULT_DATA_FILE


def _read_text(args) -> str:
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read()
    if args.text:
        return args.text
    return ""


def cmd_build(args) -> int:
    text = _read_text(args)
    if not text.strip():
        print("错误：请用 --file 或 --text 提供要生成闪卡的文本。", file=sys.stderr)
        return 2

    store = CardStore(args.data)
    engine = "规则式"
    cards = []
    if llm.is_configured():
        try:
            cards = llm.generate_cards(text, max_cards=args.max_cards)
            engine = "LLM"
        except Exception as e:  # 任何失败都降级到规则式
            print(f"提示：LLM 调用失败（{e}），已降级为规则式生成。", file=sys.stderr)
    if not cards:
        cards = extractor.extract_cards(text, max_cards=args.max_cards)
        engine = "规则式"

    added = store.add_cards(args.deck, cards)
    store.save()
    print(f"[{engine}] 卡组「{args.deck}」：新增 {added} 张，共 {len(store.cards(args.deck))} 张。")
    for c in cards[: args.preview]:
        print(f"  - [{c.type}] {c.front}  =>  {c.back}")
    return 0


def cmd_review(args) -> int:
    store = CardStore(args.data)
    today = date.today()
    bucket = store.cards(args.deck)
    due = [c for c in bucket if leiter.is_due(c["box"], date.fromisoformat(c["due"]), today)]
    if not due:
        print(f"卡组「{args.deck}」今天没有到期要复习的卡片，先去 build 生成一些吧。")
        return 0

    print(f"今天要复习 {len(due)} 张卡片（回答 y=认识 / n=忘记 / q=退出）：\n")
    done = 0
    for c in due:
        print(f"[{c['type']}] {c['front']}")
        try:
            ans = input("你的回答是？（回车看答案）").strip().lower()
        except EOFError:
            ans = "q"
        if ans == "q":
            break
        print(f"答案：{c['back']}")
        try:
            known = input("答对了吗？(y/n) ").strip().lower()
        except EOFError:
            break
        correct = known == "y"
        result = leiter.apply_answer(c["box"], correct, today)
        store.update_card(args.deck, c["id"], box=result["box"],
                          due=result["due"], correct=correct, today=today)
        done += 1
        print(f"  -> {'答对，升到 %d 盒' % result['box'] if correct else '答错，打回 1 盒'}，"
              f"下次到期 {result['due'].isoformat()}\n")
    store.save()
    print(f"本次完成 {done} 张复习，已保存进度。")
    return 0


def cmd_stats(args) -> int:
    store = CardStore(args.data)
    decks = store.decks()
    if not decks:
        print("还没有任何卡组，先用 build 生成闪卡。")
        return 0
    today = date.today()
    for deck in (args.deck and [args.deck]) or decks:
        cards = store.cards(deck)
        summary = leiter.bucket_summary(cards, today)
        total = len(cards)
        mastered = sum(s["total"] for b, s in summary.items() if b >= 4)
        due = sum(s["due"] for s in summary.values())
        print(f"卡组「{deck}」：共 {total} 张，今天到期 {due} 张，已掌握（4-5 盒）{mastered} 张。")
        for b in range(1, leiter.MAX_BOX + 1):
            s = summary[b]
            bar = "#" * min(s["total"], 20)
            print(f"  {b} 盒（{leiter.interval_for_box(b):>2} 天间隔）: {s['total']:>3} 张，"
                  f"到期 {s['due']:>3} 张  {bar}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="flashcardslite", description="规则式/LLM 闪卡 + Leitner 间隔复习")
    p.add_argument("--data", default=DEFAULT_DATA_FILE, help="指定卡片库 JSON 路径")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="从文本生成闪卡")
    b.add_argument("--file", help="输入文本文件路径")
    b.add_argument("--text", help="直接传入文本")
    b.add_argument("--deck", default="default", help="卡组名（默认 default）")
    b.add_argument("--max-cards", type=int, default=40)
    b.add_argument("--preview", type=int, default=5, help="打印前 N 张预览")
    b.set_defaults(func=cmd_build)

    r = sub.add_parser("review", help="复习今天到期的卡片")
    r.add_argument("--deck", default="default")
    r.set_defaults(func=cmd_review)

    s = sub.add_parser("stats", help="查看各盒数量与掌握情况")
    s.add_argument("--deck", default=None, help="只看某个卡组")
    s.set_defaults(func=cmd_stats)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
