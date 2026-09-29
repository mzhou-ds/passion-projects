"""Build pairs.html: hand-verified Confucius <-> modern-management pairs + unrediscovered."""
import csv, json, os, html

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DATA = os.path.join(PROJ, "data")

adj = json.load(open(os.path.join(DATA, "adjudication.json")))
lead = {r["passage_id"]: r for r in csv.DictReader(open(os.path.join(DATA, "leadership.tsv")), delimiter="\t")}
modern = {r["id"]: r for r in csv.DictReader(open(os.path.join(DATA, "modern.tsv")), delimiter="\t")}
VCOL = {"strong": "#1b7a3d", "moderate": "#7bc47f", "weak": "#e8a020", "absent": "#b03a2e"}

def esc(s): return html.escape(s)

cards = []
for v in adj["verdicts"]:
    m = modern[v["id"]]
    shelf = "Project Oxygen" if v["id"].startswith("oxy") else "Gallup Q12"
    if v["verdict"] == "absent":
        cards.append(f"""<div class="card"><div class="v" style="background:{VCOL['absent']}">absent</div>
<div class="mod"><b>{esc(m['label'])}</b> <span class="shelf">{shelf}</span><p>{esc(m['text'])}</p></div>
<div class="anc none">No Confucian precedent found in the 66-passage management corpus.</div></div>""")
        continue
    pairs = "".join(
        f"""<div class="pair"><div class="ref">Analects {lead[p['passage_id']]['book']}.{lead[p['passage_id']]['chap']} — {esc(lead[p['passage_id']]['theme'])}</div>
<blockquote>{esc(lead[p['passage_id']]['text'][:700])}</blockquote>
<div class="note">{esc(p['note'])}</div></div>"""
        for p in v["passages"])
    cards.append(f"""<div class="card"><div class="v" style="background:{VCOL[v['verdict']]}">{v['verdict']}</div>
<div class="mod"><b>{esc(m['label'])}</b> <span class="shelf">{shelf}</span><p>{esc(m['text'][:400])}</p></div>
{pairs}</div>""")

unred = "".join(
    f"""<div class="card"><div class="ref">Analects {lead[u['passage_id']]['book']}.{u['passage_id'] and lead[u['passage_id']]['chap']} — no modern equivalent</div>
<h3>{esc(u['title'])}</h3><blockquote>{esc(lead[u['passage_id']]['text'][:700])}</blockquote>
<div class="note">{esc(u['note'])}</div></div>"""
    for u in adj["unrediscovered"])

page = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Confucius vs Google's People Science — the pairs</title>
<style>body{{font-family:Georgia,serif;max-width:860px;margin:2em auto;padding:0 1em;color:#222;line-height:1.55}}
.card{{border:1px solid #ddd;border-radius:10px;padding:1.1em 1.3em;margin:1.2em 0;position:relative;background:#fff}}
.v{{position:absolute;top:1em;right:1em;color:#fff;font-size:.75em;padding:.25em .7em;border-radius:20px;text-transform:uppercase;letter-spacing:.08em}}
.mod p{{color:#444}}.shelf{{font-size:.8em;color:#888;margin-left:.6em}}blockquote{{border-left:3px solid #1b7a3d;margin:.8em 0;padding:.2em 0 .2em 1em;color:#333;font-style:italic}}
.ref{{font-size:.85em;color:#1b7a3d;font-weight:bold}}.note{{font-size:.92em;color:#555}}
.none{{color:#999;font-style:italic}}h1{{font-size:1.7em}}h2{{margin-top:2.2em;border-bottom:2px solid #1b7a3d;padding-bottom:.3em}}
h3{{margin:.4em 0}}</style></head><body>
<h1>Confucius vs Google's People Science — the verified pairs</h1>
<p>Every claimed match below was hand-verified against the full 66-passage corpus (Legge translation, Project Gutenberg #4094).
Verdicts: <b>strong</b> = same idea; <b>moderate</b> = same move, different idiom; <b>weak</b> = partial; <b>absent</b> = no precedent found.</p>
<h2>The matches (and the misses)</h2>
{''.join(cards)}
<h2>Ideas Confucius had that management science never productized</h2>
{unred}
<p style="color:#888;font-size:.85em">Method: MiniLM embeddings + permutation enrichment test + human adjudication of every pair. See README for details.</p>
</body></html>"""
open(os.path.join(PROJ, "pairs.html"), "w").write(page)
print("pairs.html written,", len(cards), "cards")
