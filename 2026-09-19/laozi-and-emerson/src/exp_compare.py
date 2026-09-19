"""Experiment: compare spaCy-averaged vs LSA sentence vectors for cross-tradition
pair mining. Prints top pairs from each so we can pick the better representation
by human inspection."""
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

DATA = "data"


def lsa_vectors(texts):
    vec = TfidfVectorizer(max_features=12000, ngram_range=(1, 2),
                          stop_words="english", min_df=2)
    X = vec.fit_transform(texts)
    svd = TruncatedSVD(n_components=256, random_state=42)
    return normalize(svd.fit_transform(X)).astype(np.float64)


def top_pairs(df, emb, k=12):
    east = df.index[df["tradition"] == "East"].to_numpy()
    west = df.index[df["tradition"] == "West"].to_numpy()
    sims = emb[east] @ emb[west].T
    best_w, best_s = sims.argmax(1), sims.max(1)
    order = np.argsort(-best_s)[: k * 3]
    seen, out = set(), []
    for ei in order:
        i, j = int(east[ei]), int(west[best_w[ei]])
        key = (df.loc[i, "text"][:60], df.loc[j, "text"][:60])
        if key in seen:
            continue
        seen.add(key)
        out.append((float(best_s[ei]), df.loc[i, "text"],
                    f"{df.loc[i,'work']} {df.loc[i,'section']}",
                    df.loc[j, "text"], f"{df.loc[j,'work']} {df.loc[j,'section']}"))
        if len(out) >= k:
            break
    return out


def show(title, pairs):
    print(f"\n===== {title} =====")
    for s, et, es, wt, ws in pairs:
        print(f"[{s:.3f}] {es}\n  E: {et[:160]}\n  W({ws}): {wt[:160]}")


def main():
    df = pd.read_csv(f"{DATA}/units.csv").reset_index(drop=True)
    lsa = lsa_vectors(df["text"].tolist())
    sp = np.load(f"{DATA}/embeddings.npz")["embeddings"].astype(np.float64)
    show("LSA", top_pairs(df, lsa))
    show("SPACY", top_pairs(df, sp))


if __name__ == "__main__":
    main()
