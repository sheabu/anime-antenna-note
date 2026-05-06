"""作品タイトルと記事のひも付きを強化（プラットフォームの「note」誤ヒットなどを除外）."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path


def normalize_text(text: str) -> str:
    """空白・記号除去 + 英字小文字化（日本語はそのまま lower の影響は主に ASCII）。"""
    return re.sub(
        r'[\s　・!！?？:：()（）「」『』【】\-\u3000]', "", str(text or "")
    ).lower()


@lru_cache(maxsize=1)
def load_filter_config(path: str | None = None) -> dict:
    p = Path(path or Path(__file__).parent / "article_filter_config.json")
    if not p.exists():
        return {"defaults": {}, "global_exclude_keywords": [], "works": {}}
    data = json.loads(p.read_text(encoding="utf-8"))
    return {
        "defaults": dict(data.get("defaults") or {}),
        "global_exclude_keywords": list(data.get("global_exclude_keywords") or []),
        "works": dict(data.get("works") or {}),
    }


def _contains_keyword(title: str, keyword: str) -> bool:
    if not keyword or not title:
        return False
    if keyword in title:
        return True
    if keyword.isascii():
        return keyword.lower() in title.lower()
    return False


def _work_rules_pass(anime_title: str, note_title: str, cfg: dict) -> bool | None:
    """作品固有ルールのみ適用。ルール未定義なら None。"""
    rules = (cfg.get("works") or {}).get(anime_title)
    if not rules:
        return None

    for ex in rules.get("exclude_keywords") or []:
        if _contains_keyword(note_title, ex):
            return False

    required_norm = rules.get("required_normalized_substrings") or []
    if required_norm:
        nt = normalize_text(note_title)
        if not any(sub in nt for sub in required_norm):
            return False

    required_raw = rules.get("required_keywords") or []
    if required_raw and not any(_contains_keyword(note_title, r) for r in required_raw):
        return False

    return True


def generic_work_match(note_title: str, anime_title: str, cfg: dict) -> bool:
    nt = normalize_text(note_title)
    at = normalize_text(anime_title)
    if at and at in nt:
        return True

    defaults = cfg.get("defaults") or {}
    min_len = int(defaults.get("min_anchor_length", 3))
    ignore_norm = set(defaults.get("ignore_anchors_normalized") or [])
    anchors = [w for w in re.split(r"[ 　/・]", anime_title) if len(str(w).strip()) >= 2]
    for a in anchors:
        an = normalize_text(a)
        if not an or an in ignore_norm:
            continue
        if len(an) < min_len:
            continue
        if an in nt:
            return True
    return False


def title_matches_anime(note_title: str, anime_title: str, cfg: dict | None = None) -> bool:
    """
    アンテナ上のひも付きが妥当かどうか。
    - 設定ファイルにある作品は required / exclude を優先。
    - それ以外は汎用一致（「NOTE」のみでの誤ヒットは ignore_anchors で防止）。
    """
    cfg = cfg or load_filter_config()
    note_title = str(note_title or "").strip()
    anime_title = str(anime_title or "").strip()

    for g in cfg.get("global_exclude_keywords") or []:
        if _contains_keyword(note_title, g):
            return False

    ruled = _work_rules_pass(anime_title, note_title, cfg)
    if ruled is not None:
        return ruled

    return generic_work_match(note_title, anime_title, cfg)
