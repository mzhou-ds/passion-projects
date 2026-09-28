"""Build pairs.html: hand-verified cross-book paraphrase gallery.

Reads data/verified_pairs.json (list of hand-verified pairs, each with
self_passage, canon_passage, works, sim, note). Writes pairs.html gallery.
"""
import json, os, html

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DATA = os.path.join(PROJ, "data")

def main():
    pairs = json.load(open(os.path.join(DATA, "verified_pairs.json")))

    cards = []
    for rank, p in enumerate(pairs, 1):
        note = p.get("note", "")
        cards.append(f"""
<div class="card">
  <div class="num">#{rank} <span class="sim">cosine {p['sim']:.3f}</span></div>
  <blockquote>{html.escape(p['self_passage'])}</blockquote>
  <div class="src">&mdash; <b>{html.escape(p['self_work'])}</b></div>
  <div class="vs">&#8646;</div>
  <blockquote>{html.escape(p['canon_passage'])}</blockquote>
  <div class="src">&mdash; <b>{html.escape(p['canon_work'])}</b></div>
  {f'<div class="note">{html.escape(note)}</div>' if note else ''}
</div>""")

    page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Same idea, 2,000 years apart — pair gallery</title>
<style>
body {{ font-family: Georgia, serif; max-width: 760px; margin: 2em auto; padding: 0 1em; color: #222; }}
h1 {{ font-size: 1.5em; }} .sub {{ color: #555; margin-bottom: 2em; }}
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1.2em; margin-bottom: 1.5em; background: #fafafa; }}
.num {{ font-size: 0.85em; color: #888; margin-bottom: 0.6em; }} .sim {{ float: right; }}
blockquote {{ margin: 0.4em 0; padding-left: 1em; border-left: 3px solid #2a6f6f; font-style: italic; }}
.src {{ text-align: right; font-size: 0.9em; color: #444; margin-bottom: 0.6em; }}
.vs {{ text-align: center; color: #a03a3a; font-size: 1.3em; margin: 0.3em 0; }}
.note {{ font-size: 0.85em; color: #666; margin-top: 0.8em; font-family: sans-serif; }}
</style></head>
<body>
<h1>Same idea, 2,000 years apart</h1>
<div class="sub">Hand-verified paraphrase pairs: a passage from a self-help classic (1859&ndash;1915)
and its closest match in the ancient wisdom canon. Machine-proposed by mutual
top-5 semantic neighbors (MiniLM embeddings), then read and confirmed by a human.
{len(pairs)} pairs survived.</div>
{''.join(cards)}
</body></html>"""
    out = os.path.join(PROJ, "pairs.html")
    open(out, "w").write(page)
    print(f"wrote {out} with {len(pairs)} pairs")

if __name__ == "__main__":
    main()
