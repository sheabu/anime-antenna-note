import json
import os
import requests
import time

DATA_FILE = 'notes_data.json'
ANIME_LIST_FILE = 'anime_list.json'

def main():
    print("🚀 ディープスキャンを再開します（各作品最大50件）...")
    
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

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
    
    for anime in anime_list:
        print(f"🔍 {anime['title']} を検索中...")
        count_per_anime = 0
        
        for page in range(1, 11): # 1ページ約6〜10件
            if count_per_anime >= 50: break
                
            search_url = f"https://note.com/api/v2/search/notes?q={anime['title']}&kind=note&page={page}"
            try:
                resp = session.get(search_url, timeout=15)
                
                if resp.status_code == 429:
                    print("⚠️ 制限検知。1分間待機します...")
                    time.sleep(60)
                    continue

                data = resp.json()
                items = data.get('data', {}).get('notes', [])
                if not items: break 
                
                for note in items:
                    if count_per_anime >= 50: break
                    url = f"https://note.com/{note['user']['urlname']}/n/{note['key']}"
                    if url not in existing_urls:
                        all_notes.append({"title": note['name'], "url": url, "anime_title": anime['title']})
                        existing_urls.add(url)
                        count_per_anime += 1
                
                time.sleep(2) # 礼儀正しい間隔
                
            except Exception as e:
                print(f"  [Skip] エラー: {e}")
                break
        
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_notes, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ 完了！総記事数: {len(all_notes)}件 (今回追加: {len(all_notes) - initial_count}件)")

if __name__ == "__main__":
    main()
