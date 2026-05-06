import json
import random
import time
from pathlib import Path
from urllib.parse import urlparse

import requests


def save_notes(notes):
    tmp = Path('notes_data.json.tmp')
    tmp.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace('notes_data.json')


def extract_note_key(url):
    try:
        path = urlparse(url).path
        key = path.rstrip('/').split('/')[-1]
        if key.startswith('n') and len(key) >= 8:
            return key
    except Exception:
        return ''
    return ''


def fetch_note_detail(session, note_url):
    key = extract_note_key(note_url)
    if not key:
        return None

    api_url = f'https://note.com/api/v3/notes/{key}'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json, text/plain, */*',
        'Referer': note_url,
    }

    for attempt in range(3):
        resp = session.get(api_url, headers=headers, timeout=20)
        if resp.status_code == 200:
            payload = resp.json().get('data') or {}
            eyecatch = payload.get('eyecatch')
            thumbnail = ''
            if isinstance(eyecatch, dict):
                thumbnail = eyecatch.get('path') or ''
            elif isinstance(eyecatch, str):
                thumbnail = eyecatch

            return {
                'like_count': int(payload.get('like_count') or 0),
                'note_title': (payload.get('name') or '').strip(),
                'posted_at': payload.get('publish_at') or '',
                'thumbnail': thumbnail,
            }
        if resp.status_code in (429, 503):
            time.sleep((attempt + 1) * 2)
            continue
        return None
    return None


def retry_missing_details():
    with open('notes_data.json', 'r', encoding='utf-8') as f:
        notes = json.load(f)
    
    # ハートが0、またはタイトルが取得できていないものを「未取得」として抽出
    targets = [n for n in notes if n.get('like_count', 0) == 0 or not n.get('note_title')]
    print(f"🚀 スキ数未取得のデータ {len(targets)} 件の再更新を開始します...")

    session = requests.Session()

    for i, note in enumerate(targets):
        try:
            url = (note.get('url') or '').strip()
            if not url.startswith('http'):
                print(f"[{i+1}/{len(targets)}] スキップ: URL不正")
                continue

            print(f"[{i+1}/{len(targets)}] 取得中: {url}")
            detail = fetch_note_detail(session, url)
            if not detail:
                print(f"⚠️ 取得失敗: {url}")
                continue

            note['like_count'] = detail['like_count']
            if detail['note_title']:
                note['note_title'] = detail['note_title']
            if detail['posted_at']:
                note['posted_at'] = detail['posted_at']
            if detail['thumbnail']:
                note['thumbnail'] = detail['thumbnail']

            if (i + 1) % 20 == 0:
                save_notes(notes)

            # レート制御
            time.sleep(random.uniform(0.05, 0.2))
        except Exception as e:
            print(f"❌ エラー: {note.get('url', '')} ({e})")
            continue

    save_notes(notes)

if __name__ == "__main__":
    retry_missing_details()
