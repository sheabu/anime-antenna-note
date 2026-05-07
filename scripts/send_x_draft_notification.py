import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
NOTES_PATH = ROOT / "notes_data.json"
MAX_X_CHARS = 140


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
        url = str(row.get("url") or "").strip()
        likes = int(float(row.get("like_count") or row.get("likes") or 0))
        if not anime or not url.startswith("https://"):
            continue
        notes.append(
            {
                "anime_title": anime,
                "url": url,
                "likes": likes,
                "posted_ts": parse_timestamp(row),
            }
        )
    return notes


def build_rankings(notes: list[dict], top_n: int = 2) -> list[str]:
    scores: defaultdict[str, float] = defaultdict(float)
    now_ts = datetime.now(timezone.utc).timestamp()
    for note in notes:
        tag = f"#{note['anime_title'].replace(' ', '')}"
        age_days = max((now_ts - note["posted_ts"]) / 86400.0, 0) if note["posted_ts"] else 30.0
        recency_boost = max(1.0, 30.0 - age_days)
        scores[tag] += note["likes"] * 2.0 + recency_boost
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [tag for tag, _ in ranked[:top_n]]


def pick_featured_url(notes: list[dict]) -> str:
    if not notes:
        return ""
    best = max(notes, key=lambda n: (n["likes"], n["posted_ts"]))
    return best["url"]


def build_x_draft(notes: list[dict]) -> str:
    tags = build_rankings(notes, top_n=2)
    featured_url = pick_featured_url(notes)
    date_label = datetime.now().strftime("%m/%d")
    tag_text = " ".join(tags) if tags else "#アニメ"

    base = f"{date_label}の注目noteまとめ {tag_text}\n{featured_url}\n#アニメ #note"
    if len(base) <= MAX_X_CHARS:
        return base

    compact = f"{date_label} 注目note {tag_text}\n{featured_url}\n#アニメ"
    if len(compact) <= MAX_X_CHARS:
        return compact

    minimal = f"{date_label} 注目note\n{featured_url}"
    return minimal[:MAX_X_CHARS]


def send_discord_message(webhook_url: str, draft: str) -> None:
    body = {
        "content": f"X投稿下書き（{MAX_X_CHARS}文字以内）\n```text\n{draft}\n```"
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
    if dry_run:
        print("[DRY_RUN] Generated X draft:")
        print(draft)
        return

    send_discord_message(webhook_url, draft)
    print("Draft sent to Discord webhook.")
    print(draft)


if __name__ == "__main__":
    main()
