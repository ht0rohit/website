(() => {
  const CATS = ['Economy & Banking','RBI & Monetary Policy','Government Schemes','National','International','Science & Tech','Awards & Honours','Sports','Appointments','MoUs & Agreements','Summits & Conferences'];
  const store = {
    get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} }
  };
  const $ = (s, r = document) => r.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const qs = new URLSearchParams(location.search);
  const slug = c => c.toLowerCase().replace(/&/g, 'and').replace(/[^a-z]+/g, '-').replace(/^-|-$/g, '');
  const fmtDate = (d, o) => new Date(d + 'T00:00:00').toLocaleDateString('en-IN', o || { day: 'numeric', month: 'short', year: 'numeric' });

  // theme
  const applyTheme = t => t ? document.documentElement.setAttribute('data-theme', t) : document.documentElement.removeAttribute('data-theme');
  applyTheme(store.get('theme', null));

  let _index, _days = {};
  const loadIndex = async () => _index ??= await (await fetch('data/index.json')).json();
  const loadDay = async d => _days[d] ??= await (await fetch(`data/${d}.json`)).json().then(j => j.items || []).catch(() => []);
  const loadAll = async dates => (await Promise.all(dates.map(loadDay))).flat();

  const bookmarks = () => new Set(store.get('bookmarks', []));
  const reads = () => new Set(store.get('read', []));
  const toggle = (key, id) => { const s = new Set(store.get(key, [])); s.has(id) ? s.delete(id) : s.add(id); store.set(key, [...s]); return s.has(id); };

  function card(it) {
    const b = bookmarks().has(it.id), r = reads().has(it.id);
    const facts = (it.key_facts || []).map(f => `<li>${esc(f)}</li>`).join('');
    return `<article class="card${r ? ' read' : ''}" data-id="${esc(it.id)}">
      <div class="meta"><span class="badge">${esc(it.category)}</span>${it.exam_relevance === 'banking' || it.exam_relevance === 'rbi' ? '<span class="badge hot">Banking priority</span>' : ''}<span>${esc(it.ministry)}</span><span>${fmtDate(it.date)}</span></div>
      <h3>${esc(it.title)}</h3><p>${esc(it.summary)}</p>
      ${facts ? `<ul class="facts">${facts}</ul>` : ''}
      <div class="actions">
        <button class="btn" data-act="bm" aria-pressed="${b}">${b ? '★ Saved' : '☆ Save'}</button>
        <button class="btn" data-act="read" aria-pressed="${r}">${r ? '✓ Read' : 'Mark read'}</button>
        <a class="btn" href="${esc(it.source_url)}" target="_blank" rel="noopener">Source: PIB ↗</a>
      </div></article>`;
  }
  function list(el, items, emptyMsg) {
    el.innerHTML = items.length ? items.map(card).join('') : `<p class="empty">${emptyMsg || 'Nothing here yet.'}</p>`;
  }
  function wireCards(root, onChange) {
    root.addEventListener('click', e => {
      const btn = e.target.closest('[data-act]'); if (!btn) return;
      const id = btn.closest('.card').dataset.id;
      toggle(btn.dataset.act === 'bm' ? 'bookmarks' : 'read', id);
      onChange();
    });
  }
  const rank = it => ({ rbi: 0, banking: 1, ssc: 2, general: 3 }[it.exam_relevance] ?? 3);
  const sortItems = a => [...a].sort((x, y) => rank(x) - rank(y));

  function banner(idx) {
    if (!idx.sample) return;
    const m = $('main'); if (!m) return;
    m.insertAdjacentHTML('afterbegin', '<div class="banner"><b>Sample data.</b> These entries are placeholders to demo the layout. Live PIB releases appear once the daily update job runs.</div>');
  }
  function dateStrip(el, dates, active, base) {
    el.innerHTML = dates.slice(0, 30).map(d => {
      const dt = new Date(d + 'T00:00:00');
      return `<a class="chip date-chip" href="${base}?date=${d}" ${d === active ? 'aria-current="true"' : ''}><small>${dt.toLocaleDateString('en-IN', { weekday: 'short' })}</small>${dt.getDate()} ${dt.toLocaleDateString('en-IN', { month: 'short' })}</a>`;
    }).join('');
  }
  function catChips(el, active) {
    el.innerHTML = `<a class="chip" href="category.html" ${!active ? 'aria-current="true"' : ''}>All</a>` + CATS.map(c => `<a class="chip" href="category.html?c=${slug(c)}" ${slug(c) === active ? 'aria-current="true"' : ''}>${esc(c)}</a>`).join('');
  }

  const pages = {
    async home(idx) {
      const today = idx.dates[0];
      $('#today-label').textContent = fmtDate(today, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
      dateStrip($('#strip'), idx.dates, today, 'daily.html');
      catChips($('#chips'));
      const items = sortItems(await loadDay(today));
      const render = () => {
        const q = $('#q').value.trim().toLowerCase();
        const shown = q ? items.filter(i => (i.title + ' ' + i.summary + ' ' + (i.tags || []).join(' ')).toLowerCase().includes(q)) : items.slice(0, 10);
        $('#list-title').textContent = q ? `Search results (${shown.length})` : "Today's top picks for banking exams";
        list($('#list'), shown, q ? 'No matches today. Try the archive.' : 'No items for this day.');
      };
      $('#q').addEventListener('input', render); render(); wireCards($('#list'), render);
      const s = store.get('quizStats', { streak: 0, best: 0, last: null });
      $('#streak').textContent = s.streak; $('#saved').textContent = bookmarks().size; $('#readn').textContent = reads().size;
    },
    async daily(idx) {
      const d = idx.dates.includes(qs.get('date')) ? qs.get('date') : idx.dates[0];
      $('#day-label').textContent = fmtDate(d, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
      dateStrip($('#strip'), idx.dates, d, 'daily.html');
      const items = sortItems(await loadDay(d)); const render = () => list($('#list'), items, 'No items for this day.');
      render(); wireCards($('#list'), render);
    },
    async category(idx) {
      const c = qs.get('c') || ''; catChips($('#chips'), c);
      const name = CATS.find(x => slug(x) === c);
      $('#cat-title').textContent = name || 'All categories';
      const days = idx.dates.slice(0, 14);
      const all = sortItems((await loadAll(days)).filter(i => !name || i.category === name)).sort((a, b) => b.date.localeCompare(a.date));
      const render = () => list($('#list'), all, 'No items in this category for the last 14 days.');
      render(); wireCards($('#list'), render);
    },
    async bookmarks(idx) {
      const all = await loadAll(idx.dates);
      const render = () => { const b = bookmarks(); list($('#list'), all.filter(i => b.has(i.id)), 'No saved items yet. Tap ☆ Save on any card.'); };
      render(); wireCards($('#list'), render);
    }
  };

  window.CA = { store, loadIndex, loadDay, loadAll, esc, fmtDate, slug, CATS };

  document.addEventListener('DOMContentLoaded', async () => {
    const t = $('#theme'); if (t) t.addEventListener('click', () => {
      const dark = document.documentElement.getAttribute('data-theme') === 'dark' || (!document.documentElement.getAttribute('data-theme') && matchMedia('(prefers-color-scheme:dark)').matches);
      const next = dark ? 'light' : 'dark'; applyTheme(next); store.set('theme', next);
    });
    const page = document.body.dataset.page; if (!pages[page]) return;
    try { const idx = await loadIndex(); banner(idx); await pages[page](idx); }
    catch (e) { console.error(e); const l = $('#list'); if (l) l.innerHTML = '<p class="empty">Could not load data. Please refresh.</p>'; }
  });
})();
