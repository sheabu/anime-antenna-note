import json

def clean_notes():
    with open('notes_data.json', 'r', encoding='utf-8') as f:
        notes = json.load(f)
    
    # 削除対象のキーワード（タイトルだけでなくURLもチェック）
    exclude_list = ["recruit", "company", "shinsotsu", "job-draft", "wantedly"]
    
    original_count = len(notes)
    # URLまたはタイトルに上記が含まれるものを除外
    cleaned_notes = [
        n for n in notes 
        if not any(k in n.get('url', '').lower() for k in exclude_list)
        and not any(k in n.get('note_title', '') for k in ["採用", "募集", "株式会社"])
    ]
    
    with open('notes_data.json', 'w', encoding='utf-8') as f:
        json.dump(cleaned_notes, f, ensure_ascii=False, indent=2)
    
    print(f"🧹 強力クリーニング完了！")
    print(f"元の件数: {original_count} -> 削除後の件数: {len(cleaned_notes)}")
    print(f"削除した件数: {original_count - len(cleaned_notes)}")

if __name__ == "__main__":
    clean_notes()
