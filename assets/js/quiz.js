(() => {
  const { store, loadIndex, loadDay, esc, fmtDate } = window.CA;
  const $ = s => document.querySelector(s);
  const shuffle = a => { a = [...a]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };

  // Question from an item: "Which ministry ...?" / "Which category...?" built from real fields, distractors from other items.
  function build(items) {
    const qs = [];
    const pool = f => [...new Set(items.map(f).filter(Boolean))];
    const mins = pool(i => i.ministry), cats = pool(i => i.category);
    for (const it of shuffle(items)) {
      const kinds = [];
      if (mins.length >= 4) kinds.push(['ministry', mins, `Which ministry/department issued the release: “${it.title}”?`, it.ministry]);
      if (cats.length >= 4) kinds.push(['category', cats, `“${it.title}” — under which topic would you file this?`, it.category]);
      (it.key_facts || []).forEach(f => { if (f.includes(':')) { const [k, v] = f.split(/:(.+)/); kinds.push(['fact', null, `${it.title}: what is “${k.trim()}”?`, v.trim()]); } });
      if (!kinds.length) continue;
      const [, opts, q, ans] = kinds[Math.floor(Math.random() * kinds.length)];
      let choices;
      if (opts) choices = shuffle([ans, ...shuffle(opts.filter(o => o !== ans)).slice(0, 3)]);
      else {
        const others = items.flatMap(i => (i.key_facts || []).filter(f => f.includes(':')).map(f => f.split(/:(.+)/)[1].trim())).filter(v => v !== ans);
        const d = shuffle([...new Set(others)]).slice(0, 3); if (d.length < 3) continue; choices = shuffle([ans, ...d]);
      }
      qs.push({ q, choices, ans, src: it.source_url });
      if (qs.length >= 8) break;
    }
    return qs;
  }

  function finish(score, total, date) {
    const s = store.get('quizStats', { streak: 0, best: 0, last: null });
    const today = new Date().toISOString().slice(0, 10);
    if (s.last !== today) {
      const y = new Date(Date.now() - 864e5).toISOString().slice(0, 10);
      s.streak = s.last === y ? s.streak + 1 : 1; s.last = today;
    }
    s.best = Math.max(s.best, score); store.set('quizStats', s);
    $('#quiz').innerHTML = `<div class="card"><h2>Score: ${score}/${total}</h2><p>Streak: <b>${s.streak}</b> day(s) · Best: ${s.best}</p><div class="actions"><button class="btn primary" onclick="location.reload()">Try again</button><a class="btn" href="daily.html?date=${date}">Revise the day</a></div></div>`;
  }

  async function run() {
    const idx = await loadIndex();
    const date = idx.dates[0]; $('#qdate').textContent = fmtDate(date);
    const items = await loadDay(date);
    const qs = build(items);
    if (qs.length < 3) { $('#quiz').innerHTML = '<p class="empty">Not enough items today to build a quiz.</p>'; return; }
    let i = 0, score = 0;
    const show = () => {
      const q = qs[i];
      $('#quiz').innerHTML = `<div class="progress"><i style="width:${(i / qs.length) * 100}%"></i></div>
        <div class="card"><div class="meta">Question ${i + 1} of ${qs.length}</div><h3>${esc(q.q)}</h3>
        ${q.choices.map((c, k) => `<button class="opt" data-k="${k}">${esc(c)}</button>`).join('')}
        <div id="fb" class="why" aria-live="polite"></div><div class="actions"><button class="btn primary" id="next" hidden>${i + 1 === qs.length ? 'Finish' : 'Next'}</button></div></div>`;
      document.querySelectorAll('.opt').forEach(b => b.addEventListener('click', () => {
        const ok = q.choices[b.dataset.k] === q.ans; if (ok) score++;
        document.querySelectorAll('.opt').forEach(o => { o.disabled = true; if (q.choices[o.dataset.k] === q.ans) o.classList.add('right'); });
        if (!ok) b.classList.add('wrong');
        $('#fb').innerHTML = `${ok ? '✅ Correct.' : '❌ Answer: ' + esc(q.ans)} <a href="${esc(q.src)}" target="_blank" rel="noopener">PIB source ↗</a>`;
        $('#next').hidden = false; $('#next').focus();
      }));
      $('#next').addEventListener('click', () => { ++i < qs.length ? show() : finish(score, qs.length, date); });
    };
    show();
  }
  document.addEventListener('DOMContentLoaded', () => run().catch(e => { console.error(e); $('#quiz').innerHTML = '<p class="empty">Could not load quiz.</p>'; }));
})();
