#!/usr/bin/env python3
"""
anime-antenna scraper v2
note内部JSON API → RSSフォールバックの2段構え。
HTMLスクレイピングは行わないためブロック回避率が高い。
"""

import json
import time
import sqlite3
import logging
import re
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

# ── 設定 ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
ANIME_LIST_PATH = BASE_DIR / "anime_list.json"
DB_PATH         = BASE_DIR / "anime_notes.db"
OUTPUT_JSON     = BASE_DIR / "notes_data.json"

# note 内部検索API（JSON返却）
NOTE_API_BASE = "https://note.com/api/v2/searches"

# ハッシュタグRSSフォールバック
RSS_HASHTAGS = [
    "https://note.com/hashtag/%E3%82%A2%E3%83%8B%E3%83%A1%E8%80%83%E5%AF%9F/rss",
    "https://note.com/hashtag/%E3%82%A2%E3%83%8B%E3%83%A1%E6%84%9F%E6%83%B3/rss",
    "https://note.com/hashtag/%E3%82%A2%E3%83%8B%E3%83%A1%E5%8F%8D%E5%BF%9C/rss",
]

RESULTS_PER_ANIME = 100
REQUEST_DELAY     = 2.0
API_PAGE_SIZE     = 20    # note APIの1ページ件数
MAX_PAGES         = 5     # 1キーワードあたり最大ページ数

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ja,en-US;q=0.9",
    "Referer": "https://note.com/",
    "Origin": "https://note.com",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── DB ───────────────────────────────────────────────────────────────────────
def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id          INTEGER PRIMARY KEY,
            anime_title TEXT NOT NULL,
            note_title  TEXT NOT NULL,
            url         TEXT UNIQUE NOT NULL,
            thumbnail   TEXT,
            like_count  INTEGER DEFAULT 0,
            posted_at   TEXT,
            author      TEXT,
            day         TEXT,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_anime ON notes(anime_title)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_likes ON notes(like_count DESC)")
    conn.commit()


def upsert_note(conn: sqlite3.Connection, row: dict) -> None:
    conn.execute("""
        INSERT INTO notes
            (anime_title, note_title, url, thumbnail, like_count, posted_at, author, day, updated_at)
        VALUES
            (:anime_title, :note_title, :url, :thumbnail, :like_count, :posted_at, :author, :day, CURRENT_TIMESTAMP)
        ON CONFLICT(url) DO UPDATE SET
            like_count  = excluded.like_count,
            thumbnail   = COALESCE(excluded.thumbnail, notes.thumbnail),
            updated_at  = CURRENT_TIMESTAMP
    """, row)


# ── HTTP ─────────────────────────────────────────────────────────────────────
def safe_get(url: str, session: requests.Session,
             params: dict | None = None, retries: int = 3) -> requests.Response | None:
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (429, 503):
                wait = REQUEST_DELAY * attempt * 3
                log.warning("Rate limited (%s). Waiting %.0fs…", resp.status_code, wait)
                time.sleep(wait)
            else:
                log.debug("HTTP %s: %s", resp.status_code, url)
                return None
        except requests.RequestException as exc:
            log.warning("Request error (attempt %d/%d): %s", attempt, retries, exc)
            time.sleep(REQUEST_DELAY * attempt)
    return None


# ── note 内部JSON API ─────────────────────────────────────────────────────────
def fetch_via_api(keyword: str, anime: dict, session: requests.Session) -> list[dict]:
    """note の内部 API を叩いて JSON で記事リストを取得する。"""
    results: list[dict] = []

    for page in range(1, MAX_PAGES + 1):
        params = {
            "context": "note",
            "q": keyword,
            "sort": "like",
            "page": page,
            "size": API_PAGE_SIZE,
        }
        log.info("  [API] %s p%d", keyword, page)
        resp = safe_get(NOTE_API_BASE, session, params=params)
        time.sleep(REQUEST_DELAY)

        if not resp:
            return []   # ブロック → フォールバックへ

        try:
            data = resp.json()
        except ValueError:
            log.warning("  JSONパース失敗")
            return []

        # レスポンス構造: data.data.notes[] or data.notes[]
        notes_raw = (
            data.get("data", {}).get("notes", [])
            or data.get("notes", [])
            or []
        )

        if not notes_raw:
            break  # 最終ページ

        for n in notes_raw:
            url = f"https://note.com/{n.get('user', {}).get('urlname','')}/n/{n.get('key','')}"
            results.append({
                "anime_title": anime["title"],
                "note_title":  n.get("name", ""),
                "url":         url,
                "thumbnail":   n.get("eyecatch") or n.get("thumbnail"),
                "like_count":  n.get("likeCount") or n.get("like_count") or 0,
                "posted_at":   n.get("publishAt") or n.get("published_at") or "",
                "author":      n.get("user", {}).get("name", ""),
                "day":         anime["day"],
            })

        if len(results) >= RESULTS_PER_ANIME:
            break

    return results


# ── RSSフォールバック ─────────────────────────────────────────────────────────
def fetch_rss_for_anime(anime: dict, session: requests.Session) -> list[dict]:
    """作品名キーワードでRSSを検索し記事を取得する（like_countは0）。"""
    results: list[dict] = []
    keyword = anime["keywords"][0].split()[0]   # 主キーワードの作品名部分だけ

    # note にはハッシュタグRSSしかないため、グローバルRSSから作品名でフィルタ
    for rss_url in RSS_HASHTAGS:
        resp = safe_get(rss_url, session)
        time.sleep(REQUEST_DELAY)
        if not resp:
            continue
        try:
            soup = BeautifulSoup(resp.content, "xml")
        except Exception:
            soup = BeautifulSoup(resp.content, "lxml-xml")

        for item in soup.find_all("item"):
            try:
                title  = item.find("title").get_text(strip=True)  if item.find("title")   else ""
                url    = item.find("link").get_text(strip=True)    if item.find("link")    else ""
                pub    = item.find("pubDate").get_text(strip=True) if item.find("pubDate") else ""
                if not url or keyword not in title:
                    continue
                results.append({
                    "anime_title": anime["title"],
                    "note_title":  title,
                    "url":         url,
                    "thumbnail":   None,
                    "like_count":  0,
                    "posted_at":   pub,
                    "author":      "",
                    "day":         anime["day"],
                })
            except Exception:
                continue

    return results


# ── JSON エクスポート ──────────────────────────────────────────────────────────
def export_json(conn: sqlite3.Connection, path: Path) -> None:
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM notes ORDER BY like_count DESC")
    rows = [dict(r) for r in cur.fetchall()]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    log.info("JSON exported → %s (%d件)", path, len(rows))


# ── メイン ────────────────────────────────────────────────────────────────────
def main() -> None:
    with open(ANIME_LIST_PATH, encoding="utf-8") as f:
        anime_list: list[dict] = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    session = requests.Session()

    for anime in anime_list:
        log.info("▶ %s (%s)", anime["title"], anime["day"])
        collected: dict[str, dict] = {}

        # ── 1st try: 内部JSON API ────────────────────────────────────────────
        for keyword in anime["keywords"]:
            articles = fetch_via_api(keyword, anime, session)
            if not articles:
                log.info("  → API失敗。RSSにフォールバック")
                break
            for a in articles:
                if a["url"] not in collected:
                    collected[a["url"]] = a
            if len(collected) >= RESULTS_PER_ANIME:
                break

        # ── 2nd try: RSSフォールバック ────────────────────────────────────────
        if not collected:
            rss_articles = fetch_rss_for_anime(anime, session)
            for a in rss_articles:
                collected[a["url"]] = a
            log.info("  → RSS取得: %d件", len(collected))

        # スキ数降順ソート → 上位100件をDB保存
        top = sorted(collected.values(), key=lambda x: x["like_count"], reverse=True)[:RESULTS_PER_ANIME]
        for row in top:
            upsert_note(conn, row)
        conn.commit()
        log.info("  保存: %d件", len(top))

    export_json(conn, OUTPUT_JSON)
    conn.close()
    log.info("✅ 完了")


if __name__ == "__main__":
    main()
