html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>あにnoteアンテナ</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header style="background:#333; color:#fff; padding:10px 0; text-align:center;">
        <h1>あにnoteアンテナ</h1>
    </header>
    
    <div class="container">
        <div id="note-list">
            <p>読み込み中...</p>
        </div>

        <div class="sidebar">
            <div style="background:#000; color:#fff; padding:10px; border-radius:8px 8px 0 0; font-weight:bold;">📢 公式最新情報</div>
            <div class="official-ticker-container">
                <div class="official-ticker-content">
                    <a href="#">🎬 進撃の巨人 公式X</a>
                    <a href="#">⚔️ 鬼滅の刃 公式X</a>
                    <a href="#">🧿 呪術廻戦 公式X</a>
                    <a href="#">🥜 SPY×FAMILY 公式X</a>
                    <a href="#">🌟 推しの子 公式X</a>
                    <a href="#">🎬 進撃の巨人 公式X</a>
                    <a href="#">⚔️ 鬼滅の刃 公式X</a>
                    <a href="#">🧿 呪術廻戦 公式X</a>
                    <a href="#">🥜 SPY×FAMILY 公式X</a>
                </div>
            </div>
        </div>
    </div>
    <script src="script.js"></script>
</body>
</html>
"""
with open('index.html', 'w') as f:
    f.write(html_content)
