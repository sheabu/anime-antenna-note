#!/usr/bin/env bash
# launchd / 手動実行の共通ランナー。
# 使い方: ./run.sh daily_briefing.py [--dry-run]
#         ./run.sh auto_pilot.py
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="${1:?実行する .py を指定してください}"
shift || true

mkdir -p "$DIR/logs"
LOG="$DIR/logs/$(basename "${SCRIPT%.py}")-$(date +%Y%m%d).log"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') start $SCRIPT =====" >> "$LOG"
# caffeinate: スクレイピング中の自動スリープを防止
caffeinate -dims "$DIR/.venv/bin/python" "$DIR/$SCRIPT" "$@" >> "$LOG" 2>&1
STATUS=$?
echo "===== $(date '+%Y-%m-%d %H:%M:%S') end $SCRIPT (exit $STATUS) =====" >> "$LOG"
exit $STATUS
