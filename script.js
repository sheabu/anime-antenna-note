let notesData = [];

async function startApp() {
    try {
        // キャッシュを破壊して強制的に最新のJSONを読み込む
        const res = await fetch('./notes_data.json?v=' + Date.now());
        if (!res.ok) throw new Error('File not found');
        notesData = await res.json();
        
        // フィルターのプルダウンを生成
        const filter = document.getElementById('work-filter');
        const works = [...new Set(notesData.map(n => n.work))].filter(Boolean).sort();
        works.forEach(w => {
            const opt = document.createElement('option');
            opt.value = w; opt.textContent = w;
            filter.appendChild(opt);
        });

        // 操作があったら即座に再描画
        document.getElementById('work-filter').onchange = render;
        document.getElementById('sort-order').onchange = render;
        document.getElementById('search-input').oninput = render;

        render();
    } catch (e) {
        document.getElementById('note-list').innerHTML = `
            <div style="background:white; padding:20px; border-radius:12px; border:1px solid #ff4e00;">
                <h3>⚠️ 起動エラー</h3>
                <p>ブラウザで <b>Cmd + Shift + R</b> を押して再読み込みしてください。</p>
            </div>`;
    }
}

function render() {
    const work = document.getElementById('work-filter').value;
    const sort = document.getElementById('sort-order').value;
    const search = document.getElementById('search-input').value.toLowerCase();

    let filtered = notesData.filter(n => 
        (work === 'all' || n.work === work) && n.title.toLowerCase().includes(search)
    );

    filtered.sort((a, b) => sort === 'new' ? 
        new Date(b.date) - new Date(a.date) : (b.likes || 0) - (a.likes || 0)
    );

    document.getElementById('note-list').innerHTML = filtered.map(n => `
        <a href="${n.url}" target="_blank" class="note-card">
            <img src="${n.image || 'https://via.placeholder.com/140x80?text=Anime'}" alt="">
            <div>
                <span style="color:#ff4e00; font-size:11px; font-weight:bold;">${n.work}</span>
                <h3 style="margin:5px 0; font-size:16px;">${n.title}</h3>
                <div style="color:#999; font-size:13px;">❤️ ${n.likes || 0}スキ</div>
            </div>
        </a>
    `).join('');
}

window.onload = startApp;
