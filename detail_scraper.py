import json
import os
import random
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_THUMBNAIL = './note-placeholder.svg'

HTML_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
}


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
    if not image_url or image_url.startswith('data:'):
        return ''
    if image_url.startswith('//'):
        return 'https:' + image_url
    if not re.match(r'^https?://', image_url, re.I):
        return urljoin(base_url, image_url)
    return image_url


def _pick_largest_from_srcset(srcset):
    if not srcset:
        return ''
    best_url, best_w = '', -1
    for part in srcset.split(','):
        part = part.strip()
        if not part:
            continue
        bits = part.split()
        url = bits[0]
        w = 0
        if len(bits) > 1 and bits[1].endswith('w'):
            try:
                w = int(bits[1][:-1])
            except ValueError:
                w = 0
        if w >= best_w:
            best_w = w
            best_url = url
    return best_url


def _is_junk_image_url(url):
    u = (url or '').lower()
    if not u:
        return True
    if 'spacer' in u or 'pixel.gif' in u or '1x1' in u:
        return True
    return False


def thumbnail_needs_refresh(note):
    t = str(note.get('thumbnail') or '').strip()
    if not t:
        return True
    if t.startswith('//'):
        return True
    if not re.match(r'^https?://', t, re.I):
        return True
    if 'via.placeholder.com' in t.lower():
        return True
    if 'note-placeholder.svg' in t.lower():
        return True
    return False


def scrape_thumbnail_from_html(session, note_url):
    try:
        resp = session.get(note_url, timeout=25, headers={**HTML_HEADERS, 'Referer': 'https://note.com/'})
        if resp.status_code != 200:
            return ''
        soup = BeautifulSoup(resp.text, 'lxml')

        # 1) og:image
        og = soup.find('meta', attrs={'property': 'og:image'}) or soup.find('meta', attrs={'name': 'og:image'})
        if og and og.get('content'):
            u = normalize_image_url(og.get('content'), note_url)
            if u and not _is_junk_image_url(u):
                return u

        # 1b) twitter:image
        tw = soup.find('meta', attrs={'name': 'twitter:image'}) or soup.find('meta', attrs={'property': 'twitter:image'})
        if tw and tw.get('content'):
            u = normalize_image_url(tw.get('content'), note_url)
            if u and not _is_junk_image_url(u):
                return u

        # 2) 本文の画像（遅延読み込み・srcset）
        candidates = soup.select(
            'article img, [class*="noteContent"] img, [class*="note-body"] img, main img, img'
        )
        for img in candidates:
            classes = ' '.join(img.get('class') or []).lower()
            if 'avatar' in classes or 'icon' in classes or 'emoji' in classes:
                continue

            src = (
                img.get('data-src')
                or img.get('data-original')
                or img.get('data-lazy-src')
                or img.get('data-srcset') and _pick_largest_from_srcset(img.get('data-srcset'))
            )
            if not src and img.get('srcset'):
                src = _pick_largest_from_srcset(img.get('srcset'))
            if not src:
                src = img.get('src')

            normalized = normalize_image_url(src, note_url)
            if normalized and not _is_junk_image_url(normalized) and not normalized.startswith('data:'):
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
                thumbnail = eyecatch.get('path') or eyecatch.get('url') or ''
            elif isinstance(eyecatch, str):
                thumbnail = eyecatch

            thumbnail = normalize_image_url(thumbnail, note_url)
            if not thumbnail or _is_junk_image_url(thumbnail):
                thumbnail = scrape_thumbnail_from_html(session, note_url)
            if not thumbnail:
                thumbnail = DEFAULT_THUMBNAIL

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
    # サムネ補完の1回あたり上限（タイムアウト対策）。環境変数で調整可能
    thumb_max = int(os.environ.get('THUMB_MAX_PER_RUN', '60'))

    with open('notes_data.json', 'r', encoding='utf-8') as f:
        notes = json.load(f)

    # サムネ未取得かつスキ/タイトルも未確定: 必ず全件処理（新規追加記事）
    targets_required = [
        n for n in notes
        if (n.get('like_count', 0) == 0 and thumbnail_needs_refresh(n))
        or not n.get('note_title')
    ]
    required_urls = {n.get('url') for n in targets_required}

    # サムネのみ欠損（スキ・タイトルは取得済み）: スキ数降順で上限件数に絞る
    targets_thumb = [
        n for n in notes
        if thumbnail_needs_refresh(n) and n.get('url') not in required_urls
    ]
    targets_thumb.sort(key=lambda n: int(n.get('like_count') or 0), reverse=True)
    targets_thumb = targets_thumb[:thumb_max]

    targets = targets_required + targets_thumb
    print(f"再取得対象: 必須={len(targets_required)}件 + サムネ補完={len(targets_thumb)}件（上限{thumb_max}件）")

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
            # placeholder以外の実URLが取れた場合のみ上書き
            if detail['thumbnail'] and detail['thumbnail'] != DEFAULT_THUMBNAIL:
                note['thumbnail'] = detail['thumbnail']

            if (i + 1) % 20 == 0:
                save_notes(notes)

            # レート制御（note.com のレート制限を避けるため控えめに）
            time.sleep(random.uniform(0.3, 0.8))
        except Exception as e:
            print(f"❌ エラー: {note.get('url', '')} ({e})")
            continue

    save_notes(notes)

if __name__ == "__main__":
    retry_missing_details()
