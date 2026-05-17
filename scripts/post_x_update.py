import json
import os
import tempfile
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
import tweepy


ROOT = Path(__file__).resolve().parents[1]
NOTES_PATH = ROOT / "notes_data.json"


@dataclass
class Note:
    anime_title: str
    note_title: str
    url: str
    thumbnail: str
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
        thumbnail = str(row.get("thumbnail") or row.get("image") or "").strip()
        if not anime or not title or not url.startswith("https://"):
            continue
        likes = int(float(row.get("like_count") or row.get("likes") or 0))
        notes.append(
            Note(
                anime_title=anime,
                note_title=title,
                url=url,
                thumbnail=thumbnail,
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
    now_label = datetime.now(timezone.utc).astimezone().strftime("%-m/%-d %H:%M")
    lines.append(f"【あにnoteアンテナ 今日の注目 {now_label}】")
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
        lines = [f"【あにnoteアンテナ 今日の注目 {now_label}】"]
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
    required = [
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print(f"Missing required env vars: {', '.join(missing)}")
        raise RuntimeError(
            "X credentials are missing. Set X_API_KEY, X_API_SECRET, "
            "X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET."
        )

    api_key = os.environ.get("X_API_KEY")
    api_secret = os.environ.get("X_API_SECRET")
    access_token = os.environ.get("X_ACCESS_TOKEN")
    access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")
    return tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )


def upload_image_if_enabled(featured: list[Note]):
    if os.environ.get("ENABLE_IMAGE", "false").lower() != "true":
        return None
    if not featured:
        return None
    image_url = featured[0].thumbnail
    if not image_url.startswith("http"):
        return None

    api_key = os.environ.get("X_API_KEY")
    api_secret = os.environ.get("X_API_SECRET")
    access_token = os.environ.get("X_ACCESS_TOKEN")
    access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")

    # URLのパス部分から拡張子を判定（クエリパラメータを除去）
    url_path = image_url.split("?")[0].lower()
    if url_path.endswith(".png"):
        suffix = ".png"
    elif url_path.endswith(".gif"):
        suffix = ".gif"
    elif url_path.endswith(".webp"):
        suffix = ".webp"
    else:
        suffix = ".jpg"

    tmp_path = None
    try:
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
        v1_api = tweepy.API(auth)

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
        urllib.request.urlretrieve(image_url, tmp_path)
        media = v1_api.media_upload(filename=tmp_path)
        return media.media_id
    except Exception as e:
        print(f"[WARN] Image upload skipped: {e}")
        return None
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def notify_discord(webhook_url: str, tweet_text: str, tweet_id: str | None = None) -> None:
    if not webhook_url:
        return
    tweet_url = f"https://x.com/i/web/status/{tweet_id}" if tweet_id else ""
    body_lines = ["**[あにnoteアンテナ] Xに投稿しました**", f"```\n{tweet_text}\n```"]
    if tweet_url:
        body_lines.append(tweet_url)
    try:
        response = requests.post(webhook_url, json={"content": "\n".join(body_lines)}, timeout=20)
        response.raise_for_status()
        print("Discord notification sent.")
    except Exception as e:
        print(f"[WARN] Discord notification failed: {e}")


def _report_x_error(e: "tweepy.TweepyException") -> None:
    """X API失敗時に原因を特定できるよう、ステータス・APIコード・本文を出力する。"""
    print("=" * 60)
    print("[X API ERROR] ツイート投稿に失敗しました")
    status = None
    response = getattr(e, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)
        print(f"  HTTP status : {status}")
        body = getattr(response, "text", "")
        if body:
            print(f"  Response body: {body[:500]}")
    api_codes = getattr(e, "api_codes", None)
    api_messages = getattr(e, "api_messages", None)
    if api_codes:
        print(f"  API codes   : {api_codes}")
    if api_messages:
        print(f"  API messages: {api_messages}")
    print(f"  Exception   : {type(e).__name__}: {e}")

    hint = {
        401: "認証情報が無効。4つのトークンを再発行し Secrets を更新してください。",
        403: "アプリ権限不足の可能性大。X Developer Portal で User authentication settings を "
             "「Read and Write」にした後、Access Token & Secret を再発行（重要）してください。"
             " もしくは重複投稿/規約違反の可能性。",
        429: "レート制限。X API Free プランの月間/日次の投稿上限に達しています。",
    }.get(status)
    if hint:
        print(f"  → 対処: {hint}")
    print("=" * 60)


def main() -> None:
    notes = load_notes(NOTES_PATH)
    if not notes:
        raise RuntimeError("notes_data.json does not contain postable notes.")

    rankings = build_hashtag_ranking(notes, top_n=3)
    featured = pick_featured_notes(notes, top_n=3)
    text = build_post_text(rankings, featured)

    if os.environ.get("DRY_RUN", "false").lower() == "true":
        print("[DRY_RUN] tweet text:")
        print(text)
        if os.environ.get("ENABLE_IMAGE", "false").lower() == "true" and featured:
            print(f"[DRY_RUN] image candidate: {featured[0].thumbnail}")
        discord_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
        if discord_url:
            print(f"[DRY_RUN] Discord notification would be sent to webhook.")
        return

    client = create_client()
    media_id = upload_image_if_enabled(featured)
    try:
        if media_id:
            response = client.create_tweet(text=text, media_ids=[media_id])
        else:
            response = client.create_tweet(text=text)
    except tweepy.TweepyException as e:
        _report_x_error(e)
        raise
    print(f"Tweet posted: {response.data}")

    tweet_id = str(response.data.get("id", "")) if response.data else None
    discord_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    notify_discord(discord_url, text, tweet_id)


if __name__ == "__main__":
    main()
