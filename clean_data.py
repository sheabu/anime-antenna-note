import json
import re


def normalize_text(text):
    return re.sub(r"[\s　・!！?？:：()（）「」『』【】\-\u3000]", "", str(text or "")).lower()


def is_relevant(note, anime_titles):
    anime_title = str(note.get("anime_title") or "").strip()
    note_title = str(note.get("note_title") or note.get("title") or "").strip()
    url = str(note.get("url") or "").strip()

    if anime_title not in anime_titles:
        return False
    if not url.startswith("https://note.com/"):
        return False
    if not note_title or note_title in {"403 ERROR", "note article"}:
        return False
    if "403" in note_title:
        return False

    # 作品名が記事タイトルに含まれているものを優先して残す
    nt = normalize_text(note_title)
    at = normalize_text(anime_title)
    if at and at in nt:
        return True

    # 代表キーワード一致（続編表記や短縮名のゆれを救済）
    anchors = [w for w in re.split(r"[ 　/・]", anime_title) if len(w) >= 2]
    return any(normalize_text(a) in nt for a in anchors)


def clean_notes():
    with open("notes_data.json", "r", encoding="utf-8") as f:
        notes = json.load(f)
    with open("anime_list.json", "r", encoding="utf-8") as f:
        anime_list = json.load(f)

    anime_titles = {str(a.get("title") or "").strip() for a in anime_list}
    anime_titles.discard("")

    cleaned_notes = [n for n in notes if is_relevant(n, anime_titles)]

    # URL重複を除去
    deduped = []
    seen = set()
    for note in cleaned_notes:
        key = note.get("url")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(note)

    with open("notes_data.json", "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    print(f"✨ クリーニング完了！ {len(notes)} -> {len(deduped)}件")

if __name__ == "__main__":
    clean_notes()
