const reader = document.getElementById('reader');
const btns = {
  A: document.getElementById('btnA'),
  B: document.getElementById('btnB'),
  M: document.getElementById('btnM'),
  MT: document.getElementById('btnMT'),
  T: document.getElementById('btnT'),
  UT: document.getElementById('btnUT'),
};
const descriptions = {
  A: {
    title: 'OpenDyslexic A — upstream current',
    sub: 'v0.99 · Abbie Gonzalez · Feb 2025 · 1 / 2 kerning pairs',
    body: 'The current official build from the OpenDyslexic project (abbiecod.es). In commit <code>7d7f63c</code> ("adjustments in positions") the designer reworked glyph widths and sidebearings and, in the process, stripped essentially all letter-pair kerning from Regular and Bold — only a single punctuation-plus-space rule remains. Italic and Bold-Italic were not touched in the same way and still ship kerned. This is the font as Abbie currently publishes it.'
  },
  B: {
    title: 'OpenDyslexic B — legacy kerned build',
    sub: 'v0.92 · renamed for ebook-fonts (Nico Verbruggen) · 3760 pairs',
    body: 'Simply an older version of OpenDyslexic (v0.92), included for reference in the <a href="https://github.com/nicoverbruggen/ebook-fonts">ebook-fonts</a> repo — no modifications. This older upstream build predates the kerning removal and includes 3760 hand-tuned pair-adjustment rules plus a legacy <code>kern</code> table, covering most Latin letter combinations with T, V, W, Y, A. Glyph outlines are the older v0.92 shapes — predating Abbie\'s v0.99 metric and glyph refinements.'
  },
  M: {
    title: 'OpenDyslexic M — clean rebuild',
    sub: 'Experimental version · 4 styles · kerning restored',
    body: 'A four-style family built from unmodified upstream OTF sources. <b>Regular</b> uses v0.99 glyphs + B\'s 3760 kern pairs. <b>Bold</b> uses v0.99 glyphs + 5504 kern pairs from the older OpenDyslexic Bold. <b>Italic</b> (4020 pairs) and <b>Bold Italic</b> (2096 pairs) are the already-kerned kobo-font-fix builds, renamed. Same metrics as A — just with kerning restored where upstream dropped it.'
  },
  MT: {
    title: 'OpenDyslexic MT — tight variant',
    sub: 'M with tightened metrics · experimental version · all kerning preserved',
    body: 'Same as M, but every glyph\'s advance width is reduced by 60 units (on a 1000 UPM grid) with outlines shifted left by 30 so tightening is symmetric. The space glyph is narrowed from 847 → 620 units (~27% tighter). Kerning pairs are preserved on top of the new metrics, so aggressive pairs like qT (−490) combine with the global tightening. Uppercase glyphs are spared the global tightening so kerned uppercase pairs (AVATAR, TITAN) don\'t over-collapse.'
  },
  T: {
    title: 'OpenDyslexic T — tight kernless',
    sub: 'A (upstream v0.99) with tightened metrics · no kerning restored',
    body: 'A different answer to "the spacing feels too generous": keep Abbie\'s deliberate kernless upstream design, but shave 90 units off every glyph\'s advance (uppercase included, since there\'s no kerning to double-penalize) and narrow the space from 847 → 560. Digits and punctuation are <b>exempt</b> and keep their upstream metrics; sentence-ending punctuation (<code>. , : ; ! ?</code> and ellipsis) additionally gets 80 units of extra <i>leading</i> whitespace so it doesn\'t hug the preceding word. Italic and Bold Italic are <b>synthesized</b> from the Regular and Bold sources via a 12° shear — the upstream italic cuts are not used. Kerning is stripped everywhere and the <code>fi</code>/<code>fl</code> ligature substitutions are disabled across all four styles. Compare against MT to see the trade-off: MT uses per-pair kerning on top of tightening, T uses only metrics.'
  },
  UT: {
    title: 'OpenDyslexic UT — ultra tight kernless <span class="meta-pill">personal favorite</span>',
    sub: 'A (upstream v0.99) with aggressively tightened metrics · experimental version',
    body: 'The same idea as T, pushed further: −150 units off every glyph\'s advance (outlines shifted left by 75 for symmetric tightening) and the space narrowed from 847 → 480 (~43% tighter). Digits and punctuation are <b>exempt</b> from the tightening, and sentence-ending punctuation gets extra leading whitespace, matching T. Italic and Bold Italic are <b>synthesized</b> by shearing the Regular and Bold sources 12° — no upstream italic used. Still kernless, and <code>fi</code>/<code>fl</code> ligature substitutions disabled across all four styles. Useful as the extreme end of the tightening spectrum — A is untouched upstream, T is moderately tight, UT pushes metrics about as far as they can go before pairs start to collide.'
  }
};
const order = ['A','B','T','UT','M','MT'];

function setFont(which) {
  order.forEach(k => {
    reader.classList.toggle(k, which === k);
    btns[k].classList.toggle('active', which === k);
  });
  const d = descriptions[which];
  document.getElementById('desc').innerHTML =
    `<h3>${d.title}</h3><div class="sub">${d.sub}</div><p>${d.body}</p>`;
}

order.forEach(k => btns[k].onclick = () => setFont(k));
setFont('A');

document.addEventListener('keydown', (e) => {
  const cur = order.find(k => reader.classList.contains(k)) || 'A';
  if (e.key === ' ') { e.preventDefault(); setFont(order[(order.indexOf(cur)+1) % order.length]); }
  const idx = '1234567'.indexOf(e.key);
  if (idx >= 0 && idx < order.length) setFont(order[idx]);
});

const sizeEl = document.getElementById('size');
const lhEl   = document.getElementById('lh');
sizeEl.oninput = () => reader.style.fontSize = sizeEl.value + 'px';
lhEl.oninput   = () => reader.style.lineHeight = (lhEl.value/100).toString();
const justifyEl = document.getElementById('justify');
const applyJustify = () => reader.classList.toggle('justify', justifyEl.checked);
justifyEl.onchange = applyJustify;
applyJustify();

const bodyStyleEl = document.getElementById('bodyStyle');
const applyBodyStyle = () => {
  reader.classList.remove('body-italic','body-bold','body-bolditalic');
  const v = bodyStyleEl.value;
  if (v !== 'regular') reader.classList.add('body-' + v);
};
bodyStyleEl.onchange = applyBodyStyle;
