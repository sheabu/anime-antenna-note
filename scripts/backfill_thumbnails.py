#!/usr/bin/env python3
"""
notes_data.json のプレースホルダ／欠損サムネを、note.com v3 API（detail_scraper と同じ）で埋める。

サイト直下の ./note-placeholder.svg は表示用フォールバック用。
本スクリプトで assets.st-note.com 等の実サムネを書き込む。

例::

    cd /path/to/anime-antenna && python3 scripts/backfill_thumbnails.py --max 200
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))

    from detail_scraper import (
        fetch_note_detail,
        save_notes,
        thumbnail_needs_refresh,
    )

    import requests

    p = argparse.ArgumentParser(description="Backfill note thumbnails from note.com API")
    p.add_argument("--max", type=int, default=0, help="処理する最大件数（0=制限なし）")
    p.add_argument("--sleep-min", type=float, default=0.15)
    p.add_argument("--sleep-max", type=float, default=0.45)
    args = p.parse_args()

    path = ROOT / "notes_data.json"
    notes = json.loads(path.read_text(encoding="utf-8"))
    targets = [n for n in notes if thumbnail_needs_refresh(n)]
    print(f"サムネ更新対象: {len(targets)} 件（プレースホルダ・欠損・非HTTPS URL）")

    session = requests.Session()
    updated = 0
    for i, note in enumerate(targets):
        if args.max and updated >= args.max:
            print(f"--max {args.max} に達したため終了します。")
            break
        url = (note.get("url") or "").strip()
        if not url.startswith("http"):
            continue

        detail = fetch_note_detail(session, url)
        if not detail:
            print(f"[skip] 取得失敗 {url}")
            continue

        thumb = str(detail.get("thumbnail") or "").strip()
        # まだプレースホルダだけならスキップ（レート制限等）
        if not thumb or "note-placeholder.svg" in thumb or "via.placeholder.com" in thumb.lower():
            print(f"[skip] サムネ未取得 {url}")
            continue

        note["thumbnail"] = thumb
        if detail.get("note_title"):
            note["note_title"] = detail["note_title"]
        note["like_count"] = detail.get("like_count", note.get("like_count", 0))
        if detail.get("posted_at"):
            note["posted_at"] = detail["posted_at"]

        updated += 1
        if updated % 25 == 0:
            save_notes(notes)
            print(f"  ... 中間保存 ({updated} 件更新)")

        time.sleep(random.uniform(args.sleep_min, args.sleep_max))

    save_notes(notes)
    print(f"完了: {updated} 件のサムネを更新しました。")


if __name__ == "__main__":
    main()
