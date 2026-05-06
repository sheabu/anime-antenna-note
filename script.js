let notes = [];

async function loadData() {
    try {
        const res = await fetch('notes_data.json');
        if (!res.ok) throw new Error('File not found');
        notes = await res.json();
        
        // 作品リストを生成
        const filter = document.getElementById('work-filter');
        const works = [...new Set(notes.map(n => n.work))].sort();
        works.forEach(w => {
            const opt = document.createElement('option');
            opt.value = w; opt.textContent = w;
            filter.appendChild(opt);
        });

        render();
    } catch (e) {
        document.getElementById('note-list').innerHTML = "記事データの読み込みに失敗しました。JSONファイルが存在するか確認してください。";
    }
}

function render() {
    const work = document.getElementById('work-filter').value;
    const search = document.getElementById('search-input').value.toLowerCase();
    
    const filtered = notes.filter(n => 
        (work === 'all' || n.work === work) && n.title.toLowerCase().includes(search)
    );

    document.getElementById('note-list').innerHTML = filtered.map(n => `
        <a href="${n.url}" target="_blank" class="note-card">
            <img src="${n.image || ''}">
            <div>
                <div style="font-size:10px; color:#ff4e00;">${n.work}</div>
                <h3 style="margin:5px 0; font-size:15px;">${n.title}</h3>
                <div style="font-size:12px; color:#888;">❤️ ${n.likes || 0}</div>
            </div>
        </a>
    `).join('');
}

document.getElementById('work-filter').addEventListener('change', render);
document.getElementById('search-input').addEventListener('input', render);

loadData();
