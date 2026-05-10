let notesData = [];
const RANKING_REFRESH_MS = 5 * 60 * 1000;
// 同一リポジトリ内SVG（外部プレースホルダはブロックされやすく、onerror で無限ループしやすい）
const DEFAULT_THUMBNAIL = './note-placeholder.svg';
const MOBILE_MAX_WIDTH = 900;
const MOBILE_PER_PAGE = 10;
let currentPage = 1;

function isGenericTitle(value) {
    return /^\s*note\s*article\s*$/i.test(String(value || ''));
}

function normalizeNote(note) {
    const safeUrl = typeof note.url === 'string' && /^https?:\/\//.test(note.url) ? note.url : '#';
    const noteTitle = String(note.note_title || '').trim();
    const legacyTitle = String(note.title || '').trim();
    const displayTitle = (!isGenericTitle(noteTitle) && noteTitle)
        || (!isGenericTitle(legacyTitle) && legacyTitle)
        || `${note.anime_title ?? note.work ?? 'アニメ'} 関連note`;
    const displayWork = note.work ?? note.anime_title ?? '未分類';
    const baseLikes = Number(note.likes ?? note.like_count ?? 0) || 0;

    let candidateImage = String(note.image ?? note.thumbnail ?? '').trim();
    if (candidateImage.startsWith('//')) candidateImage = 'https:' + candidateImage;
    const isRelativeAsset =
        candidateImage.startsWith('./') ||
        candidateImage.startsWith('/') ||
        candidateImage.endsWith('.svg');
    const isHttp = /^https?:\/\//i.test(candidateImage);
    const isDeadPlaceholder =
        /via\.placeholder\.com|placehold\.it|placekitten|dummyimage\.com/i.test(candidateImage);
    const safeImage =
        (isHttp && !isDeadPlaceholder) || isRelativeAsset ? candidateImage : DEFAULT_THUMBNAIL;

    return {
        work: displayWork,
        title: displayTitle,
        likes: baseLikes,
        date: note.date ?? note.posted_at ?? note.updated_at ?? '',
        image: safeImage,
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
        
        // フィルターのプルダウンを生成
        const filter = document.getElementById('work-filter');
        const works = [...new Set(notesData.map(n => n.work))].filter(Boolean).sort();
        works.forEach(w => {
            const opt = document.createElement('option');
            opt.value = w; opt.textContent = w;
            filter.appendChild(opt);
        });

        // 操作があったら即座に再描画
        document.getElementById('work-filter').onchange = () => {
            currentPage = 1;
            render();
        };
        document.getElementById('sort-order').onchange = () => {
            currentPage = 1;
            render();
        };
        document.getElementById('search-input').oninput = () => {
            currentPage = 1;
            render();
        };
        window.addEventListener('resize', render);

        render();
        initializeXWidgets();
        loadHashtagRanking();
        setInterval(loadHashtagRanking, RANKING_REFRESH_MS);
    } catch (e) {
        document.getElementById('note-list').innerHTML = `
            <div style="background:white; padding:20px; border-radius:12px; border:1px solid #ff4e00;">
                <h3>⚠️ 起動エラー</h3>
                <p>ブラウザで <b>Cmd + Shift + R</b> を押して再読み込みしてください。</p>
            </div>`;
    }
}

function initializeXWidgets() {
    const tryLoad = () => {
        if (window.twttr && window.twttr.widgets && window.twttr.widgets.load) {
            window.twttr.widgets.load();
        }
    };

    tryLoad();
    window.setTimeout(tryLoad, 1200);
    window.setTimeout(showXFallbackIfNeeded, 3500);
}

function showXFallbackIfNeeded() {
    const fallback = document.getElementById('x-widget-fallback');
    const widgetWindow = document.querySelector('.x-ad-window');
    if (!fallback || !widgetWindow) return;
    const hasIframe = widgetWindow.querySelector('iframe');
    if (!hasIframe) fallback.classList.remove('hidden');
}

async function loadHashtagRanking() {
    const listEl = document.getElementById('x-rank-list');
    const trackEl = document.getElementById('x-rank-track');
    if (!listEl || !trackEl) return;

    try {
        const res = await fetch(`./x_ranking.json?v=${Date.now()}`);
        if (!res.ok) throw new Error('ranking not found');
        const payload = await res.json();
        const rankings = Array.isArray(payload.rankings) ? payload.rankings.slice(0, 8) : [];

        if (!rankings.length) throw new Error('ranking empty');
        listEl.innerHTML = rankings.map((item, i) => `
            <li>
                <a class="rank-tag" href="https://twitter.com/hashtag/${encodeURIComponent((item.tag || '').replace('#', ''))}?f=live" target="_blank" rel="noopener noreferrer">
                    ${i + 1}. ${item.tag}
                </a>
                <span class="rank-score">${item.score}</span>
            </li>
        `).join('') + `<div class="x-rank-meta">更新: ${payload.updated_at || 'unknown'}</div>`;

        trackEl.innerHTML = rankings.map((item, i) => `
            <a href="https://twitter.com/hashtag/${encodeURIComponent((item.tag || '').replace('#', ''))}?f=live" target="_blank" rel="noopener noreferrer">
                ${i + 1}位 ${item.tag}
            </a>
        `).join('');
    } catch (_) {
        listEl.innerHTML = `
            <li>
                <a class="rank-tag" href="https://twitter.com/hashtag/%E3%82%A2%E3%83%8B%E3%83%A1?f=live" target="_blank" rel="noopener noreferrer">
                    1. #アニメ
                </a>
                <span class="rank-score">LIVE</span>
            </li>
        `;
        trackEl.innerHTML = '<a href="https://twitter.com/hashtag/%E3%82%A2%E3%83%8B%E3%83%A1?f=live" target="_blank" rel="noopener noreferrer">#アニメ ライブ投稿</a>';
    }
}

function render() {
    const work = document.getElementById('work-filter').value;
    const sort = document.getElementById('sort-order').value;
    const search = document.getElementById('search-input').value.toLowerCase();

    let filtered = notesData
        .filter((note) =>
            (work === 'all' || note.work === work) &&
            (note.title || '').toLowerCase().includes(search)
        );

    filtered.sort((a, b) => sort === 'new' ?
        new Date(b.date) - new Date(a.date) : (b.likes || 0) - (a.likes || 0)
    );

    const isMobile = window.innerWidth <= MOBILE_MAX_WIDTH;
    const perPage = isMobile ? MOBILE_PER_PAGE : filtered.length || 1;
    const totalPages = Math.max(1, Math.ceil(filtered.length / perPage));
    currentPage = Math.min(currentPage, totalPages);
    const start = (currentPage - 1) * perPage;
    const pageItems = filtered.slice(start, start + perPage);

    document.getElementById('note-list').innerHTML = pageItems.map((note) => {
        return `
        <div class="note-card">
            <img src="${note.image}" alt="" loading="lazy" decoding="async" onerror="this.onerror=null;this.src='${DEFAULT_THUMBNAIL}'">
            <div class="note-main">
                <span style="color:#ff4e00; font-size:11px; font-weight:bold;">${note.work}</span>
                <h3 style="margin:5px 0; font-size:16px;">
                    <a href="${note.url}" target="_blank" rel="noopener noreferrer" class="note-link">${note.title}</a>
                </h3>
                <div class="note-actions">
                    <div style="color:#999; font-size:13px;">❤️ ${note.likes || 0}スキ</div>
                </div>
            </div>
        </div>
    `;
    }).join('');

    renderPagination(isMobile, totalPages);
}

function renderPagination(isMobile, totalPages) {
    const pagination = document.getElementById('pagination');
    if (!pagination) return;

    if (!isMobile || totalPages <= 1) {
        pagination.classList.add('hidden');
        pagination.innerHTML = '';
        return;
    }

    pagination.classList.remove('hidden');
    pagination.innerHTML = `
        <button id="page-prev" ${currentPage <= 1 ? 'disabled' : ''}>前へ</button>
        <span class="page-indicator">${currentPage} / ${totalPages}</span>
        <button id="page-next" ${currentPage >= totalPages ? 'disabled' : ''}>次へ</button>
    `;

    const prev = document.getElementById('page-prev');
    const next = document.getElementById('page-next');
    if (prev) {
        prev.onclick = () => {
            if (currentPage > 1) {
                currentPage -= 1;
                render();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        };
    }
    if (next) {
        next.onclick = () => {
            if (currentPage < totalPages) {
                currentPage += 1;
                render();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        };
    }
}

window.onload = startApp;
