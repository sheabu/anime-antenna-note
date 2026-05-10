#!/usr/bin/env bash
# results.json → notes_data.json 反映後、ランキング更新・GitHub に push（Pages が更新される）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RESULTS="${RESULTS_JSON:-$ROOT/results.json}"
if [[ ! -f "$RESULTS" ]]; then
  echo "results.json がありません: $RESULTS"
  echo "例: RESULTS_JSON=/path/to/results.json $0"
  exit 1
fi

python3 scripts/merge_results_to_notes.py --results "$RESULTS"
# clean_data は記事タイトルが作品名と一致しない場合に大量削除するため、
# fetch_note で集めた記事を優先して載せるときはデフォルトでスキップする。
if [[ "${RUN_CLEAN_DATA:-0}" == "1" ]]; then
  python3 clean_data.py
fi
python3 generate_x_ranking.py

git add notes_data.json x_ranking.json
if git diff --cached --quiet; then
  echo "変更なし（すべて既存URLと重複している可能性があります）。"
  exit 0
fi

MSG="${COMMIT_MSG:-chore: merge fetch_note results into notes_data [$(date '+%Y-%m-%d %H:%M')]}"
git commit -m "$MSG"
git pull --rebase origin main
git push origin main

echo "完了: ${ROOT}/notes_data.json を push しました。GitHub Pages のデプロイ完了を待ってサイトを再読込してください。"
