import re

file_path = 'script.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 除外したいワードのリスト
exclude_words = ["うそ探偵", "YOSOHACHI", "電車", "募集", "副業"]

# フィルタリングロジックを挿入
filter_logic = f"""
    let filtered = allNotes.filter(n => {{
        const title = (n.note_title || "").toLowerCase();
        const anime = (n.anime_title || "").toLowerCase();
        const tags = (n.tags || []);
        
        // 除外ワードチェック
        const excludeWords = {exclude_words};
        const isIrrelevant = excludeWords.some(word => 
            title.includes(word.toLowerCase()) || 
            tags.some(tag => tag.includes(word))
        );

        return !isIrrelevant && 
               (title.includes(searchTerm) || anime.includes(searchTerm)) && 
               (!selectedAnime || n.anime_title === selectedAnime);
    }});
"""

# 既存の let filtered = ... の部分を丸ごと差し替え
content = re.sub(r'let filtered = allNotes\.filter\(.*?\);', filter_logic, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("✅ script.js のフィルタリング機能を更新しました")
