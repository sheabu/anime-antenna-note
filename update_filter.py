import re

with open('script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# フィルタキーワードを最新・厳格なものに置換
keywords = '["アニメ", "感想", "考察", "マンガ", "レビュー", "推しの子", "進撃", "呪術", "鬼滅", "スパイファミリー"]'
content = re.sub(r'const animeKeywords = \[.*?\];', f'const animeKeywords = {keywords};', content)

with open('script.js', 'w', encoding='utf-8') as f:
    f.write(content)
print("✅ キーワードフィルタを修正しました")
