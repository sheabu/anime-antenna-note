import json

def clean_notes():
    with open('notes_data.json', 'r', encoding='utf-8') as f:
        notes = json.load(f)
    
    # 除外したいワードを追加
    exclude_keywords = ["電車", "YOSOHACHI", "採用", "募集", "株式会社", "投資", "副業"]
    
    cleaned_notes = [
        n for n in notes 
        if not any(k in n.get('note_title', '') for k in exclude_keywords)
    ]
    
    with open('notes_data.json', 'w', encoding='utf-8') as f:
        json.dump(cleaned_notes, f, ensure_ascii=False, indent=2)
    
    print(f"✨ クリーニング完了！ {len(notes)} -> {len(cleaned_notes)}件")

if __name__ == "__main__":
    clean_notes()
