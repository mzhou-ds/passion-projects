"""Build explorer.html: an interactive scatter-plot explorer of the metrics.

Single self-contained HTML file, no external dependencies. Generated from
data/metrics.csv so it stays in sync with the analysis.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

METRICS = [
    ("year", "Year of original publication"),
    ("words", "Total words"),
    ("flesch_ease", "Flesch Reading Ease (higher = easier)"),
    ("flesch_kincaid_grade", "Flesch-Kincaid grade level"),
    ("gunning_fog", "Gunning Fog index"),
    ("avg_sentence_len", "Mean sentence length (words)"),
    ("avg_syllables_per_word", "Mean syllables per word"),
    ("ttr_10k", "Lexical diversity (type-token ratio, first 10k words)"),
    ("i_per_1k", '"I" per 1,000 words'),
    ("we_per_1k", '"we" per 1,000 words'),
    ("you_per_1k", '"you" per 1,000 words'),
    ("questions_per_1k", "Questions per 1,000 words"),
    ("abstract_per_1k", "Abstract-noun suffixes per 1,000 words"),
    ("polysyllabic_share", "Share of words with 3+ syllables"),
    ("concreteness", "Mean concreteness (1 = abstract, 5 = concrete)"),
    ("vader_mean", "Mean paragraph sentiment (VADER compound)"),
]

ERA_COLORS = {"Ancient": "#2a7f62", "Early Modern": "#b25c1e", "Modern": "#3b5bdb"}

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Philosophy in Data — Explorer</title>
<style>
  body { font-family: Georgia, 'Times New Roman', serif; max-width: 1000px;
         margin: 2rem auto; padding: 0 1.5rem; color: #1a1a1a; background: #fdfcf9; }
  h1 { font-size: 1.9rem; margin-bottom: 0.2rem; }
  .sub { color: #666; margin-bottom: 1.5rem; }
  .controls { display: flex; gap: 1.2rem; flex-wrap: wrap; margin-bottom: 1rem; }
  label { font-size: 0.85rem; color: #555; display: block; margin-bottom: 0.25rem; }
  select { font-size: 0.95rem; padding: 0.35rem 0.5rem; border: 1px solid #ccc;
           border-radius: 6px; background: #fff; max-width: 300px; }
  #plot { width: 100%; height: 480px; border: 1px solid #e5e0d5; border-radius: 8px;
          background: #fff; }
  #tooltip { position: fixed; pointer-events: none; background: rgba(20,20,20,0.92);
             color: #fff; padding: 0.6rem 0.8rem; border-radius: 6px; font-size: 0.85rem;
             display: none; max-width: 280px; line-height: 1.45; z-index: 10; }
  #tooltip .t { font-weight: bold; font-size: 1rem; }
  #tooltip .a { color: #ffd98a; }
  .legend { display: flex; gap: 1.2rem; margin-top: 0.8rem; font-size: 0.9rem; }
  .legend span::before { content: "●"; margin-right: 0.3rem; }
  .foot { margin-top: 2rem; font-size: 0.82rem; color: #888; }
  a { color: #3b5bdb; }
</style>
</head>
<body>
<h1>Philosophy in Data — Explorer</h1>
<p class="sub">Twelve philosophical texts, 2,311 years, sixteen linguistic metrics.
Pick any two metrics and see where each thinker lands. Hover a dot for details.</p>
<div class="controls">
  <div><label for="xsel">X axis</label><select id="xsel"></select></div>
  <div><label for="ysel">Y axis</label><select id="ysel"></select></div>
</div>
<svg id="plot" viewBox="0 0 960 480" preserveAspectRatio="xMidYMid meet"></svg>
<div class="legend">__LEGEND__</div>
<div id="tooltip"></div>
<p class="foot">Data: Project Gutenberg editions (public domain) · Concreteness norms:
Brysbaert, Warriner &amp; Kuperman (2014) · Sentiment: VADER ·
<a href="https://github.com/mzhou-ds/passion-projects">mzhou-ds/passion-projects</a></p>
<script>
const DATA = __DATA__;
const METRICS = __METRICS__;
const COLORS = __COLORS__;
const W = 960, H = 480, M = {l: 64, r: 24, t: 20, b: 54};
const svg = document.getElementById('plot');
const tip = document.getElementById('tooltip');
const xsel = document.getElementById('xsel'), ysel = document.getElementById('ysel');
METRICS.forEach(([k, label], i) => {
  xsel.add(new Option(label, k)); ysel.add(new Option(label, k));
});
xsel.value = 'year'; ysel.value = 'flesch_ease';

function fmtYear(v) { return v < 0 ? Math.abs(Math.round(v)) + ' BCE' : Math.round(v) + ' CE'; }

function draw() {
  const xk = xsel.value, yk = ysel.value;
  svg.innerHTML = '';
  const xs = DATA.map(d => d[xk]), ys = DATA.map(d => d[yk]);
  let x0 = Math.min(...xs), x1 = Math.max(...xs);
  let y0 = Math.min(...ys), y1 = Math.max(...ys);
  const pad = (a, b) => { const p = (b - a) * 0.08 || 1; return [a - p, b + p]; };
  [x0, x1] = pad(x0, x1); [y0, y1] = pad(y0, y1);
  const X = v => M.l + (v - x0) / (x1 - x0) * (W - M.l - M.r);
  const Y = v => H - M.b - (v - y0) / (y1 - y0) * (H - M.t - M.b);
  const ns = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs) => { const e = document.createElementNS(ns, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]); svg.appendChild(e); return e; };
  // gridlines + ticks
  for (let i = 0; i <= 5; i++) {
    const gx = x0 + (x1 - x0) * i / 5, gy = y0 + (y1 - y0) * i / 5;
    el('line', {x1: X(gx), y1: Y(y0), x2: X(gx), y2: Y(y1), stroke: '#eee'});
    el('line', {x1: X(x0), y1: Y(gy), x2: X(x1), y2: Y(gy), stroke: '#eee'});
    const tx = el('text', {x: X(gx), y: H - 30, 'text-anchor': 'middle',
      'font-size': 12, fill: '#777'});
    tx.textContent = xk === 'year' ? fmtYear(gx) : Math.round(gx * 100) / 100;
    const ty = el('text', {x: M.l - 10, y: Y(gy) + 4, 'text-anchor': 'end',
      'font-size': 12, fill: '#777'});
    ty.textContent = yk === 'year' ? fmtYear(gy) : Math.round(gy * 100) / 100;
  }
  const xl = METRICS.find(m => m[0] === xk)[1], yl = METRICS.find(m => m[0] === yk)[1];
  const xt = el('text', {x: W / 2, y: H - 6, 'text-anchor': 'middle',
    'font-size': 13, 'font-weight': 'bold', fill: '#333'}); xt.textContent = xl;
  const yt = el('text', {x: 16, y: H / 2, 'text-anchor': 'middle',
    'font-size': 13, 'font-weight': 'bold', fill: '#333',
    transform: `rotate(-90 16 ${H / 2})`}); yt.textContent = yl;
  // points
  DATA.forEach(d => {
    const c = el('circle', {cx: X(d[xk]), cy: Y(d[yk]), r: 9,
      fill: COLORS[d.era], stroke: '#fff', 'stroke-width': 2,
      style: 'cursor:pointer;opacity:0.9'});
    c.addEventListener('mousemove', ev => {
      tip.style.display = 'block';
      tip.style.left = (ev.clientX + 14) + 'px';
      tip.style.top = (ev.clientY + 14) + 'px';
      const fx = v => Math.round(v * 100) / 100;
      tip.innerHTML = `<div class="t">${d.title}</div>
        <div class="a">${d.author} · ${d.year < 0 ? Math.abs(d.year) + ' BCE' : d.year + ' CE'} · ${d.era}</div>
        <div>${xl}: <b>${xk === 'year' ? fmtYear(d[xk]) : fx(d[xk])}</b></div>
        <div>${yl}: <b>${yk === 'year' ? fmtYear(d[yk]) : fx(d[yk])}</b></div>
        <div style="color:#bbb">${Number(d.words).toLocaleString()} words</div>`;
    });
    c.addEventListener('mouseleave', () => tip.style.display = 'none');
    const lab = el('text', {x: X(d[xk]) + 12, y: Y(d[yk]) + 4, 'font-size': 12, fill: '#555'});
    lab.textContent = d.short;
  });
}
xsel.addEventListener('change', draw); ysel.addEventListener('change', draw);
draw();
</script>
</body>
</html>
"""


def main():
    df = pd.read_csv(DATA / "metrics.csv")
    SHORT = {
        "plato-apology": "Plato", "aristotle-ethics": "Aristotle",
        "aurelius-meditations": "Aurelius", "augustine-confessions": "Augustine",
        "descartes-discourse": "Descartes", "spinoza-ethics": "Spinoza",
        "hume-enquiry": "Hume", "kant-critique": "Kant",
        "mill-utilitarianism": "Mill", "nietzsche-bge": "Nietzsche",
        "james-pragmatism": "James", "russell-problems": "Russell",
    }
    df["short"] = df["slug"].map(SHORT)
    cols = ["short", "title", "author", "year", "era", "words"]
    for m, _ in METRICS:
        if m not in cols:
            cols.append(m)
    records = df[cols].round(4).to_dict("records")
    legend = "".join(
        f'<span style="color:{c}">{e}</span>' for e, c in ERA_COLORS.items())
    html = (HTML.replace("__DATA__", json.dumps(records))
                .replace("__METRICS__", json.dumps(METRICS))
                .replace("__COLORS__", json.dumps(ERA_COLORS))
                .replace("__LEGEND__", legend))
    (ROOT / "explorer.html").write_text(html, encoding="utf-8")
    print("explorer.html written")


if __name__ == "__main__":
    main()
