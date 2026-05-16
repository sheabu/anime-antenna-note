#!/usr/bin/env python3
"""朝のルーティン自動化。

1. Notion のタスク管理 DB を取得し、期日で整理する
2. 競合サイトをバックグラウンド巡回し、更新内容を要約する
3. 重要トピックを Discord に通知する

実行: automation/.venv/bin/python automation/daily_briefing.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime

import config
from lib import competitors, discord, notion, summarize


def build_task_section() -> str:
    token = config.get("NOTION_TOKEN")
    db_id = config.get("NOTION_DATABASE_ID")
    if not token or not db_id:
        return "■ タスク（Notion）\n  NOTION_TOKEN / NOTION_DATABASE_ID が未設定のためスキップ"

    try:
        tasks = notion.fetch_tasks(token, db_id)
    except Exception as exc:
        return f"■ タスク（Notion）\n  取得エラー: {exc}"

    board = notion.organize(tasks)
    lines = ["■ タスク（Notion）"]

    def render(label: str, items: list[notion.Task]) -> None:
        if not items:
            return
        lines.append(f"  【{label}】{len(items)}件")
        for t in items[:10]:
            due = t.due.strftime("%m/%d") if t.due else "期日なし"
            lines.append(f"   - [{due}] {t.title}")

    render("期限切れ", board.overdue)
    render("今日", board.today)
    render("今後", board.upcoming)
    render("期日未設定", board.no_date)
    if len(lines) == 1:
        lines.append("  未完了タスクはありません")
    return "\n".join(lines)


def build_competitor_section() -> str:
    sites = competitors.load_config(config.COMPETITORS_CONFIG)
    if not sites:
        return "■ 競合巡回\n  competitors.json に対象サイトが未設定のためスキップ"

    api_key = config.get("OPENAI_API_KEY")
    lines = ["■ 競合巡回・更新要約"]
    for result in competitors.crawl_all(sites):
        lines.append(f"  ● {result.name}")
        if result.error:
            lines.append(f"    巡回エラー: {result.error}")
            continue
        if not result.headlines:
            lines.append("    新しい見出しを検出できませんでした")
            continue
        digest = summarize.summarize(
            result.text, api_key, context=result.name, limit=180
        )
        for line in digest.splitlines():
            lines.append(f"    {line}")
        lines.append(f"    {result.url}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="朝のブリーフィング")
    parser.add_argument("--dry-run", action="store_true", help="Discord 送信せず標準出力のみ")
    args = parser.parse_args()

    header = f"☀ デイリーブリーフィング {datetime.now().strftime('%Y-%m-%d (%a) %H:%M')}"
    sections = [header, build_task_section(), build_competitor_section()]
    digest = "\n\n".join(sections)

    print(digest)

    webhook = config.get("DISCORD_WEBHOOK_URL")
    if args.dry_run:
        print("\n[dry-run] Discord 送信はスキップしました。")
        return
    if not webhook:
        print("\n[warn] DISCORD_WEBHOOK_URL 未設定のため通知をスキップしました。")
        return
    discord.send(webhook, digest)
    print("\nDiscord に通知しました。")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
