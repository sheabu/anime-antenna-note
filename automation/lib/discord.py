"""Discord Webhook 通知。

Discord の content は 2000 文字制限のため、長文は分割送信する。
"""

from __future__ import annotations

import requests

_LIMIT = 1900  # 余裕を持たせた分割上限


def _chunks(text: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    size = 0
    for line in text.splitlines(keepends=True):
        if size + len(line) > _LIMIT and buf:
            out.append("".join(buf))
            buf, size = [], 0
        buf.append(line)
        size += len(line)
    if buf:
        out.append("".join(buf))
    return out or [text]


def send(webhook_url: str, content: str) -> None:
    """プレーンテキストを Discord に送信する。"""
    if not webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL が未設定です。")
    for chunk in _chunks(content):
        resp = requests.post(webhook_url, json={"content": chunk}, timeout=20)
        resp.raise_for_status()


def send_codeblock(webhook_url: str, title: str, body: str) -> None:
    """タイトル + コードブロックで送信する（X 投稿文プレビュー等）。"""
    send(webhook_url, f"**{title}**\n```\n{body}\n```")
