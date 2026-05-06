import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# サイドバーエリアを特定して置換
new_sidebar = """
<div class="col-md-4">
    <div class="card mb-4 border-0 shadow-sm">
        <div class="card-header bg-dark text-white fw-bold">📢 公式SNS最新情報</div>
        <div class="official-ticker-container">
            <div class="official-ticker-content">
                <a href="https://x.com/anime_shingeki" target="_blank">🎬 進撃の巨人 公式X</a>
                <a href="https://x.com/kimetsu_off" target="_blank">⚔️ 鬼滅の刃 公式X</a>
                <a href="https://x.com/anime_jujutsu" target="_blank">🧿 呪術廻戦 公式X</a>
                <a href="https://x.com/spyfamily_anime" target="_blank"> Peanut SPY×FAMILY 公式X</a>
                <a href="https://x.com/oshinoko_anime" target="_blank">🌟 推しの子 公式X</a>
                <a href="https://x.com/anime_shingeki" target="_blank">🎬 進撃の巨人 公式X</a>
            </div>
        </div>
    </div>
    <div class="card p-3 bg-light border-0 shadow-sm">
        <h5>このサイトについて</h5>
        <p class="small text-muted">noteのアニメタグから記事を厳選。公式情報もリアルタイムでチェックできます。</p>
    </div>
</div>
"""

# コメントタグの間をまるごと入れ替え
html = re.sub(r'.*?', new_sidebar, html, flags=re.DOTALL)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("✅ サイドバーを強制的に更新しました")
