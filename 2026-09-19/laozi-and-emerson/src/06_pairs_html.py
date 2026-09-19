"""Build pairs.html: a browsable gallery of hand-verified East<->West pairs."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

TEMPLATE_CARD = """
  <div class="card">
    <div class="method">{method}</div>
    <div class="quotes">
      <div class="q east">
        <div class="src">{east_src}</div>
        <p>&ldquo;{east_text}&rdquo;</p>
      </div>
      <div class="q west">
        <div class="src">{west_src}</div>
        <p>&ldquo;{west_text}&rdquo;</p>
      </div>
    </div>
  </div>
"""

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Same Thought, 2,200 Years Apart &mdash; Laozi and Emerson</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 900px; margin: 0 auto;
         padding: 2rem 1.2rem; color: #222; background: #faf8f4; }}
  h1 {{ font-size: 1.9rem; margin-bottom: 0.2rem; }}
  .sub {{ color: #666; margin-bottom: 2rem; }}
  .card {{ background: #fff; border: 1px solid #e4ddcf; border-radius: 10px;
          padding: 1.2rem 1.4rem; margin-bottom: 1.2rem;
          box-shadow: 0 1px 3px rgba(0,0,0,0.05); position: relative; }}
  .score {{ position: absolute; top: 0.9rem; right: 1.1rem; font-size: 0.8rem;
           color: #999; font-family: monospace; }}
  .method {{ position: absolute; top: 0.9rem; right: 1.1rem; font-size: 0.72rem;
           color: #aaa; font-style: italic; }}
  .quotes {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; }}
  @media (max-width: 640px) {{ .quotes {{ grid-template-columns: 1fr; }} }}
  .q p {{ font-size: 1.02rem; line-height: 1.55; margin: 0.4rem 0 0; }}
  .src {{ font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; }}
  .east .src {{ color: #2f6f9f; }} .west .src {{ color: #c26a2b; }}
  .note {{ font-size: 0.9rem; color: #777; margin-top: 2.5rem; }}
</style>
</head>
<body>
<h1>Same thought, 2,200 years apart</h1>
<p class="sub">Ten hand-verified parallels between the
Tao Te Ching, the Dhammapada, Emerson&rsquo;s Essays, and Thoreau&rsquo;s Walden.
Six surfaced by embedding similarity (mutual top-5 cross-tradition matches);
four by thematic search. Every pair was verified by a human reader.
Full method in the project README.</p>
{cards}
<p class="note">Embeddings are LSA (TF-IDF 1&ndash;2 grams &rarr; 256-dim SVD),
cosine similarity. Fully automated mining mostly produced spurious
word-overlap matches, so the gallery is curated, not raw output.
All texts public domain via Project Gutenberg.</p>
</body>
</html>
"""


def main():
    pairs = json.loads((DATA / "pairs_curated.json").read_text())
    cards = []
    for r in pairs:
        cards.append(TEMPLATE_CARD.format(
            method=html.escape(r["method"]),
            east_text=html.escape(r["east_text"]),
            east_src=html.escape(r["east_source"]),
            west_text=html.escape(r["west_text"]),
            west_src=html.escape(r["west_source"]),
        ))
    (ROOT / "pairs.html").write_text(PAGE.format(cards="\n".join(cards)))
    print(f"wrote pairs.html with {len(cards)} curated pairs")


if __name__ == "__main__":
    main()
