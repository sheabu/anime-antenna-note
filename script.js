let allNotes = [];

async function init() {
    const listArea = document.getElementById('note-list');
    const countArea = document.getElementById('result-count');

    try {
        const response = await fetch('notes_data.json');
        if (!response.ok) throw new Error('Network error');
        allNotes = await response.json();
        
        // プルダウン生成
        const filter = document.getElementById('work-filter');
        const works = [...new Set(allNotes.map(n => n.work))].filter(Boolean).sort();
        works.forEach(work => {
            const opt = document.createElement('option');
            opt.value = work;
            opt.textContent = work;
            filter.appendChild(opt);
        });

        // イベント登録
        [filter, document.getElementById('sort-order')].forEach(el => el.addEventListener('change', update));
        document.getElementById('search-input').addEventListener('input', update);

        update();
    } catch (e) {
        countArea.textContent = "データの読み込みに失敗しました。";
        console.error(e);
    }
}

function update() {
    const work = document.getElementById('work-filter').value;
    const sort = document.getElementById('sort-order').value;
    const search = document.getElementById('search-input').value.toLowerCase();

    let filtered = allNotes.filter(n => 
        (work === 'all' || n.work === work) && n.title.toLowerCase().includes(search)
    );

    filtered.sort((a, b) => sort === 'new' ? 
        new Date(b.date) - new Date(a.date) : (b.likes || 0) - (a.likes || 0)
    );

    render(filtered);
}

function render(data) {
    const list = document.getElementById('note-list');
    document.getElementById('result-count').textContent = `${data.length} 件の記事を表示中`;
    list.innerHTML = data.map(item => `
        <a href="${item.url}" target="_blank" class="note-card">
            <img src="${item.image || 'no-image.png'}">
            <div class="info">
                <div style="font-size:11px; color:#ff4e00; font-weight:bold;">${item.work}</div>
                <h3 style="margin:5px 0; font-size:16px;">${item.title}</h3>
                <div style="font-size:12px; color:#888;">❤️ ${item.likes || 0} likes</div>
            </div>
        </a>
    `).join('');
}

init();
