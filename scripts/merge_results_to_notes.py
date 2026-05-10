#!/usr/bin/env python3
"""
fetch_note_articles_500.py が出力した results.json を、サイト用の notes_data.json に取り込む。

- URL が既に notes にあればスキップ（既存の詳細情報を優先）
- 新規分だけ末尾に追加し、id は連番で採番
- サムネイルはプレースホルダ。詳細は後続で detail_scraper.py が補完可能

使い方::

    python scripts/merge_results_to_notes.py
    python scripts/merge_results_to_notes.py --results path/to/results.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_THUMBNAIL = "https://via.placeholder.com/140x80?text=Anime"


def load_results(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("results.json はオブジェクト形式である必要があります")
    return data


def load_notes(path: Path) -> list[dict]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("notes_data.json は配列形式である必要があります")
    return raw


def save_notes_atomic(path: Path, notes: list[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    p = argparse.ArgumentParser(description="Merge results.json into notes_data.json")
    p.add_argument("--results", type=Path, default=ROOT / "results.json", help="fetch_note 出力")
    p.add_argument("--notes", type=Path, default=ROOT / "notes_data.json", help="サイト用データ")
    args = p.parse_args()

    results_path = args.results if args.results.is_absolute() else ROOT / args.results
    notes_path = args.notes if args.notes.is_absolute() else ROOT / args.notes

    if not results_path.exists():
        raise SystemExit(f"見つかりません: {results_path}")

    payload = load_results(results_path)
    works = payload.get("works")
    if not isinstance(works, list):
        raise SystemExit("results.json に works がありません")

    notes = load_notes(notes_path)
    existing_urls = {str(n.get("url") or "").strip() for n in notes if n.get("url")}
    max_id = max((int(n.get("id") or 0) for n in notes), default=0)

    added = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for work in works:
        anime_title = str(work.get("anime_title") or "").strip()
        if not anime_title:
            continue
        articles = work.get("articles") or []
        if not isinstance(articles, list):
            continue
        for art in articles:
            url = str(art.get("url") or "").strip()
            if not url.startswith("https://note.com/"):
                continue
            if url in existing_urls:
                continue
            max_id += 1
            notes.append(
                {
                    "id": max_id,
                    "anime_title": anime_title,
                    "note_title": str(art.get("title") or "").strip(),
                    "url": url,
                    "thumbnail": DEFAULT_THUMBNAIL,
                    "like_count": int(art.get("like_count") or 0),
                    "posted_at": str(art.get("posted_at") or "").strip(),
                    "author": str(art.get("author_name") or "").strip(),
                    "day": "",
                    "updated_at": now_str,
                }
            )
            existing_urls.add(url)
            added += 1

    save_notes_atomic(notes_path, notes)
    print(f"マージ完了: 新規 {added} 件を追加（notes 合計 {len(notes)} 件）")
    print(f"出力: {notes_path}")


if __name__ == "__main__":
    main()
