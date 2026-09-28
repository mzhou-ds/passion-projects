#!/usr/bin/env python3
"""wisdom.py — semantic search over the wisdom corpus (see README).

Ask it a question or describe a problem; it returns the most relevant
passage from each shelf: the ancient canon, the transcendentalists,
and the self-help classics.

Usage:
    python3 wisdom.py "how do I deal with a difficult coworker"
    python3 wisdom.py --n 3 "what to do when plans fall apart"

Requires: sentence-transformers (see requirements.txt).
Embeddings are precomputed in data/embeddings_st.npz.
"""
import argparse, os, sys

# Keep the model loader offline: the snapshot lives in the local HF cache
# (see README / data build notes), so no network is needed or wanted.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
# Local snapshot of sentence-transformers/all-MiniLM-L6-v2, cached during the build.
MODEL_DIR = os.path.expanduser(
    "~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/local")

GROUP_NAMES = {"canon": "ANCIENT CANON", "philosophy": "TRANSCENDENTALISTS", "selfhelp": "SELF-HELP CLASSICS"}

def main():
    ap = argparse.ArgumentParser(description="Search the wisdom corpus by meaning.")
    ap.add_argument("query", nargs="+", help="question or problem, in plain words")
    ap.add_argument("--n", type=int, default=2, help="passages per shelf (default 2)")
    args = ap.parse_args()
    query = " ".join(args.query)

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        sys.exit("sentence-transformers is not installed. Run: pip install -r requirements.txt")

    E = np.load(os.path.join(DATA, "embeddings_st.npz"))["E"]
    df = pd.read_csv(os.path.join(DATA, "corpus.csv"))
    n_passages = len(df)
    ap.description = f"Search {n_passages:,} passages of wisdom by meaning."
    model = SentenceTransformer(MODEL_DIR if os.path.isdir(MODEL_DIR) else "all-MiniLM-L6-v2")
    q = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
    sims = E @ q
    df = df.copy()
    df["sim"] = sims

    print(f'\n  "{query}"\n')
    for group in ["canon", "philosophy", "selfhelp"]:
        sub = df[df["group"] == group].nlargest(args.n, "sim")
        print(f"--- {GROUP_NAMES[group]} ---")
        for _, r in sub.iterrows():
            print(f"\n  \"{r['passage']}\"")
            print(f"  — {r['title']} ({r['author']}, {int(r['year']) if r['year'] > 0 else f'c. {abs(int(r['year']))} BCE'})  [sim {r['sim']:.2f}]")
        print()

if __name__ == "__main__":
    main()
