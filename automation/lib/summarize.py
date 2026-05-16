"""OpenAI を使った軽量テキスト要約。

OPENAI_API_KEY が無い場合は先頭抜粋でフォールバックする（巡回自体は止めない）。
"""

from __future__ import annotations

import requests

_API = "https://api.openai.com/v1/chat/completions"
_MODEL = "gpt-4o-mini"


def _fallback(text: str, limit: int) -> str:
    flat = " ".join(text.split())
    return flat[:limit] + ("…" if len(flat) > limit else "")


def summarize(text: str, api_key: str, *, context: str = "", limit: int = 200) -> str:
    """text を日本語で簡潔に要約する。失敗時は抜粋を返す。"""
    text = (text or "").strip()
    if not text:
        return "(本文なし)"
    if not api_key:
        return _fallback(text, limit)

    prompt = (
        f"次のWebページの更新内容を、日本語で{limit}字以内の箇条書き要約にしてください。"
        f"{('対象: ' + context) if context else ''}\n\n{text[:6000]}"
    )
    try:
        resp = requests.post(
            _API,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": _MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 400,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # 要約失敗で巡回全体を止めない
        return f"{_fallback(text, limit)}\n（要約APIエラー: {exc}）"
