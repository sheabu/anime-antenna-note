import json
import os
import time
import random
import re
from playwright.sync_api import sync_playwright

DATA_FILE = 'notes_data.json'
ANIME_LIST_FILE = 'anime_list.json'

def is_relevant_title(title, anime_title):
    t = re.sub(r"[\s　・!！?？:：()（）「」『』【】\-\u3000]", "", str(title or "")).lower()
    a = re.sub(r"[\s　・!！?？:：()（）「」『』【】\-\u3000]", "", str(anime_title or "")).lower()
    if not t or t == "notearticle":
        return False
    if a and a in t:
        return True
    anchors = [w for w in re.split(r"[ 　/・]", anime_title) if len(w) >= 2]
    return any(re.sub(r"[\s　]", "", w).lower() in t for w in anchors)


def main():
    print("🎭 全件スキャンモードを開始します。お昼休憩の間にMacに任せましょう...")
    
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
    
    if not os.path.exists(ANIME_LIST_FILE):
        print(f"❌ {ANIME_LIST_FILE} が見つかりません。")
        return

    with open(ANIME_LIST_FILE, 'r', encoding='utf-8') as f:
        anime_list = json.load(f)

    # 制限を解除し、リストにある全作品を対象にします
    test_list = anime_list 

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for anime in test_list:
            print(f"📺 {anime['title']} を検索中...")
            search_url = f"https://note.com/search?q={anime['title']}&kind=note"
            
            try:
                page.goto(search_url, wait_until="networkidle", timeout=60000)
                page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(random.uniform(2, 4))

                links = page.query_selector_all('a[href*="/n/"]')
                count_per_anime = 0
                for link in links:
                    if count_per_anime >= 30: break # 各作品30件程度
                    raw_url = link.get_attribute('href')
                    if not raw_url: continue
                    full_url = raw_url if raw_url.startswith('http') else f"https://note.com{raw_url.split('?')[0]}"
                    link_text = (link.inner_text() or "").strip()
                    if full_url not in existing_urls and is_relevant_title(link_text, anime['title']):
                        all_notes.append({
                            "title": "note article",
                            "note_title": link_text,
                            "url": full_url,
                            "anime_title": anime['title'],
                            "like_count": 0
                        })
                        existing_urls.add(full_url)
                        count_per_anime += 1
                print(f"  ✅ {count_per_anime} 件取得")
            except Exception as e:
                print(f"  ⚠️ スキップ: {e}")
            
            # ブロックを避けるための休憩時間
            time.sleep(random.uniform(4, 7))
        browser.close()

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_notes, f, ensure_ascii=False, indent=2)
    print(f"\n✨ 完了！現在の総記事数: {len(all_notes)} 件")

if __name__ == "__main__":
    main()
