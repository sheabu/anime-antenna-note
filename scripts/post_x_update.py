import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTES_PATH = ROOT / "notes_data.json"


@dataclass
class Note:
    anime_title: str
    note_title: str
    url: str
    likes: int
    posted_ts: float


def parse_timestamp(note: dict) -> float:
    candidates = [note.get("posted_at"), note.get("updated_at")]
    for candidate in candidates:
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


def load_notes(path: Path) -> list[Note]:
    data = json.loads(path.read_text(encoding="utf-8"))
    notes: list[Note] = []
    for row in data:
        anime = str(row.get("anime_title") or row.get("work") or "").strip()
        title = str(row.get("note_title") or row.get("title") or "").strip()
        url = str(row.get("url") or "").strip()
        if not anime or not title or not url.startswith("https://"):
            continue
        likes = int(float(row.get("like_count") or row.get("likes") or 0))
        notes.append(
            Note(
                anime_title=anime,
                note_title=title,
                url=url,
                likes=likes,
                posted_ts=parse_timestamp(row),
            )
        )
    return notes


def build_hashtag_ranking(notes: list[Note], top_n: int = 3) -> list[tuple[str, int]]:
    now = datetime.now(timezone.utc).timestamp()
    scores: defaultdict[str, float] = defaultdict(float)
    for note in notes:
        tag = f"#{note.anime_title.replace(' ', '')}"
        age_days = max((now - note.posted_ts) / 86400.0, 0) if note.posted_ts else 30.0
        recency_boost = max(1.0, 30.0 - age_days)
        scores[tag] += note.likes * 2.0 + recency_boost
    ranking = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [(tag, int(score)) for tag, score in ranking[:top_n]]


def pick_featured_notes(notes: list[Note], top_n: int = 3) -> list[Note]:
    # 同一作品で埋まりすぎないように、まず作品ごとの最高スコア記事を拾う
    best_per_work: dict[str, Note] = {}
    for note in notes:
        current = best_per_work.get(note.anime_title)
        if current is None or (note.likes, note.posted_ts) > (current.likes, current.posted_ts):
            best_per_work[note.anime_title] = note
    unique_top = sorted(best_per_work.values(), key=lambda n: (n.likes, n.posted_ts), reverse=True)
    return unique_top[:top_n]


def build_post_text(rankings: list[tuple[str, int]], featured: list[Note]) -> str:
    lines: list[str] = []
    lines.append("【あにnoteアンテナ 今日の注目】")
    if rankings:
        lines.append("▼人気タグ")
        for i, (tag, score) in enumerate(rankings, start=1):
            lines.append(f"{i}. {tag} ({score})")
    if featured:
        lines.append("▼注目記事")
        for i, note in enumerate(featured, start=1):
            lines.append(f"{i}. {note.anime_title} / ❤️{note.likes}")
            lines.append(note.url)
    lines.append("#アニメ #note")

    text = "\n".join(lines)
    if len(text) <= 280:
        return text

    # 280文字制限を超える場合は注目記事を段階的に削る
    while featured and len(text) > 280:
        featured = featured[:-1]
        lines = lines[:]
        lines = ["【あにnoteアンテナ 今日の注目】"]
        if rankings:
            lines.append("▼人気タグ")
            for i, (tag, score) in enumerate(rankings, start=1):
                lines.append(f"{i}. {tag} ({score})")
        if featured:
            lines.append("▼注目記事")
            for i, note in enumerate(featured, start=1):
                lines.append(f"{i}. {note.anime_title} / ❤️{note.likes}")
                lines.append(note.url)
        lines.append("#アニメ #note")
        text = "\n".join(lines)
    return text[:280]


def create_client():
    import tweepy

    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
    if not all([api_key, api_secret, access_token, access_token_secret]):
        raise RuntimeError(
            "X credentials are missing. Set X_API_KEY, X_API_SECRET, "
            "X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET."
        )
    return tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )


def main() -> None:
    notes = load_notes(NOTES_PATH)
    if not notes:
        raise RuntimeError("notes_data.json does not contain postable notes.")

    rankings = build_hashtag_ranking(notes, top_n=3)
    featured = pick_featured_notes(notes, top_n=3)
    text = build_post_text(rankings, featured)

    if os.getenv("DRY_RUN", "false").lower() == "true":
        print("[DRY_RUN] tweet text:")
        print(text)
        return

    client = create_client()
    response = client.create_tweet(text=text)
    print(f"Tweet posted: {response.data}")


if __name__ == "__main__":
    main()
