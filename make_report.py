import json

def generate_note_draft():
    with open('notes_data.json', 'r', encoding='utf-8') as f:
        notes = json.load(f)
    
    # スキ数が多く、かつタイトルが正しく取れているものを抽出
    valid_notes = [n for n in notes if n.get('note_title') and n['note_title'] != "取得失敗"]
    sorted_notes = sorted(valid_notes, key=lambda x: x.get('like_count', 0), reverse=True)
    
    print("\n📝 --- note投稿用コピー＆ペースト素材 ---\n")
    print("今週の人気アニメnoteまとめランキング！\n")
    print("話題の作品の感想記事をスキ数順にピックアップしました。\n")
    
    for i, note in enumerate(sorted_notes[:10]):
        title = note['note_title']
        url = note['url']
        likes = note['like_count']
        anime = note.get('anime_title', '注目作品')
        
        print(f"【第{i+1}位】{title}")
        print(f"作品：{anime} / ❤️ {likes}スキ")
        print(f"{url}\n")

if __name__ == "__main__":
    generate_note_draft()
