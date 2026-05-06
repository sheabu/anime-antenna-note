import json
from collections import defaultdict
from datetime import datetime
from email.utils import parsedate_to_datetime


def parse_timestamp(note):
    candidates = [note.get("posted_at"), note.get("updated_at")]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return parsedate_to_datetime(candidate).timestamp()
        except Exception:
            pass
        try:
            return datetime.fromisoformat(str(candidate).replace("Z", "+00:00")).timestamp()
        except Exception:
            pass
    return 0.0


def build_rankings(notes):
    scores = defaultdict(float)
    now_ts = datetime.now().timestamp()

    for note in notes:
        anime = (note.get("anime_title") or note.get("work") or "").strip()
        if not anime:
            continue

        tag = f"#{anime.replace(' ', '')}"
        likes = float(note.get("like_count") or note.get("likes") or 0)
        note_ts = parse_timestamp(note)
        age_days = max((now_ts - note_ts) / 86400.0, 0) if note_ts else 30.0
        recency_boost = max(1.0, 30.0 - age_days)
        scores[tag] += likes * 2.0 + recency_boost

    ranking = sorted(
        [{"tag": tag, "score": int(score)} for tag, score in scores.items()],
        key=lambda x: x["score"],
        reverse=True,
    )[:20]

    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "notes_data.json",
        "rankings": ranking,
    }


def main():
    with open("notes_data.json", "r", encoding="utf-8") as f:
        notes = json.load(f)
    output = build_rankings(notes)
    with open("x_ranking.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"x_ranking.json updated ({len(output['rankings'])} tags)")


if __name__ == "__main__":
    main()
