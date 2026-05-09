import json
import os
import requests
import time
import random
from urllib.parse import quote

from article_filters import load_filter_config, title_matches_anime

DATA_FILE = 'notes_data.json'
ANIME_LIST_FILE = 'anime_list.json'
MAX_PAGES_PER_ANIME = int(os.getenv("SCRAPE_MAX_PAGES", "3"))
MAX_NEW_PER_ANIME = int(os.getenv("SCRAPE_MAX_NEW_PER_ANIME", "20"))
MIN_SLEEP_SEC = float(os.getenv("SCRAPE_SLEEP_MIN", "0.6"))
MAX_SLEEP_SEC = float(os.getenv("SCRAPE_SLEEP_MAX", "1.5"))

def main():
    print("🥋 最終兵器：超・擬態モードで再挑戦します...")
    
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                all_notes = json.load(f)
            except:
                all_notes = []
    else:
        all_notes = []

    existing_urls = {note['url'] for note in all_notes}
    initial_count = len(all_notes)
    
    with open(ANIME_LIST_FILE, 'r', encoding='utf-8') as f:
        anime_list = json.load(f)

    filter_cfg = load_filter_config()

    session = requests.Session()
    # ブラウザが送る「本物の情報」をより正確に再現
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        'Origin': 'https://note.com',
        'Referer': 'https://note.com/search?q=anime&kind=note'
    })
    
    # 全作品を対象に巡回（以前は先頭20件だけだったため最新記事の取りこぼしが起きていた）
    for anime in anime_list:
        print(f"🕵️ {anime['title']} を探索中...")
        count_per_anime = 0
        
        # 検索キーワードをURL用に安全な形に変換（日本語対策）
        encoded_query = quote(anime['title'])
        
        for page in range(1, MAX_PAGES_PER_ANIME + 1):
            if count_per_anime >= MAX_NEW_PER_ANIME:
                break
            
            # ブラウザが実際に叩いている「最新の」エンドポイントを試す
            search_url = f"https://note.com/api/v2/search/combined?q={encoded_query}&kind=note&page={page}"
            
            try:
                resp = session.get(search_url, timeout=15)
                
                if resp.status_code != 200:
                    print(f"  ❌ ステータス: {resp.status_code} (一旦飛ばします)")
                    break

                data = resp.json()
                # combined APIの場合は構造が少し違うため調整
                items = data.get('data', {}).get('notes', [])
                if not items:
                    # もしnotesになければ、別の階層を探す
                    items = data.get('data', {}).get('search_results', {}).get('notes', [])
                
                if not items: break 
                
                for note in items:
                    if count_per_anime >= MAX_NEW_PER_ANIME:
                        break
                    user = note.get('user') or {}
                    urlname = user.get('urlname')
                    key = note.get('key')
                    if not urlname or not key:
                        continue
                    note_name = (note.get('name') or '').strip()
                    url = f"https://note.com/{urlname}/n/{key}"
                    if url not in existing_urls and title_matches_anime(note_name, anime['title'], filter_cfg):
                        all_notes.append({"title": note_name, "url": url, "anime_title": anime['title']})
                        existing_urls.add(url)
                        count_per_anime += 1
                
                # 全作品巡回するため、待機は短めにして収集幅を優先
                time.sleep(random.uniform(MIN_SLEEP_SEC, MAX_SLEEP_SEC))
                
            except Exception as e:
                print(f"  [Error] {e}")
                break
        
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_notes, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ 探索終了！")
    print(f"・新しく追加された記事: {len(all_notes) - initial_count} 件")
    print(f"・現在の総蓄積数: {len(all_notes)} 件")

if __name__ == "__main__":
    main()
