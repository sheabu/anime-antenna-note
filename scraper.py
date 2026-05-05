import json
import os
import requests
import time

DATA_FILE = 'notes_data.json'
ANIME_LIST_FILE = 'anime_list.json'

def main():
    print("🌕 深夜の超ディープスキャンを開始します（各作品最大50件）...")
    
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
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
    
    for anime in anime_list:
        print(f"🔥 {anime['title']} を収穫中...")
        count_per_anime = 0
        
        # 1ページ約6〜10件なので、50件に到達するまで最大15ページ分回します
        for page in range(1, 16): 
            if count_per_anime >= 50:
                break
                
            search_url = f"https://note.com/api/v2/search/notes?q={anime['title']}&kind=note&page={page}"
            try:
                resp = session.get(search_url, timeout=10)
                data = resp.json()
                items = data.get('data', {}).get('notes', [])
                
                if not items:
                    break 
                
                for note in items:
                    if count_per_anime >= 50:
                        break
                        
                    url = f"https://note.com/{note['user']['urlname']}/n/{note['key']}"
                    if url not in existing_urls:
                        all_notes.append({
                            "title": note['name'],
                            "url": url,
                            "anime_title": anime['title']
                        })
                        existing_urls.add(url)
                        count_per_anime += 1
                
                print(f"  └ {page}ページ目完了（累計 {count_per_anime}件取得）")
                time.sleep(1.2) # noteのサーバーに配慮して少し長めに待機
                
            except Exception as e:
                print(f"  [停止] エラーが発生しました: {e}")
                break
        
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_notes, f, ensure_ascii=False, indent=2)
    
    final_count = len(all_notes)
    print(f"\n✨ スキャン完了！")
    print(f"・今回新しく追加: {final_count - initial_count} 件")
    print(f"・サイトの総記事数: {final_count} 件")

if __name__ == "__main__":
    main()
