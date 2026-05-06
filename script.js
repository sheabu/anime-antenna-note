let notesData = [];
const likesStoreKey = 'anime-antenna-liked-notes';
let likedNotes = {};

function loadLikes() {
    try {
        const raw = localStorage.getItem(likesStoreKey);
        likedNotes = raw ? JSON.parse(raw) : {};
    } catch (_) {
        likedNotes = {};
    }
}

function saveLikes() {
    localStorage.setItem(likesStoreKey, JSON.stringify(likedNotes));
}

function noteKey(note) {
    if (note.url && note.url !== '#') return note.url;
    return `${note.work}::${note.title}`;
}

function normalizeNote(note) {
    const safeUrl = typeof note.url === 'string' && /^https?:\/\//.test(note.url) ? note.url : '#';
    const displayTitle = note.title ?? note.note_title ?? '（無題）';
    const displayWork = note.work ?? note.anime_title ?? '未分類';
    const baseLikes = Number(note.likes ?? note.like_count ?? 0) || 0;

    return {
        work: displayWork,
        title: displayTitle,
        likes: baseLikes,
        date: note.date ?? note.posted_at ?? note.updated_at ?? '',
        image: note.image ?? note.thumbnail ?? '',
        url: safeUrl
    };
}

async function startApp() {
    try {
        // キャッシュを破壊して強制的に最新のJSONを読み込む
        const res = await fetch('./notes_data.json?v=' + Date.now());
        if (!res.ok) throw new Error('File not found');
        const rawNotes = await res.json();
        notesData = rawNotes.map(normalizeNote);
        loadLikes();
        notesData = notesData.map(n => {
            const key = noteKey(n);
            const delta = Number(likedNotes[key] || 0);
            return { ...n, likes: n.likes + delta };
        });
        
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
        document.getElementById('note-list').addEventListener('click', onLikeClick);

        render();
    } catch (e) {
        document.getElementById('note-list').innerHTML = `
            <div style="background:white; padding:20px; border-radius:12px; border:1px solid #ff4e00;">
                <h3>⚠️ 起動エラー</h3>
                <p>ブラウザで <b>Cmd + Shift + R</b> を押して再読み込みしてください。</p>
            </div>`;
    }
}

function onLikeClick(event) {
    const button = event.target.closest('.like-button');
    if (!button) return;

    const index = Number(button.dataset.noteIndex);
    if (!Number.isInteger(index) || !notesData[index]) return;

    const note = notesData[index];
    const key = noteKey(note);
    likedNotes[key] = Number(likedNotes[key] || 0) + 1;
    note.likes = Number(note.likes || 0) + 1;
    saveLikes();
    render();
}

function render() {
    const work = document.getElementById('work-filter').value;
    const sort = document.getElementById('sort-order').value;
    const search = document.getElementById('search-input').value.toLowerCase();

    let filtered = notesData
        .map((note, idx) => ({ note, idx }))
        .filter(({ note }) =>
            (work === 'all' || note.work === work) &&
            (note.title || '').toLowerCase().includes(search)
        );

    filtered.sort((a, b) => sort === 'new' ?
        new Date(b.note.date) - new Date(a.note.date) : (b.note.likes || 0) - (a.note.likes || 0)
    );

    document.getElementById('note-list').innerHTML = filtered.map(({ note, idx }) => {
        return `
        <div class="note-card">
            <img src="${note.image || 'https://via.placeholder.com/140x80?text=Anime'}" alt="">
            <div class="note-main">
                <span style="color:#ff4e00; font-size:11px; font-weight:bold;">${note.work}</span>
                <h3 style="margin:5px 0; font-size:16px;">
                    <a href="${note.url}" target="_blank" rel="noopener noreferrer" class="note-link">${note.title}</a>
                </h3>
                <div class="note-actions">
                    <div style="color:#999; font-size:13px;">❤️ ${note.likes || 0}スキ</div>
                    <button class="like-button" data-note-index="${idx}" type="button">スキする</button>
                </div>
            </div>
        </div>
    `;
    }).join('');
}

window.onload = startApp;
