import json
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
NOTES_PATH = ROOT / "notes_data.json"
MAX_X_CHARS = 140
ESSENTIAL_HASHTAGS = "#アニメ #note"


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


def pick_newest_notes(notes: list[dict], top_n: int = 3) -> list[dict]:
    """posted_at が新しい順。同一時刻は URL で安定ソート。"""
    return sorted(
        notes,
        key=lambda n: (n["posted_ts"], n["url"]),
        reverse=True,
    )[:top_n]


def truncate_dots(text: str, max_len: int) -> str:
    """長すぎる場合は末尾を ... で省略（X本文の文字数に合わせる）。"""
    t = text.strip()
    if max_len <= 0:
        return ""
    if len(t) <= max_len:
        return t
    if max_len <= 3:
        return "." * min(max_len, 3)
    return t[: max_len - 3] + "..."


def normalize_hook_title(title: str) -> str:
    text = title.replace("【", "").replace("】", " ").replace("『", "").replace("』", "").strip()
    text = " ".join(text.split())
    return text.strip("\"'")


def build_x_draft(notes: list[dict]) -> str:
    """
    新着1件ベース。本文 + 固定ハッシュタグ2つで MAX_X_CHARS 以内。
    """
    if not notes:
        return ""
    featured = pick_newest_notes(notes, top_n=1)[0]

    mmdd = datetime.now().strftime("%m/%d")
    line1 = f"{mmdd} 新着note"
    url = featured["url"]
    anime = featured["anime_title"].strip()
    hook_src = normalize_hook_title(featured["title"])
    footer = f"\n{ESSENTIAL_HASHTAGS}"

    def render(anime_s: str, hook_s: str | None) -> str:
        lines = [line1, anime_s]
        if hook_s:
            lines.append(f"続きが気になる『{hook_s}』")
        lines.append(url)
        return "\n".join(lines) + footer

    # アニメ名・フックを短くしながら 140 文字に収める
    max_anime = len(anime)
    while max_anime >= 1:
        a = truncate_dots(anime, max_anime)
        # フックなし
        body0 = render(a, None)
        if len(body0) <= MAX_X_CHARS:
            # 余裕があればフックをできるだけ長く
            best = body0
            for hlen in range(len(hook_src), 0, -1):
                h = truncate_dots(hook_src, hlen)
                cand = render(a, h)
                if len(cand) <= MAX_X_CHARS:
                    best = cand
                    break
            return best

        for hlen in range(len(hook_src), 0, -1):
            h = truncate_dots(hook_src, hlen)
            cand = render(a, h)
            if len(cand) <= MAX_X_CHARS:
                return cand

        max_anime -= 1

    # 最終手段（極端に長い URL 等）
    minimal = f"{line1}\n{url}{footer}"
    if len(minimal) <= MAX_X_CHARS:
        return minimal
    return truncate_dots(minimal, MAX_X_CHARS)


def format_posted_hint(note: dict) -> str:
    ts = note["posted_ts"]
    if not ts:
        return "投稿日時不明"
    try:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()
        return dt.strftime("%m/%d %H:%M")
    except Exception:
        return "投稿日時不明"


def build_discord_report(notes: list[dict], draft: str) -> str:
    """▼投稿文を最優先。新着1件の短いコンテキストのみ（TOP3一覧は出さない）。"""
    featured = pick_newest_notes(notes, top_n=1)[0]
    one_line = (
        f"{featured['anime_title']} / "
        f"{truncate_dots(normalize_hook_title(featured['title']), 42)}"
    )
    lines = [
        "X投稿下書き（自動生成・新着順）",
        f"文字数: {len(draft)} / {MAX_X_CHARS}",
        f"新着1件: {one_line}（{format_posted_hint(featured)}）",
        "",
        "▼投稿文",
        draft,
    ]
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
    if len(draft) > MAX_X_CHARS:
        raise RuntimeError(f"Draft exceeds {MAX_X_CHARS} chars: {len(draft)}")

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
