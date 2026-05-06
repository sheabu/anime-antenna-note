let notes = [];

async function init() {
    const listEl = document.getElementById('note-list');
    try {
        // 現在時刻を付けてキャッシュを強制回避
        const res = await fetch('./notes_data.json?nocache=' + Date.now());
        if (!res.ok) throw new Error('Data file not found');
        
        notes = await res.json();
        
        // プルダウン生成
        const filter = document.getElementById('work-filter');
        const works = [...new Set(notes.map(n => n.work))].filter(Boolean).sort();
        works.forEach(w => {
            const opt = document.createElement('option');
            opt.value = w; opt.textContent = w;
            filter.appendChild(opt);
        });

        // 全イベント登録
        document.getElementById('work-filter').addEventListener('change', update);
        document.getElementById('sort-order').addEventListener('change', update);
        document.getElementById('search-input').addEventListener('input', update);

        update();
    } catch (e) {
        listEl.innerHTML = `<div style="padding:20px; background:#fff; border-radius:10px;">
            <p>⚠️ データの読み込みに失敗しました</p>
            <small style="color:#888;">原因: ${e.message}<br>notes_data.jsonがリポジトリ直下にあるか確認してください</small>
        </div>`;
    }
}

function update() {
    const work = document.getElementById('work-filter').value;
    const sort = document.getElementById('sort-order').value;
    const search = document.getElementById('search-input').value.toLowerCase();

    let filtered = notes.filter(n => 
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
    list.innerHTML = data.map(n => `
        <a href="${n.url}" target="_blank" class="note-card">
            <img src="${n.image || 'https://via.placeholder.com/120x68?text=No+Image'}">
            <div class="card-info">
                <span style="font-size:10px; color:#ff4e00; font-weight:bold;">${n.work}</span>
                <h3 style="margin:4px 0; font-size:15px;">${n.title}</h3>
                <div style="font-size:12px; color:#999;">❤️ ${n.likes || 0}</div>
            </div>
        </a>
    `).join('');
}

// DOMの読み込みが終わってから実行
window.addEventListener('DOMContentLoaded', init);
