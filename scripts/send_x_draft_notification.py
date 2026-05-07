import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
NOTES_PATH = ROOT / "notes_data.json"
MAX_X_CHARS = 220


def parse_timestamp(note: dict) -> float:
    for candidate in (note.get("posted_at"), note.get("updated_at")):
        if not candidate:
            continue
        text = str(candidate)
        try:
            return parsedate_to_datetime(text).timestamp()
        except Exception:
            pass
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
        except Exception:
            pass
    return 0.0


def load_notes(path: Path) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    notes: list[dict] = []
    for row in rows:
        anime = str(row.get("anime_title") or row.get("work") or "").strip()
        title = str(row.get("note_title") or row.get("title") or "").strip()
        url = str(row.get("url") or "").strip()
        likes = int(float(row.get("like_count") or row.get("likes") or 0))
        if not anime or not title or not url.startswith("https://"):
            continue
        notes.append(
            {
                "anime_title": anime,
                "title": title,
                "url": url,
                "likes": likes,
                "posted_ts": parse_timestamp(row),
            }
        )
    return notes


def build_rankings(notes: list[dict], top_n: int = 3) -> list[str]:
    scores: defaultdict[str, float] = defaultdict(float)
    now_ts = datetime.now(timezone.utc).timestamp()
    for note in notes:
        tag = f"#{note['anime_title'].replace(' ', '')}"
        age_days = max((now_ts - note["posted_ts"]) / 86400.0, 0) if note["posted_ts"] else 30.0
        recency_boost = max(1.0, 30.0 - age_days)
        scores[tag] += note["likes"] * 2.0 + recency_boost
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [tag for tag, _ in ranked[:top_n]]


def pick_top_notes(notes: list[dict], top_n: int = 3) -> list[dict]:
    # 人気順（いいね数優先）+ 同率は新しい記事を優先
    sorted_notes = sorted(notes, key=lambda n: (n["likes"], n["posted_ts"]), reverse=True)
    return sorted_notes[:top_n]


def short_title_hook(title: str, max_len: int = 36) -> str:
    text = title.replace("【", "").replace("】", " ").replace("『", "").replace("』", "").strip()
    text = " ".join(text.split())
    text = text.strip("\"'")
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def build_teaser(top_note: dict) -> str:
    hook = short_title_hook(top_note["title"], max_len=32)
    return f"続きが気になる『{hook}』"


def build_x_draft(notes: list[dict]) -> str:
    tags = build_rankings(notes, top_n=2)
    top_notes = pick_top_notes(notes, top_n=3)
    top_note = top_notes[0]
    featured_url = top_note["url"]
    date_label = datetime.now().strftime("%m/%d")
    tag_text = " ".join(tags) if tags else f"#{top_note['anime_title'].replace(' ', '')}"
    teaser = build_teaser(top_note)

    base = (
        f"{date_label} 人気note速報\n"
        f"❤️{top_note['likes']} / {top_note['anime_title']}\n"
        f"{teaser}\n"
        f"{featured_url}\n"
        f"#アニメ #note #考察 {tag_text}"
    )
    if len(base) <= MAX_X_CHARS:
        return base

    compact = (
        f"{date_label} 注目note\n"
        f"{top_note['anime_title']} ❤️{top_note['likes']}\n"
        f"{featured_url}\n"
        f"#アニメ #note #考察"
    )
    if len(compact) <= MAX_X_CHARS:
        return compact

    minimal = f"{date_label} 注目note {featured_url}"
    return minimal[:MAX_X_CHARS]


def build_discord_report(notes: list[dict], draft: str) -> str:
    top_notes = pick_top_notes(notes, top_n=3)
    lines = ["X投稿下書き（自動生成）", f"文字数: {len(draft)}", ""]
    lines.append("▼人気記事TOP3（いいね順）")
    for idx, note in enumerate(top_notes, start=1):
        hook = short_title_hook(note["title"], max_len=46)
        lines.append(f"{idx}. ❤️{note['likes']} {note['anime_title']} / {hook}")
    lines.append("")
    lines.append("▼投稿文")
    lines.append(draft)
    return "\n".join(lines)


def send_discord_message(webhook_url: str, report_text: str) -> None:
    body = {
        "content": f"```text\n{report_text}\n```"
    }
    response = requests.post(webhook_url, json=body, timeout=20)
    response.raise_for_status()


def main() -> None:
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url and not dry_run:
        raise RuntimeError("Missing DISCORD_WEBHOOK_URL. Set it in GitHub Secrets.")

    notes = load_notes(NOTES_PATH)
    if not notes:
        raise RuntimeError("notes_data.json does not contain valid records.")

    draft = build_x_draft(notes)
    report = build_discord_report(notes, draft)
    if dry_run:
        print("[DRY_RUN] Generated X draft:")
        print(draft)
        print("")
        print("[DRY_RUN] Report Preview:")
        print(report)
        return

    send_discord_message(webhook_url, report)
    print("Draft sent to Discord webhook.")
    print(draft)


if __name__ == "__main__":
    main()
