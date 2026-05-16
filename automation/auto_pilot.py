#!/usr/bin/env python3
"""まとめサイト・SNS 運用の自動連携。

1. note から最新記事を抽出（fetch_note_articles_500.py をラップ）
2. results.json をサイト用 notes_data.json にマージ（merge_results_to_notes.py）
3. サムネイル等の詳細を補完（detail_scraper.py）
4. X ハッシュタグランキングを更新（generate_x_ranking.py）
5. 変更を検知して git add/commit/pull/push（GitHub Pages に本番反映）
6. X 投稿用テキストを生成し、Make.com Webhook（無ければ Discord）へ連携

実行: automation/.venv/bin/python automation/auto_pilot.py [--dry-run]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from datetime import datetime

import requests

import config
from lib import discord

# 既存スクリプト（scripts/send_x_draft_notification.py）の純粋関数を再利用
sys.path.insert(0, str(config.SCRIPTS_DIR))


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def run_script(name: str, args: list[str] | None = None, *, cwd=None) -> bool:
    """既存スクリプトを automation venv の python で実行する。"""
    script = config.SCRIPTS_DIR / name
    if not script.exists():
        script = config.PROJECT_ROOT / name  # ルート直下のスクリプト
    cmd = [str(config.VENV_PYTHON), str(script)] + (args or [])
    _log(f"実行: {script.name} {' '.join(args or [])}")
    proc = subprocess.run(cmd, cwd=cwd or config.PROJECT_ROOT)
    if proc.returncode != 0:
        _log(f"  -> 失敗 (exit {proc.returncode})")
        return False
    _log("  -> 完了")
    return True


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=config.PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


def step_extract_and_merge() -> None:
    """note 抽出 → notes_data.json へマージ → 詳細補完 → ランキング更新。"""
    max_works = config.get("AUTO_PILOT_MAX_WORKS", "40")
    if run_script("fetch_note_articles_500.py", ["--max-works", max_works]):
        run_script("merge_results_to_notes.py", ["--results", str(config.RESULTS_JSON)])
    else:
        _log("note 抽出に失敗。既存 results.json があればマージを試みます。")
        if config.RESULTS_JSON.exists():
            run_script("merge_results_to_notes.py", ["--results", str(config.RESULTS_JSON)])
    run_script("detail_scraper.py")
    run_script("generate_x_ranking.py")


def step_publish(dry_run: bool) -> bool:
    """変更があれば commit / pull --rebase / push。戻り値: 変更があったか。"""
    targets = ["notes_data.json", "x_ranking.json", "results.json"]
    git("add", *targets)
    staged = git("diff", "--cached", "--quiet")
    if staged.returncode == 0:
        _log("サイトデータに変更なし。push をスキップします。")
        return False

    msg = f"chore: auto_pilot で note 最新データを反映 [{datetime.now():%Y-%m-%d %H:%M}]"
    if dry_run or config.get("AUTO_PILOT_NO_PUSH").lower() == "true":
        _log(f"[dry-run/no-push] commit/push をスキップ（メッセージ: {msg}）")
        git("reset", "HEAD", *targets)
        return True

    commit = git("commit", "-m", msg)
    if commit.returncode != 0:
        _log(f"commit 失敗: {commit.stderr.strip()}")
        return True
    _log("commit 完了。")

    pull = git("pull", "--rebase", "origin", "main")
    if pull.returncode != 0:
        _log(f"pull --rebase 失敗（push を中止）: {pull.stderr.strip()}")
        return True

    push = git("push", "origin", "main")
    if push.returncode != 0:
        _log(f"push 失敗: {push.stderr.strip()}")
    else:
        _log("GitHub へ push 完了。GitHub Pages に本番反映されます。")
    return True


def build_x_text() -> str:
    """既存 send_x_draft_notification.py の関数を使い X 投稿文を生成。"""
    import send_x_draft_notification as sx

    notes = sx.load_notes(sx.NOTES_PATH)
    if not notes:
        return ""
    return sx.build_x_draft(notes)


def deliver_x_text(text: str, dry_run: bool) -> None:
    if not text:
        _log("投稿可能な note が無いため X テキスト生成をスキップ。")
        return
    print("---- X 投稿テキスト ----")
    print(text)
    print("------------------------")
    if dry_run:
        _log("[dry-run] 連携送信をスキップ。")
        return

    make_url = config.get("MAKE_WEBHOOK_URL")
    if make_url:
        try:
            resp = requests.post(
                make_url,
                json={"text": text, "content": text, "source": "auto_pilot"},
                timeout=30,
            )
            resp.raise_for_status()
            _log("Make.com Webhook へ X テキストを連携しました。")
            return
        except Exception as exc:
            _log(f"Make.com 連携失敗、Discord へフォールバック: {exc}")

    webhook = config.get("DISCORD_WEBHOOK_URL")
    if webhook:
        discord.send_codeblock(webhook, "[auto_pilot] X 投稿下書き", text)
        _log("Discord へ X テキストを連携しました。")
    else:
        _log("[warn] MAKE_WEBHOOK_URL / DISCORD_WEBHOOK_URL 未設定。連携先がありません。")


def main() -> None:
    parser = argparse.ArgumentParser(description="まとめサイト・SNS 自動連携")
    parser.add_argument("--dry-run", action="store_true", help="push と外部送信を行わない")
    args = parser.parse_args()

    _log("=== auto_pilot 開始 ===")
    step_extract_and_merge()
    changed = step_publish(args.dry_run)
    text = build_x_text()
    deliver_x_text(text, args.dry_run)
    _log(f"=== auto_pilot 完了（サイト変更: {'あり' if changed else 'なし'}）===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
