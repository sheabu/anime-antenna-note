let allNotes = [];

// 1. データの読み込み
async function loadNotes() {
    try {
        const response = await fetch('notes_data.json');
        allNotes = await response.json();
        
        // 作品名プルダウンを自動生成
        populateWorkFilter();
        // 初期表示
        renderNotes(allNotes);
    } catch (err) {
        console.error("データの読み込みに失敗しました", err);
    }
}

// 2. 作品プルダウンの動的生成
function populateWorkFilter() {
    const filter = document.getElementById('work-filter');
    const works = [...new Set(allNotes.map(n => n.work))].filter(Boolean);
    
    works.forEach(work => {
        const option = document.createElement('option');
        option.value = work;
        option.textContent = work;
        filter.appendChild(option);
    });
}

// 3. 描画機能（リンクも正常化）
function renderNotes(notes) {
    const list = document.getElementById('note-list');
    const count = document.getElementById('article-count');
    list.innerHTML = '';
    count.textContent = `${notes.length} 件の記事が見つかりました`;

    notes.forEach(note => {
        const card = document.createElement('a');
        card.className = 'note-card';
        card.href = note.url;
        card.target = '_blank';
        card.innerHTML = `
            <img src="${note.image || 'default.png'}" alt="thumb">
            <div class="note-info">
                <h3>${note.title}</h3>
                <div class="meta">
                    <span class="work-tag">${note.work}</span>
                    <span class="likes">❤️ ${note.likes}</span>
                </div>
            </div>
        `;
        list.appendChild(card);
    });
}

// 4. フィルタリングとソート（ここが死んでいました）
function updateList() {
    const work = document.getElementById('work-filter').value;
    const sort = document.getElementById('sort-order').value;
    const search = document.getElementById('search-input').value.toLowerCase();

    let filtered = allNotes.filter(n => {
        const matchWork = (work === 'all' || n.work === work);
        const matchSearch = n.title.toLowerCase().includes(search);
        return matchWork && matchSearch;
    });

    if (sort === 'new') {
        filtered.sort((a, b) => new Date(b.date) - new Date(a.date));
    } else {
        filtered.sort((a, b) => b.likes - a.likes);
    }

    renderNotes(filtered);
}

// イベント登録
document.getElementById('work-filter').addEventListener('change', updateList);
document.getElementById('sort-order').addEventListener('change', updateList);
document.getElementById('search-input').addEventListener('input', updateList);

loadNotes();
