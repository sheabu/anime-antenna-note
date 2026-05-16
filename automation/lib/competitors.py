"""競合サイトのバックグラウンド巡回。

competitors.json で対象サイトを設定する。各サイトのトップから
最新記事の見出し・抜粋を抽出して返す（要約は呼び出し側で行う）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import requests
from bs4 import BeautifulSoup

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class CrawlResult:
    name: str
    url: str
    headlines: list[str] = field(default_factory=list)
    text: str = ""
    error: str = ""


def load_config(path: Path) -> list[dict]:
    """competitors.json を読む。無ければ空リスト。"""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("sites", []) if isinstance(data, dict) else data


def _fetch(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": _UA}, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or resp.encoding
    return resp.text


def crawl_site(site: dict, *, max_headlines: int = 8) -> CrawlResult:
    """1サイトを巡回。site = {name, url, selector?}。"""
    name = site.get("name", site.get("url", "?"))
    url = site.get("url", "")
    result = CrawlResult(name=name, url=url)
    if not url:
        result.error = "url が未設定"
        return result
    try:
        soup = BeautifulSoup(_fetch(url), "lxml")
        selector = site.get("selector")
        if selector:
            nodes = soup.select(selector)
        else:
            # 既定: h1〜h3 と記事リンクから見出しを推定
            nodes = soup.select("h1, h2, h3, article a, .entry-title")
        seen: set[str] = set()
        for node in nodes:
            title = " ".join(node.get_text().split())
            if 6 <= len(title) <= 120 and title not in seen:
                seen.add(title)
                result.headlines.append(title)
            if len(result.headlines) >= max_headlines:
                break
        result.text = "\n".join(result.headlines)
    except Exception as exc:
        result.error = str(exc)
    return result


def crawl_all(sites: list[dict]) -> list[CrawlResult]:
    return [crawl_site(s) for s in sites]
