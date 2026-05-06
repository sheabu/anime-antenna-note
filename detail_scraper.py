import json
import os
import time
import random
from playwright.sync_api import sync_playwright

DATA_FILE = 'notes_data.json'

def update_note_details():
    if not os.path.exists(DATA_FILE): return

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        notes = json.load(f)

    # 【条件を緩めました】URLがあれば、とにかく全部見に行く設定です
    target_notes = [n for n in notes if n.get('url')]
    
    total = len(target_notes)
    print(f"🚀 合計 {total} 件の全件更新を開始します。長い戦いになりますが、Macに任せましょう！")

    with sync_playwright() as p:
        # 画面を見たい場合は headless=False にするとブラウザが立ち上がります
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for i, note in enumerate(target_notes):
            try:
                print(f"[{i+1}/{total}] 更新中: {note.get('note_title', 'No Title')}")
                page.goto(note['url'], wait_until="domcontentloaded", timeout=30000)
                
                # サーバーに怒られないよう、1〜2秒ランダムに待機
                time.sleep(random.uniform(1.2, 2.5))

                # スキ数を取得
                like_el = page.query_selector('.m-noteStatus__item .m-noteStatus__label')
                if like_el:
                    text = like_el.inner_text().replace(',', '').strip()
                    note['like_count'] = int(text) if text.isdigit() else 0
                
                # サムネイルをOGPから取得
                img_el = page.query_selector('meta[property="og:image"]')
                if img_el:
                    note['thumbnail'] = img_el.get_attribute('content')

                # 10件ごとにこまめに保存（これなら途中で止めても大丈夫）
                if i % 10 == 0:
                    with open(DATA_FILE, 'w', encoding='utf-8') as f:
                        json.dump(notes, f, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"  ⚠️ スキップ: {e}")
                continue

        browser.close()
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
    print("✨ すべての更新が完了しました！")

if __name__ == "__main__":
    update_note_details()
