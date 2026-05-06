let allNotes = [];

async function loadNotes() {
    try {
        const response = await fetch('notes_data.json');
        if (!response.ok) throw new Error('Network response was not ok');
        allNotes = await response.json();
        
        console.log("Loaded notes:", allNotes.length);

        const animeTitles = [...new Set(allNotes.map(n => n.anime_title))].filter(Boolean).sort();
        const filterSelect = document.getElementById('anime-filter');
        filterSelect.innerHTML = '<option value="">すべての作品</option>'; // 初期化
        animeTitles.forEach(title => {
            const opt = document.createElement('option');
            opt.value = title;
            opt.textContent = title;
            filterSelect.appendChild(opt);
        });

        displayNotes();
    } catch (error) {
        console.error("データの読み込みに失敗しました:", error);
        document.getElementById('note-list').innerHTML = '<p class="text-center">データの読み込みに失敗しました。再読み込みしてください。</p>';
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

    if (filtered.length === 0) {
        listContainer.innerHTML = '<p class="text-center p-5">該当する記事が見つかりません。</p>';
        return;
    }

    listContainer.innerHTML = filtered.map(n => `
        <a href="${n.url}" target="_blank" class="note-card">
            <img src="${n.thumbnail || 'https://placehold.jp/24/cccccc/ffffff/200x120.png?text=No+Image'}" class="note-card-img" onerror="this.src='https://placehold.jp/200x120.png?text=No+Image'">
            <div class="note-card-content">
                <div class="note-card-title">${n.note_title || '記事タイトルを取得中...'}</div>
                <div class="note-card-meta">
                    <span class="badge bg-primary">${n.anime_title || '作品名不明'}</span>
                    <span class="badge-likes">❤️ ${n.like_count || 0}</span>
                </div>
            </div>
        </a>
    `).join('');
}

document.getElementById('search-input').addEventListener('input', displayNotes);
document.getElementById('anime-filter').addEventListener('change', displayNotes);
document.getElementById('sort-order').addEventListener('change', displayNotes);

window.onload = loadNotes;
