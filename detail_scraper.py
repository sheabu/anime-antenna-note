import json
import time
import random
from playwright.sync_api import sync_playwright

def retry_missing_details():
    with open('notes_data.json', 'r', encoding='utf-8') as f:
        notes = json.load(f)
    
    # ハートが0、またはタイトルが取得できていないものを「未取得」として抽出
    targets = [n for n in notes if n.get('like_count', 0) == 0 or not n.get('note_title')]
    print(f"🚀 スキ数未取得のデータ {len(targets)} 件の再更新を開始します...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for i, note in enumerate(targets):
            try:
                print(f"[{i+1}/{len(targets)}] 取得中: {note['url']}")
                time.sleep(random.uniform(4, 7)) # 制限回避のため長めに待機
                page.goto(note['url'], timeout=60000)
                
                # スキ数の取得
                like_el = page.query_selector('.st-Icon_heartCount, .m-noteSkeleton_likeCount')
                if like_el:
                    count_text = like_el.inner_text().replace(',', '').strip()
                    note['like_count'] = int(count_text) if count_text else 0
                
                # タイトルの取得
                title_el = page.query_selector('h1')
                if title_el:
                    note['note_title'] = title_el.inner_text().strip()

                # 10件ごとに保存
                if i % 10 == 0:
                    with open('notes_data.json', 'w', encoding='utf-8') as f:
                        json.dump(notes, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"❌ エラー: {note['url']}")
                continue
        
        with open('notes_data.json', 'w', encoding='utf-8') as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)
        browser.close()

if __name__ == "__main__":
    retry_missing_details()
