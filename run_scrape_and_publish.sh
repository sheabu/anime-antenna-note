#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "1/5 detail_scraper.py を実行します..."
python3 detail_scraper.py

echo "2/5 XランキングJSONを更新します..."
python3 generate_x_ranking.py

echo "3/5 変更をコミットします（その後 pull / push）..."
git add notes_data.json x_ranking.json
if git diff --cached --quiet; then
  echo "変更がないためコミットをスキップしました。"
else
  git commit -m "$(cat <<'EOF'
Auto-update: refresh likes and X hashtag ranking

EOF
)"
fi

echo "4/5 最新を取り込んで rebase します..."
git pull --rebase origin main

echo "5/5 GitHub へ push します..."
git push origin main

echo "完了: スクレイピング結果とXランキングを反映しました。"
