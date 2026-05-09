import json
import os
import random
import re
import time
from urllib.parse import quote

import requests

from article_filters import load_filter_config, title_matches_anime

DATA_FILE = "notes_data.json"
ANIME_LIST_FILE = "anime_list.json"
MAX_PAGES_PER_ANIME = int(os.getenv("SCRAPE_MAX_PAGES", "2"))
MAX_NEW_PER_ANIME = int(os.getenv("SCRAPE_MAX_NEW_PER_ANIME", "8"))
MIN_SLEEP_SEC = float(os.getenv("SCRAPE_SLEEP_MIN", "0.5"))
MAX_SLEEP_SEC = float(os.getenv("SCRAPE_SLEEP_MAX", "1.2"))
MAX_WORKS = int(os.getenv("SCRAPE_MAX_WORKS", "0"))  # 0: 全件
SEARCH_PAGE_STEP = int(os.getenv("SCRAPE_PAGE_STEP", "20"))

NOTE_PATH_RE = re.compile(r"/([a-zA-Z0-9_.-]+)/n/(n[a-f0-9]+)")


def request_with_retry(session: requests.Session, url: str, *, timeout: int = 20) -> requests.Response | None:
    for attempt in range(5):
        try:
            resp = session.get(url, timeout=timeout)
            if resp.status_code in (403, 429) or 500 <= resp.status_code < 600:
                wait = min(2 ** attempt, 20) + random.uniform(0.2, 0.8)
                print(f"  [retry {attempt + 1}/5] {resp.status_code} -> {wait:.1f}s")
                time.sleep(wait)
                continue
            return resp
        except requests.RequestException as exc:
            wait = min(2 ** attempt, 20) + random.uniform(0.2, 0.8)
            print(f"  [retry {attempt + 1}/5] request error: {exc} -> {wait:.1f}s")
            time.sleep(wait)
    return None


def collect_candidate_urls_from_search_html(session: requests.Session, anime_title: str) -> list[str]:
    found: list[str] = []
    seen = set()
    encoded_query = quote(anime_title)
    for page_idx in range(MAX_PAGES_PER_ANIME):
        start = page_idx * SEARCH_PAGE_STEP
        search_url = f"https://note.com/search?q={encoded_query}&context=note&sort=new&start={start}"
        resp = request_with_retry(session, search_url)
        if resp is None or resp.status_code != 200:
            break
        html = resp.text
        matches = NOTE_PATH_RE.findall(html)
        if not matches:
            break
        for urlname, note_key in matches:
            url = f"https://note.com/{urlname}/n/{note_key}"
            if url in seen:
                continue
            seen.add(url)
            found.append(url)
        time.sleep(random.uniform(MIN_SLEEP_SEC, MAX_SLEEP_SEC))
    return found


def fetch_note_detail_name(session: requests.Session, note_url: str) -> tuple[str, str]:
    note_key = note_url.rstrip("/").split("/")[-1]
    detail_url = f"https://note.com/api/v3/notes/{note_key}"
    headers = {"Accept": "application/json", "Referer": note_url}
    resp = request_with_retry(session, detail_url, timeout=15)
    if resp is None or resp.status_code != 200:
        return "", ""
    try:
        payload = resp.json()
    except Exception:
        return "", ""
    data = payload.get("data") or {}
    return str(data.get("name") or "").strip(), str(data.get("publishAt") or "").strip()


def main():
    print("🥋 新着探索: HTML検索 + v3 詳細API で実行します...")

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                all_notes = json.load(f)
            except Exception:
                all_notes = []
    else:
        all_notes = []

    existing_urls = {note.get("url", "") for note in all_notes if note.get("url")}
    initial_count = len(all_notes)

    with open(ANIME_LIST_FILE, "r", encoding="utf-8") as f:
        anime_list = json.load(f)

    if MAX_WORKS > 0:
        anime_list = anime_list[:MAX_WORKS]

    filter_cfg = load_filter_config()

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Origin": "https://note.com",
            "Referer": "https://note.com/search?q=anime&context=note&sort=new",
        }
    )

    for i, anime in enumerate(anime_list, start=1):
        anime_title = (anime.get("title") or "").strip()
        if not anime_title:
            continue
        print(f"[{i}/{len(anime_list)}] 🕵️ {anime_title} を探索中...")
        count_per_anime = 0

        candidates = collect_candidate_urls_from_search_html(session, anime_title)
        for url in candidates:
            if count_per_anime >= MAX_NEW_PER_ANIME:
                break
            if url in existing_urls:
                continue
            note_name, posted_at = fetch_note_detail_name(session, url)
            if not note_name:
                continue
            if not title_matches_anime(note_name, anime_title, filter_cfg):
                continue
            all_notes.append(
                {
                    "title": note_name,
                    "url": url,
                    "anime_title": anime_title,
                    "posted_at": posted_at,
                }
            )
            existing_urls.add(url)
            count_per_anime += 1
            time.sleep(random.uniform(MIN_SLEEP_SEC, MAX_SLEEP_SEC))

        print(f"  -> 追加 {count_per_anime} 件")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_notes, f, ensure_ascii=False, indent=2)

    print("\n✨ 探索終了！")
    print(f"・新しく追加された記事: {len(all_notes) - initial_count} 件")
    print(f"・現在の総蓄積数: {len(all_notes)} 件")


if __name__ == "__main__":
    main()
