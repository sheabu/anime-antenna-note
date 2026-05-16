"""Notion API クライアント（タスク管理 DB の取得・整理）。

Notion API v1 (2022-06-28) の databases query を使用。
プロパティ名は DB ごとに異なるため、型ベースで柔軟に値を抽出する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

import requests

_API = "https://api.notion.com/v1"
_VERSION = "2022-06-28"


@dataclass
class Task:
    title: str
    status: str = ""
    due: date | None = None
    url: str = ""

    @property
    def is_done(self) -> bool:
        return self.status in {"Done", "完了", "Complete", "済"}


@dataclass
class TaskBoard:
    overdue: list[Task] = field(default_factory=list)
    today: list[Task] = field(default_factory=list)
    upcoming: list[Task] = field(default_factory=list)
    no_date: list[Task] = field(default_factory=list)
    done_recent: list[Task] = field(default_factory=list)


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": _VERSION,
        "Content-Type": "application/json",
    }


def _extract_title(props: dict) -> str:
    for prop in props.values():
        if prop.get("type") == "title":
            parts = prop.get("title") or []
            return "".join(p.get("plain_text", "") for p in parts).strip()
    return "(無題)"


def _extract_status(props: dict) -> str:
    for prop in props.values():
        t = prop.get("type")
        if t == "status" and prop.get("status"):
            return prop["status"].get("name", "")
        if t == "select" and prop.get("select"):
            return prop["select"].get("name", "")
    return ""


def _extract_due(props: dict) -> date | None:
    for prop in props.values():
        if prop.get("type") == "date" and prop.get("date"):
            start = prop["date"].get("start")
            if start:
                try:
                    return datetime.fromisoformat(start.replace("Z", "+00:00")).date()
                except ValueError:
                    return None
    return None


def fetch_tasks(token: str, database_id: str) -> list[Task]:
    """DB の全ページをページネーションで取得して Task に変換する。"""
    tasks: list[Task] = []
    payload: dict = {"page_size": 100}
    while True:
        resp = requests.post(
            f"{_API}/databases/{database_id}/query",
            headers=_headers(token),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        for page in data.get("results", []):
            props = page.get("properties", {})
            tasks.append(
                Task(
                    title=_extract_title(props),
                    status=_extract_status(props),
                    due=_extract_due(props),
                    url=page.get("url", ""),
                )
            )
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return tasks


def organize(tasks: list[Task], today: date | None = None) -> TaskBoard:
    """期日と完了状態でタスクを仕分ける。"""
    today = today or date.today()
    board = TaskBoard()
    for task in tasks:
        if task.is_done:
            if task.due and task.due >= today.replace(day=1):
                board.done_recent.append(task)
            continue
        if task.due is None:
            board.no_date.append(task)
        elif task.due < today:
            board.overdue.append(task)
        elif task.due == today:
            board.today.append(task)
        else:
            board.upcoming.append(task)
    board.overdue.sort(key=lambda t: t.due or today)
    board.upcoming.sort(key=lambda t: t.due or today)
    return board
