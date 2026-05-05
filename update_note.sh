#!/bin/bash
# 1. フォルダに移動
cd /Users/abesho/Downloads/note-template-v1/anime-antenna

# 2. 蓄積モードでプログラムを実行
python3 scraper.py

# 3. 増えたデータをネットに公開
git add notes_data.json
git commit -m "Auto-update: note実データ蓄積反映"
git push origin main
