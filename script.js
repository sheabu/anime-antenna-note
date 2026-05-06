let allNotes = [];

// 作品名に基づいてランダムな色を生成する関数
const getBadgeColor = (str) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const h = hash % 360;
    return `hsl(${h}, 70%, 40%)`;
};

async function loadNotes() {
    try {
        const response = await fetch('notes_data.json');
        allNotes = await response.json();
        
        const animeTitles = [...new Set(allNotes.map(n => n.anime_title))].filter(Boolean).sort();
        const filterSelect = document.getElementById('anime-filter');
        animeTitles.forEach(title => {
            const opt = document.createElement('option');
            opt.value = title;
            opt.textContent = title;
            filterSelect.appendChild(opt);
        });

        displayNotes();
    } catch (error) {
        console.error("データの読み込みに失敗しました:", error);
    }
}

function displayNotes() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const selectedAnime = document.getElementById('anime-filter').value;
    const sortOrder = document.getElementById('sort-order').value;
    const listContainer = document.getElementById('note-list');

    let filtered = allNotes.filter(n => {
        const title = (n.note_title || "").toLowerCase();
        const anime = (n.anime_title || "").toLowerCase();
        const matchesSearch = title.includes(searchTerm) || anime.includes(searchTerm);
        const matchesAnime = !selectedAnime || n.anime_title === selectedAnime;
        return matchesSearch && matchesAnime;
    });

    if (sortOrder === 'likes') {
        filtered.sort((a, b) => (b.like_count || 0) - (a.like_count || 0));
    } else {
        filtered.reverse();
    }

    document.getElementById('result-count').textContent = `${filtered.length}件`;

    listContainer.innerHTML = filtered.map(n => {
        const animeTitle = n.anime_title || '作品名不明';
        const badgeColor = getBadgeColor(animeTitle);
        return `
        <a href="${n.url}" target="_blank" class="note-card">
            <img src="${n.thumbnail || 'https://placehold.jp/24/cccccc/ffffff/200x120.png?text=No+Image'}" class="note-card-img" alt="thumbnail">
            <div class="note-card-content">
                <div class="note-card-title">${n.note_title || '記事タイトルを取得中...'}</div>
                <div class="note-card-meta">
                    <span class="badge border" style="background-color: ${badgeColor}; color: white;">${animeTitle}</span>
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
