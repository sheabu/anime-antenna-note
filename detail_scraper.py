import json
import random
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_THUMBNAIL = 'https://via.placeholder.com/140x80?text=Anime'


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


def normalize_image_url(image_url, base_url):
    image_url = (image_url or '').strip()
    if not image_url:
        return ''
    return urljoin(base_url, image_url)


def scrape_thumbnail_from_html(session, note_url):
    try:
        resp = session.get(note_url, timeout=20, headers={'User-Agent': 'Mozilla/5.0', 'Referer': note_url})
        if resp.status_code != 200:
            return ''
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 1) og:image を最優先
        og = soup.find('meta', attrs={'property': 'og:image'}) or soup.find('meta', attrs={'name': 'og:image'})
        if og and og.get('content'):
            return normalize_image_url(og.get('content'), note_url)

        # 2) 本文の1枚目画像（遅延読み込み属性を考慮）
        candidates = soup.select('article img, main img, .note-body img, .o-noteContentText img, img')
        for img in candidates:
            src = (
                img.get('data-src')
                or img.get('data-original')
                or img.get('data-lazy-src')
                or img.get('src')
            )
            if not src and img.get('srcset'):
                src = img.get('srcset').split(',')[0].strip().split(' ')[0]
            normalized = normalize_image_url(src, note_url)
            if normalized:
                return normalized
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

            thumbnail = normalize_image_url(thumbnail, note_url)
            if not thumbnail:
                thumbnail = scrape_thumbnail_from_html(session, note_url)

            return {
                'like_count': int(payload.get('like_count') or 0),
                'note_title': (payload.get('name') or '').strip(),
                'posted_at': payload.get('publish_at') or '',
                'thumbnail': thumbnail or DEFAULT_THUMBNAIL,
            }
        if resp.status_code in (429, 503):
            time.sleep((attempt + 1) * 2)
            continue
        return None
    return None


def retry_missing_details():
    with open('notes_data.json', 'r', encoding='utf-8') as f:
        notes = json.load(f)
    
    # スキ数・タイトル・サムネイルの不足を再取得対象にする
    targets = [
        n for n in notes
        if n.get('like_count', 0) == 0
        or not n.get('note_title')
        or not str(n.get('thumbnail') or '').strip()
    ]
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
