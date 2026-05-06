let allNotes = [];

async function init() {
    try {
        const response = await fetch('notes_data.json');
        allNotes = await response.json();
        
        // 作品プルダウンの生成
        const filter = document.getElementById('work-filter');
        const works = [...new Set(allNotes.map(n => n.work))].filter(Boolean);
        works.sort().forEach(work => {
            const opt = document.createElement('option');
            opt.value = work;
            opt.textContent = work;
            filter.appendChild(opt);
        });

        updateList(); // 初期表示
    } catch (e) {
        console.error("データの読み込みエラー", e);
    }
}

function updateList() {
    const work = document.getElementById('work-filter').value;
    const sort = document.getElementById('sort-order').value;
    const search = document.getElementById('search-input').value.toLowerCase();

    // フィルタリング（死んでいました）
    let filtered = allNotes.filter(n => {
        const matchWork = (work === 'all' || n.work === work);
        const matchSearch = n.title.toLowerCase().includes(search);
        return matchWork && matchSearch;
    });

    // ソート（人気順と最新順）
    if (sort === 'new') {
        filtered.sort((a, b) => new Date(b.date) - new Date(a.date));
    } else {
        filtered.sort((a, b) => (b.likes || 0) - (a.likes || 0));
    }

    render(filtered);
}

function render(data) {
    const list = document.getElementById('note-list');
    const count = document.getElementById('result-count');
    list.innerHTML = '';
    count.textContent = `${data.length} articles found`;

    data.forEach(item => {
        const card = document.createElement('a');
        card.className = 'note-card';
        card.href = item.url;
        card.target = '_blank';
        card.innerHTML = `
            <img src="${item.image || 'no-image.png'}" alt="thumb">
            <div class="note-info">
                <div style="font-size:12px; color:#ff4e00; font-weight:bold;">${item.work}</div>
                <h3 style="margin:5px 0; font-size:16px;">${item.title}</h3>
                <div style="font-size:13px; color:#666;">❤️ ${item.likes || 0}likes</div>
            </div>
        `;
        list.appendChild(card);
    });
}

// イベントリスナーの登録（死んでいました）
document.getElementById('work-filter').addEventListener('change', updateList);
document.getElementById('sort-order').addEventListener('change', updateList);
document.getElementById('search-input').addEventListener('input', updateList);

init();
