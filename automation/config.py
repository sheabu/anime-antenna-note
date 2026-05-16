"""共通設定: パス解決と .env 読み込み。

自動化スイート全体がこのモジュールから設定を取得する。
シークレットは automation/.env（git 管理外）に置く。
OPENAI_API_KEY など既存キーは anime-antenna-tools/.env からも読み込む。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

AUTOMATION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = AUTOMATION_DIR.parent                      # anime-antenna/
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
LOG_DIR = AUTOMATION_DIR / "logs"
VENV_PYTHON = AUTOMATION_DIR / ".venv" / "bin" / "python"

# 既存の共有 .env（OPENAI_API_KEY 等）。automation/.env を優先する。
_SHARED_ENV = PROJECT_ROOT.parent / "anime-antenna-tools" / ".env"

load_dotenv(AUTOMATION_DIR / ".env")
if _SHARED_ENV.exists():
    load_dotenv(_SHARED_ENV, override=False)

LOG_DIR.mkdir(exist_ok=True)


def get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def require(name: str) -> str:
    value = get(name)
    if not value:
        raise RuntimeError(
            f"環境変数 {name} が未設定です。automation/.env に設定してください。"
        )
    return value


# --- データファイル（既存サイト資産） ---
NOTES_DATA = PROJECT_ROOT / "notes_data.json"
RESULTS_JSON = PROJECT_ROOT / "results.json"
X_RANKING_JSON = PROJECT_ROOT / "x_ranking.json"

# --- 競合巡回設定 ---
COMPETITORS_CONFIG = AUTOMATION_DIR / "competitors.json"
