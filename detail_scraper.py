import json
import time
import random
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

LIKE_SELECTORS = [
    '.st-Icon_heartCount',
    '.m-noteSkeleton_likeCount',
    '[data-testid="like-count"]',
    '[class*="heartCount"]',
    '[class*="likeCount"]'
]


def extract_like_count(page):
    for selector in LIKE_SELECTORS:
        el = page.query_selector(selector)
        if not el:
            continue
        text = el.inner_text().strip()
        m = re.search(r'(\d[\d,]*)', text)
        if m:
            return int(m.group(1).replace(',', ''))

    # フォールバック: ページ本文から「123 スキ」の形式を拾う
    page_text = page.inner_text('body')
    m = re.search(r'(\d[\d,]*)\s*スキ', page_text)
    if m:
        return int(m.group(1).replace(',', ''))
    return 0


def save_notes(notes):
    tmp = Path('notes_data.json.tmp')
    tmp.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace('notes_data.json')


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
                url = (note.get('url') or '').strip()
                if not url.startswith('http'):
                    print(f"[{i+1}/{len(targets)}] スキップ: URL不正")
                    continue

                print(f"[{i+1}/{len(targets)}] 取得中: {url}")
                time.sleep(random.uniform(4, 7)) # 制限回避のため長めに待機
                page.goto(url, timeout=60000, wait_until='domcontentloaded')
                
                # スキ数の取得
                note['like_count'] = extract_like_count(page)
                
                # タイトルの取得
                title_el = page.query_selector('h1')
                if title_el:
                    note['note_title'] = title_el.inner_text().strip()

                # 10件ごとに保存
                if (i + 1) % 10 == 0:
                    save_notes(notes)
            except Exception as e:
                print(f"❌ エラー: {note.get('url', '')} ({e})")
                continue
        
        save_notes(notes)
        browser.close()

if __name__ == "__main__":
    retry_missing_details()
