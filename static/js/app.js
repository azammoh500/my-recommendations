// Estate — frontend interactions
// ---------------------------------------------------------

// Date line in masthead
(function setToday() {
  const months = ['January','February','March','April','May','June',
                  'July','August','September','October','November','December'];
  const d = new Date();
  const el = document.getElementById('today');
  if (el) el.textContent = `${months[d.getMonth()]} ${d.getFullYear()}`;
})();

// Stagger card entrance
document.querySelectorAll('.grid .card').forEach((card, i) => {
  card.style.setProperty('--i', i + 1);
});

// ---------------------------------------------------------
// Audio preview (only one plays at a time)
// ---------------------------------------------------------
let currentAudio = null;
let currentButton = null;

function stopCurrent() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
  }
  if (currentButton) {
    currentButton.classList.remove('is-playing');
    const play = currentButton.querySelector('.play-icon');
    const pause = currentButton.querySelector('.pause-icon');
    if (play) play.hidden = false;
    if (pause) pause.hidden = true;
    currentButton = null;
  }
}

document.addEventListener('click', (e) => {
  const btn = e.target.closest('.card__play');
  if (!btn) return;
  e.preventDefault();
  const src = btn.dataset.src;
  if (!src) return;

  if (currentButton === btn) {
    stopCurrent();
    return;
  }

  stopCurrent();

  const audio = new Audio(src);
  audio.volume = 0.85;
  audio.play().catch(err => console.warn('Audio error:', err));
  audio.addEventListener('ended', stopCurrent);

  currentAudio = audio;
  currentButton = btn;
  btn.classList.add('is-playing');
  const play = btn.querySelector('.play-icon');
  const pause = btn.querySelector('.pause-icon');
  if (play) play.hidden = true;
  if (pause) pause.hidden = false;
});

// ---------------------------------------------------------
// Delete items
// ---------------------------------------------------------
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.card__delete');
  if (!btn) return;
  e.preventDefault();
  e.stopPropagation();

  const kind = btn.dataset.kind;
  const id = btn.dataset.id;
  if (!confirm('Remove this from the collection?')) return;

  const url = kind === 'movie' ? `/api/movies/${id}` : `/api/songs/${id}`;
  try {
    const res = await fetch(url, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed');
    const card = btn.closest('.card');
    if (card) {
      card.style.transition = 'opacity .3s, transform .3s';
      card.style.opacity = '0';
      card.style.transform = 'scale(0.92)';
      setTimeout(() => card.remove(), 300);
    }
  } catch (err) {
    alert('Could not remove. Please try again.');
  }
});

// ---------------------------------------------------------
// Modal
// ---------------------------------------------------------
const modal = document.getElementById('addModal');
const openBtn = document.getElementById('openAdd');
const tabs = modal.querySelectorAll('.tab');
const movieForm = document.getElementById('movieForm');
const songForm = document.getElementById('songForm');

function openModal() {
  modal.hidden = false;
  document.body.style.overflow = 'hidden';
}
function closeModal() {
  modal.hidden = true;
  document.body.style.overflow = '';
  // reset errors
  modal.querySelectorAll('[data-error]').forEach(p => {
    p.hidden = true;
    p.textContent = '';
  });
}

openBtn.addEventListener('click', openModal);
modal.querySelectorAll('[data-close]').forEach(el => {
  el.addEventListener('click', closeModal);
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !modal.hidden) closeModal();
});

tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('tab--active'));
    tab.classList.add('tab--active');
    const kind = tab.dataset.tab;
    movieForm.hidden = (kind !== 'movie');
    songForm.hidden = (kind !== 'song');
  });
});

// ---------------------------------------------------------
// Add movie
// ---------------------------------------------------------
movieForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const errEl = movieForm.querySelector('[data-error]');
  errEl.hidden = true;

  const fd = new FormData(movieForm);
  try {
    const res = await fetch('/api/movies', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Something went wrong');

    prependCard('movie', data.movie);
    movieForm.reset();
    closeModal();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.hidden = false;
  }
});

// ---------------------------------------------------------
// Add song
// ---------------------------------------------------------
songForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const errEl = songForm.querySelector('[data-error]');
  errEl.hidden = true;

  const fd = new FormData(songForm);
  try {
    const res = await fetch('/api/songs', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Something went wrong');

    prependCard('song', data.song);
    songForm.reset();
    closeModal();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.hidden = false;
  }
});

// ---------------------------------------------------------
// Card rendering (client-side)
// ---------------------------------------------------------
function esc(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function movieCardHTML(m) {
  const img = m.image_url
    ? `<img src="${esc(m.image_url)}" alt="${esc(m.title)}" loading="lazy"/>`
    : `<div class="card__placeholder"><span>${esc((m.title || '?')[0])}</span></div>`;
  const year = m.year ? `<span class="card__meta">${esc(m.year)}</span>` : '';
  const note = m.note ? `<p class="card__note">${esc(m.note)}</p>` : '';
  return `
    <article class="card card--movie" data-id="${m.id}">
      <div class="card__poster">
        ${img}
        <button type="button" class="card__delete" title="remove" data-kind="movie" data-id="${m.id}">×</button>
      </div>
      <div class="card__body">
        <h3 class="card__title">${esc(m.title)}</h3>
        ${year}
        ${note}
      </div>
    </article>`;
}

function songCardHTML(s) {
  const img = s.album_image
    ? `<img src="${esc(s.album_image)}" alt="${esc(s.title)}" loading="lazy"/>`
    : `<div class="card__placeholder card__placeholder--round"><span>♪</span></div>`;
  const play = s.preview_url
    ? `<button type="button" class="card__play" data-src="${esc(s.preview_url)}" aria-label="play preview">
         <span class="play-icon">▶</span>
         <span class="pause-icon" hidden>❚❚</span>
       </button>`
    : '';
  const note = s.note ? `<p class="card__note">${esc(s.note)}</p>` : '';
  return `
    <article class="card card--song" data-id="${s.id}">
      <div class="card__cover">
        ${img}
        ${play}
        <button type="button" class="card__delete" title="remove" data-kind="song" data-id="${s.id}">×</button>
      </div>
      <div class="card__body">
        <h3 class="card__title">${esc(s.title)}</h3>
        <span class="card__meta">${esc(s.artist)}</span>
        ${note}
      </div>
    </article>`;
}

function prependCard(kind, item) {
  const grid = document.getElementById(kind === 'movie' ? 'moviesGrid' : 'songsGrid');
  if (!grid) return;
  const html = kind === 'movie' ? movieCardHTML(item) : songCardHTML(item);
  const temp = document.createElement('div');
  temp.innerHTML = html.trim();
  const card = temp.firstChild;
  grid.prepend(card);
  // remove any "empty" note if present
  const emptyNote = grid.parentElement.querySelector('.empty');
  if (emptyNote) emptyNote.remove();
}

// ---------------------------------------------------------
// Search (Python backend, rendered here)
// ---------------------------------------------------------
const qInput = document.getElementById('q');
const resultsEl = document.getElementById('searchResults');
const gridEl = document.getElementById('searchGrid');
const countEl = document.getElementById('searchCount');
const clearBtn = document.getElementById('clearSearch');
const filters = document.querySelectorAll('.search__filters input');

let searchTimer = null;

function runSearch() {
  const q = qInput.value.trim();
  if (!q) {
    resultsEl.hidden = true;
    gridEl.innerHTML = '';
    return;
  }
  const kind = document.querySelector('.search__filters input:checked').value;

  fetch(`/api/search?q=${encodeURIComponent(q)}&kind=${kind}`)
    .then(r => r.json())
    .then(data => {
      resultsEl.hidden = false;
      countEl.textContent = data.count === 0
        ? 'no matches'
        : `${data.count} ${data.count === 1 ? 'match' : 'matches'} for "${q}"`;

      gridEl.innerHTML = data.results.map(r =>
        r.kind === 'movie' ? movieCardHTML(r.data) : songCardHTML(r.data)
      ).join('');
      gridEl.querySelectorAll('.card').forEach((c, i) => c.style.setProperty('--i', i + 1));
    })
    .catch(err => console.error('Search failed:', err));
}

qInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(runSearch, 180);
});
filters.forEach(f => f.addEventListener('change', runSearch));
clearBtn.addEventListener('click', () => {
  qInput.value = '';
  runSearch();
  qInput.focus();
});

// Smooth scroll for nav links
document.querySelectorAll('.masthead__nav a[href^="#"]').forEach(a => {
  a.addEventListener('click', (e) => {
    const id = a.getAttribute('href').slice(1);
    const el = document.getElementById(id);
    if (el) {
      e.preventDefault();
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});
