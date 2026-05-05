import json
import os
import requests
from bs4 import BeautifulSoup
import time

# 設定
DATA_FILE = 'notes_data.json'
ANIME_LIST_FILE = 'anime_list.json'

def load_anime_list():
    with open(ANIME_LIST_FILE, 'r') as f:
        return json.load(f)

def fetch_rss_for_anime(anime, session):
    """RSSから最新の記事を取得する"""
    rss_url = f"https://note.com/hashtag/{anime['title']}/rss"
    try:
        resp = session.get(rss_url, timeout=10)
        # XML解析用にlxmlがない場合はhtml.parserで代用
        soup = BeautifulSoup(resp.content, "html.parser")
        items = soup.find_all("item")
        
        results = []
        for item in items:
            results.append({
                "title": item.title.text,
                "url": item.link.text,
                "anime_title": anime['title']
            })
        return results
    except Exception as e:
        print(f"  [ERROR] {anime['title']} RSS取得失敗: {e}")
        return []

def main():
    print("🚀 蓄積モードでスクレイピングを開始します...")
    
    # 1. 既存の蓄積データを読み込む
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                all_notes = json.load(f)
            except:
                all_notes = []
    else:
        all_notes = []

    # 既に持っているURLを把握（重複防止のため）
    existing_urls = {note['url'] for note in all_notes}
    initial_count = len(all_notes)
    
    # 2. アニメ一覧を取得して巡回
    anime_list = load_anime_list()
    session = requests.Session()
    
    for anime in anime_list:
        print(f"🔍 {anime['title']} をチェック中...")
        new_items = fetch_rss_for_anime(anime, session)
        
        for item in new_items:
            if item['url'] not in existing_urls:
                all_notes.append(item)
                existing_urls.add(item['url'])
        
        time.sleep(1) # noteへの負荷軽減

    # 3. 保存
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_notes, f, ensure_ascii=False, indent=2)
    
    added_count = len(all_notes) - initial_count
    print(f"\n✅ 完了！")
    print(f"・新しく追加された記事: {added_count} 件")
    print(f"・現在の総蓄積数: {len(all_notes)} 件")

if __name__ == "__main__":
    main()
