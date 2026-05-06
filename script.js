let allNotes = [];

async function loadNotes() {
    try {
        const response = await fetch('notes_data.json');
        allNotes = await response.json();
        displayNotes();
    } catch (error) { console.error("Error:", error); }
}

function displayNotes() {
    const listContainer = document.getElementById('note-list');
    
    // フィルタリング条件の定義
    const filtered = allNotes.filter(n => {
        const title = n.note_title || "";
        const tags = n.tags || [];
        
        // 1. 除外したいタグやタイトルの指定
        const isBlacklisted = tags.includes("うそ探偵トマント") || title.includes("YOSOHACHI") || title.includes("電車");
        
        // 2. アニメに関係するタグが1つでもあるか（タグ基準の抽出）
        const animeKeywords = ["アニメ", "感想", "考察", "マンガ", "レビュー"];
        const hasAnimeTag = tags.some(tag => animeKeywords.some(key => tag.includes(key)));

        return !isBlacklisted && (hasAnimeTag || title.includes("アニメ"));
    });

    listContainer.innerHTML = filtered.map(n => {
        const dummyImg = `https://placehold.jp/24/3d5afe/ffffff/200x120.png?text=${encodeURIComponent(n.anime_title || 'Anime')}`;
        const imgSrc = (n.thumbnail && !n.thumbnail.includes("error")) ? n.thumbnail : dummyImg;

        return `
        <a href="${n.url}" target="_blank" class="note-card mb-3 d-flex align-items-center text-decoration-none text-dark p-2 border rounded bg-white shadow-sm">
            <img src="${imgSrc}" style="width:120px; height:80px; object-fit:cover; border-radius:4px;" class="me-3">
            <div>
                <h6 class="mb-1 fw-bold">${n.note_title || "タイトル取得中..."}</h6>
                <span class="badge bg-primary">${n.anime_title || '作品名不明'}</span>
                <span class="ms-2 text-danger">❤️ ${n.like_count || 0}</span>
            </div>
        </a>
    `}).join('');
}

window.onload = loadNotes;
