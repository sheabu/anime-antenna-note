let allNotes = [];

async function loadNotes() {
    try {
        const response = await fetch('notes_data.json');
        allNotes = await response.json();
        
        const animeTitles = [...new Set(allNotes.map(n => n.anime_title))].filter(Boolean).sort();
        const filterSelect = document.getElementById('anime-filter');
        filterSelect.innerHTML = '<option value="">すべての作品</option>';
        animeTitles.forEach(title => {
            const opt = document.createElement('option');
            opt.value = title;
            opt.textContent = title;
            filterSelect.appendChild(opt);
        });

        displayNotes();
    } catch (error) {
        console.error("Error:", error);
    }
}

function displayNotes() {
    const listContainer = document.getElementById('note-list');
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const selectedAnime = document.getElementById('anime-filter').value;
    const sortOrder = document.getElementById('sort-order').value;

    let filtered = allNotes.filter(n => {
        const title = (n.note_title || "").toLowerCase();
        const anime = (n.anime_title || "").toLowerCase();
        return (title.includes(searchTerm) || anime.includes(searchTerm)) && 
               (!selectedAnime || n.anime_title === selectedAnime);
    });

    if (sortOrder === 'likes') {
        filtered.sort((a, b) => (b.like_count || 0) - (a.like_count || 0));
    } else {
        filtered.reverse();
    }

    document.getElementById('result-count').textContent = `${filtered.length}件`;

    listContainer.innerHTML = filtered.map(n => {
        // エラータイトルの書き換え
        let displayTitle = n.note_title || "記事タイトルを取得中...";
        if (displayTitle.includes("403 ERROR") || displayTitle.includes("取得失敗")) {
            displayTitle = "（読み込み中...）noteで詳細を確認";
        }

        // ダミー画像生成サービスのURLを利用して、「No Image」を少しオシャレに
        const dummyImg = `https://placehold.jp/24/3d5afe/ffffff/200x120.png?text=${encodeURIComponent(n.anime_title || 'Anime')}`;
        const imgSrc = (n.thumbnail && !n.thumbnail.includes("error")) ? n.thumbnail : dummyImg;

        return `
        <a href="${n.url}" target="_blank" class="note-card">
            <img src="${imgSrc}" class="note-card-img" alt="thumbnail">
            <div class="note-card-content">
                <div class="note-card-title">${displayTitle}</div>
                <div class="note-card-meta">
                    <span class="badge bg-primary">${n.anime_title || '作品名不明'}</span>
                    <span class="badge-likes">❤️ ${n.like_count || 0}</span>
                </div>
            </div>
        </a>
    `}).join('');
}

document.getElementById('search-input').addEventListener('input', displayNotes);
document.getElementById('anime-filter').addEventListener('change', displayNotes);
document.getElementById('sort-order').addEventListener('change', displayNotes);

window.onload = loadNotes;
