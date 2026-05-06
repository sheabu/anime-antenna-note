import json
import re

from article_filters import load_filter_config, title_matches_anime


def normalize_text(text):
    return re.sub(r"[\s　・!！?？:：()（）「」『』【】\-\u3000]", "", str(text or "")).lower()


def is_relevant(note, anime_titles, filter_cfg=None):
    anime_title = str(note.get("anime_title") or "").strip()
    note_title = str(note.get("note_title") or note.get("title") or "").strip()
    url = str(note.get("url") or "").strip()

    if anime_title not in anime_titles:
        return False
    if not url.startswith("https://note.com/"):
        return False
    if not note_title or normalize_text(note_title) in {"403error", "notearticle"}:
        return False
    if "403" in note_title:
        return False

    return title_matches_anime(note_title, anime_title, filter_cfg)


def clean_notes():
    with open("notes_data.json", "r", encoding="utf-8") as f:
        notes = json.load(f)
    with open("anime_list.json", "r", encoding="utf-8") as f:
        anime_list = json.load(f)

    anime_titles = {str(a.get("title") or "").strip() for a in anime_list}
    anime_titles.discard("")

    filter_cfg = load_filter_config()

    cleaned_notes = [n for n in notes if is_relevant(n, anime_titles, filter_cfg)]

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
