#!/usr/bin/env python3
"""
500作品のアニメタイトルに基づき、note検索から作品ごとに人気寄りの記事を最大N件取得し JSON に保存する。

ブロック回避のため待機・UAローテーション・リトライを実装。
長時間実行・中断再開（レジューム）に対応。

Warp / 長時間実行の例（Mac・スリープ防止）::

    caffeinate -dims python3 scripts/fetch_note_articles_500.py --max-works 50

数件テスト::

    python3 scripts/fetch_note_articles_500.py --start-index 0 --max-works 2 --per-work 5
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

# プロジェクトルート（scripts/ の親）
ROOT = Path(__file__).resolve().parents[1]


def log(msg: str) -> None:
    print(msg, flush=True)


def load_fake_ua():
    try:
        from fake_useragent import UserAgent

        return UserAgent()
    except Exception:
        log("[warn] fake-useragent unavailable; using static User-Agent lists.")
        return None


STATIC_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


def rotate_user_agent(session: requests.Session, ua_gen) -> None:
    if ua_gen is not None:
        try:
            session.headers["User-Agent"] = ua_gen.random
        except Exception:
            session.headers["User-Agent"] = random.choice(STATIC_USER_AGENTS)
    else:
        session.headers["User-Agent"] = random.choice(STATIC_USER_AGENTS)


def build_session(ua_gen) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Origin": "https://note.com",
            "Referer": "https://note.com/",
        }
    )
    rotate_user_agent(s, ua_gen)
    return s


def request_with_retry(
    session: requests.Session,
    ua_gen,
    method: str,
    url: str,
    *,
    max_retries: int = 5,
    timeout: int = 25,
    **kwargs,
) -> requests.Response:
    """429 / 403 / 5xx を指数バックオフで最大 max_retries 回まで再試行。"""
    last_err: Exception | None = None
    for attempt in range(max_retries):
        rotate_user_agent(session, ua_gen)
        try:
            resp = session.request(method, url, timeout=timeout, **kwargs)
            if resp.status_code in (429, 403):
                wait = min(30 * (2**attempt), 600) + random.uniform(0, 5)
                log(
                    f"    [retry {attempt + 1}/{max_retries}] HTTP {resp.status_code} -> sleep {wait:.1f}s"
                )
                time.sleep(wait)
                continue
            if 500 <= resp.status_code < 600:
                wait = min(10 * (2**attempt), 300) + random.uniform(0, 3)
                log(
                    f"    [retry {attempt + 1}/{max_retries}] HTTP {resp.status_code} -> sleep {wait:.1f}s"
                )
                time.sleep(wait)
                continue
            return resp
        except (requests.RequestException, OSError) as e:
            last_err = e
            wait = min(5 * (2**attempt), 120) + random.uniform(0, 2)
            log(f"    [retry {attempt + 1}/{max_retries}] {e!r} -> sleep {wait:.1f}s")
            time.sleep(wait)
    if last_err:
        raise last_err
    raise RuntimeError("request_with_retry: exceeded retries without response")


def extract_note_items(data: dict) -> list[dict]:
    """combined 検索のレスポンスから notes 配列を取り出す。"""
    root = data.get("data") or {}
    notes = root.get("notes")
    if isinstance(notes, list) and notes:
        return notes
    sr = root.get("search_results") or {}
    notes = sr.get("notes")
    if isinstance(notes, list):
        return notes
    return []


def note_url_from_item(note: dict) -> str | None:
    user = note.get("user") or {}
    urlname = user.get("urlname")
    key = note.get("key")
    if not urlname or not key:
        return None
    return f"https://note.com/{urlname}/n/{key}"


def extract_note_key(url: str) -> str:
    parts = url.rstrip("/").split("/")
    return parts[-1] if parts else ""


def fetch_note_detail(
    session: requests.Session,
    ua_gen,
    note_url: str,
) -> dict[str, Any] | None:
    key = extract_note_key(note_url)
    if not key.startswith("n") or len(key) < 8:
        return None
    api_url = f"https://note.com/api/v3/notes/{key}"
    headers = {"Referer": note_url}
    resp = request_with_retry(session, ua_gen, "GET", api_url, headers=headers, timeout=25)
    if resp.status_code != 200:
        return None
    payload = (resp.json() or {}).get("data") or {}
    user = payload.get("user") or {}
    author = (
        (user.get("name") or "").strip()
        or (user.get("nickname") or "").strip()
        or (user.get("urlname") or "").strip()
    )
    title = (payload.get("name") or "").strip()
    like_count = int(payload.get("like_count") or 0)
    posted_at = payload.get("publish_at") or payload.get("created_at") or ""
    return {
        "title": title,
        "url": note_url,
        "like_count": like_count,
        "posted_at": posted_at,
        "author_name": author,
    }


def collect_search_candidates(
    session: requests.Session,
    ua_gen,
    anime_title: str,
    max_pages: int,
) -> list[dict]:
    """検索APIで複数ページ取得し、ノート辞書のリストを返す（重複キーは後で除外）。"""
    encoded = quote(anime_title)
    collected: list[dict] = []
    for page in range(1, max_pages + 1):
        search_url = (
            f"https://note.com/api/v2/search/combined"
            f"?q={encoded}&kind=note&page={page}"
        )
        resp = request_with_retry(session, ua_gen, "GET", search_url, timeout=20)
        if resp.status_code != 200:
            log(f"    search page {page}: HTTP {resp.status_code} -> stop pages")
            break
        try:
            data = resp.json()
        except json.JSONDecodeError:
            break
        items = extract_note_items(data)
        if not items:
            break
        collected.extend(items)
        time.sleep(random.uniform(3.0, 7.0))
    return collected


def dedupe_by_url(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for n in items:
        u = note_url_from_item(n)
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(n)
    return out


def enrich_and_pick_top(
    session: requests.Session,
    ua_gen,
    candidates: list[dict],
    target_count: int,
    detail_delay_min: float,
    detail_delay_max: float,
) -> list[dict[str, Any]]:
    """
    各候補に対し v3 で詳細を取得し、like_count でソートして上位 target_count 件。
    """
    details: list[dict[str, Any]] = []
    for i, raw in enumerate(candidates):
        url = note_url_from_item(raw)
        if not url:
            continue
        try:
            d = fetch_note_detail(session, ua_gen, url)
            if d and d.get("title"):
                details.append(d)
        except Exception as e:
            log(f"    [detail error] {url} -> {e!r}")
        if i + 1 < len(candidates):
            time.sleep(random.uniform(detail_delay_min, detail_delay_max))
    details.sort(key=lambda x: int(x.get("like_count") or 0), reverse=True)
    return details[:target_count]


def load_results(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"meta": {}, "works": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"meta": {}, "works": []}


def save_results_atomic(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def upsert_work(
    data: dict[str, Any],
    index: int,
    anime_title: str,
    articles: list[dict[str, Any]],
) -> None:
    works = data.setdefault("works", [])
    entry = {
        "index": index,
        "anime_title": anime_title,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(articles),
        "articles": articles,
    }
    replaced = False
    for i, w in enumerate(works):
        if w.get("index") == index:
            works[i] = entry
            replaced = True
            break
    if not replaced:
        works.append(entry)
    works.sort(key=lambda x: x.get("index", 0))
    data["meta"] = {
        "last_completed_index": index,
        "total_works_scheduled": data.get("meta", {}).get("total_works_scheduled"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch popular note articles per anime title (large batch).")
    p.add_argument(
        "--anime-list",
        type=Path,
        default=ROOT / "anime_list.json",
        help="Path to anime list JSON (array of {title: ...})",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results.json",
        help="Output JSON path (resume / merge)",
    )
    p.add_argument("--start-index", type=int, default=None, help="0-based index in anime list to start from")
    p.add_argument("--max-works", type=int, default=500, help="Max number of titles to process from start-index")
    p.add_argument("--per-work", type=int, default=30, help="Target articles per anime (top by likes after enrich)")
    p.add_argument(
        "--search-pages",
        type=int,
        default=12,
        help="Max search API pages per anime (each page ~ several notes); increase if fewer than per-work hits",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    ua_gen = load_fake_ua()

    anime_path = args.anime_list
    if not anime_path.is_absolute():
        anime_path = ROOT / anime_path
    out_path = args.output
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    with open(anime_path, "r", encoding="utf-8") as f:
        anime_list = json.load(f)

    total_titles = len(anime_list)
    data = load_results(out_path)
    meta = data.setdefault("meta", {})
    meta["total_works_scheduled"] = total_titles

    start = args.start_index
    if start is None:
        start = int(meta.get("last_completed_index", -1)) + 1
    if start < 0 or start >= total_titles:
        log(f"[fatal] start-index out of range: {start} (list length {total_titles})")
        sys.exit(1)

    end = min(start + args.max_works, total_titles)
    log(f"━━━ fetch_note_articles_500 ━━━")
    log(f"Anime list: {anime_path}")
    log(f"Output: {out_path}")
    log(f"Titles in list: {total_titles}")
    log(f"Processing indices [{start}, {end})  (= {end - start} works)")
    log(f"Target per work: {args.per_work} articles (by like_count after detail fetch)")
    log(f"Sleep: 10–25s per work start, 3–7s per search page, 2–5s between detail API calls")
    log("")

    detail_min = float(os.environ.get("FETCH_DETAIL_SLEEP_MIN", "2"))
    detail_max = float(os.environ.get("FETCH_DETAIL_SLEEP_MAX", "5"))

    session = build_session(ua_gen)

    for idx in range(start, end):
        item = anime_list[idx]
        title = str(item.get("title") or "").strip()
        if not title:
            log(f"[{idx + 1}/{total_titles}] skip empty title at index {idx}")
            continue

        log(f"[{idx + 1}/{total_titles}] 開始: {title}")

        try:
            time.sleep(random.uniform(10.0, 25.0))

            raw_candidates = collect_search_candidates(
                session, ua_gen, title, max_pages=args.search_pages
            )
            candidates = dedupe_by_url(raw_candidates)

            if not candidates:
                log(f"  -> 検索結果なし。空で保存します。")
                upsert_work(data, idx, title, [])
                save_results_atomic(out_path, data)
                continue

            # 人気順確定のため多めに詳細取得するが、件数は上限で抑える（全件だと極端に遅い）
            need_fetch = min(
                len(candidates),
                max(args.per_work * 2, args.per_work + 15),
            )
            candidates = candidates[:need_fetch]

            articles = enrich_and_pick_top(
                session,
                ua_gen,
                candidates,
                target_count=args.per_work,
                detail_delay_min=detail_min,
                detail_delay_max=detail_max,
            )

            upsert_work(data, idx, title, articles)
            save_results_atomic(out_path, data)
            log(f"  -> 保存 {len(articles)} 件（like順上位）")
        except KeyboardInterrupt:
            log("[interrupt] ユーザー中断。ここまでの进度は results.json に保存されている行まで確認してください。")
            raise
        except Exception as e:
            log(f"  [ERROR] index={idx} title={title!r}: {e!r}")
            traceback.print_exc()

    log("")
    log(f"完了: インデックス {start} ～ {end - 1} まで処理。出力 {out_path}")


if __name__ == "__main__":
    main()
