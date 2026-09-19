"""Core analyses for Laozi-and-Emerson (LSA sentence vectors).

1. Kinship index: for every sentence, its nearest neighbor (cosine) among all
   other sentences. What share of each work's sentences find their closest
   match in the *other* tradition (East vs West)? Plus a size-robust
   "coverage" metric: best same-tradition similarity vs best cross-tradition
   similarity per sentence.
2. Quote mining: top East<->West sentence pairs by cosine similarity, filtered
   to pairs sharing >= 2 content words (kills single-word collisions like two
   sentences that both reduce to ["know"]), deduped, diversity-capped
   -> data/pairs.csv.
3. Theme clustering: KMeans(k=24) on the LSA vectors; per-cluster tradition
   mix and top TF-IDF terms -> shared themes (both traditions >= 25%).
   UMAP is used only for 2D plot coordinates.
4. Discriminative words: logistic regression East vs West on TF-IDF bigrams.
5. Section affinity (Western sections only): which Emerson essay is most
   Taoist? which Walden chapter most Buddhist?

Outputs: data/results.json, data/pairs.csv, data/clusters.csv,
         data/section_affinity.csv
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

EAST_WORKS = {"Tao Te Ching", "Dhammapada"}
PAIR_MIN_SIM = 0.30
MAX_PAIRS_PER_WORKPAIR = 15
MAX_PAIRS_TOTAL = 60
N_CLUSTERS = 24

STOP = set("""
a an the and or of to in on for with as by at from is are was were be been
being it its it’s this that these those i you he she we they me him her us
them my your his our their mine yours ours theirs myself yourself himself
herself itself ourselves yourselves themselves what which who whom whose
when where why how all any both each few more most other some such no nor
not only own same so than too very can will just don should now doth hath
thou thee thy thine ye o oh ah lo ere e’en e'er tis twas
""".split())


def content_words(s):
    return [w for w in re.findall(r"[a-z']+", s.lower())
            if w not in STOP and len(w) >= 3]


def load():
    df = pd.read_csv(DATA / "units.csv").reset_index(drop=True)
    z = np.load(DATA / "embeddings.npz")
    emb = z["embeddings"].astype(np.float64)
    assert len(df) == emb.shape[0], "units/embeddings row mismatch"
    return df, emb


def nearest_neighbors(emb):
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=2, metric="cosine").fit(emb)
    dist, idx = nn.kneighbors(emb)
    return 1.0 - dist[:, 1], idx[:, 1]


def kinship(df, emb):
    sim, nidx = nearest_neighbors(emb)
    df = df.copy()
    df["nn_sim"] = sim
    df["nn_work"] = df["work"].iloc[nidx].values
    df["nn_tradition"] = df["tradition"].iloc[nidx].values

    # size-robust coverage: best same-tradition sim vs best cross-tradition sim
    east_idx = df.index[df["tradition"] == "East"].to_numpy()
    west_idx = df.index[df["tradition"] == "West"].to_numpy()
    best_same = np.empty(len(df))
    best_cross = np.empty(len(df))
    for i in range(len(df)):
        pool_same = east_idx if df.loc[i, "tradition"] == "East" else west_idx
        pool_cross = west_idx if df.loc[i, "tradition"] == "East" else east_idx
        pool_same = pool_same[pool_same != i]
        best_same[i] = (emb[i] @ emb[pool_same].T).max()
        best_cross[i] = (emb[i] @ emb[pool_cross].T).max()
    df["best_same"] = best_same
    df["best_cross"] = best_cross
    df["cross_beats_same"] = best_cross > best_same

    out = {}
    for work, g in df.groupby("work"):
        out[work] = {
            "n": int(len(g)),
            "pct_nn_other_tradition": round(
                100 * (g["nn_tradition"] != g["tradition"]).mean(), 1),
            "mean_best_same": round(float(g["best_same"].mean()), 3),
            "mean_best_cross": round(float(g["best_cross"].mean()), 3),
            "pct_cross_beats_same": round(100 * g["cross_beats_same"].mean(), 1),
        }
    return df, out


def top_cross_pairs(df, emb):
    """Mine East<->West sentence pairs.

    Two-sided signal: (1) embedding cosine for semantic closeness, restricted
    to *mutual* top-5 matches so the pairing is not one-directional; (2) a
    lexical sanity check -- the pair must share >=2 content words whose
    combined idf is high, which kills degenerate collisions on bleached
    words ("things", "know", "man") that otherwise saturate the top of the
    cosine ranking on short sentences.
    """
    import json, re
    idf = json.loads((DATA / "tfidf_idf.json").read_text())
    df = df.copy()
    df["cw"] = df["text"].map(lambda s: set(content_words(s)))
    east = df.index[df["tradition"] == "East"].to_numpy()
    west = df.index[df["tradition"] == "West"].to_numpy()
    sims = emb[east] @ emb[west].T
    topE = np.argsort(-sims, axis=1)[:, :5]
    topW = np.argsort(-sims, axis=0)[:5, :]
    mutual = np.zeros_like(sims, dtype=bool)
    for ei in range(len(east)):
        for wj in topE[ei]:
            if ei in topW[:, wj]:
                mutual[ei, wj] = True
    rows = []
    for ei in range(len(east)):
        for wj in np.where(mutual[ei])[0]:
            s = float(sims[ei, wj])
            if s < PAIR_MIN_SIM:
                continue
            i, j = int(east[ei]), int(west[wj])
            if len(df.loc[i, "cw"]) < 3 or len(df.loc[j, "cw"]) < 3:
                continue
            overlap = df.loc[i, "cw"] & df.loc[j, "cw"]
            if len(overlap) < 2:
                continue
            # idf-weighted overlap: shared rare words count, shared
            # bleached words ("things", "know") barely do
            oidf = sum(idf.get(w, 0.0) + idf.get(w + "s", 0.0)
                       for w in overlap)
            if oidf < 12.0:
                continue
            rows.append((s, oidf, i, j, sorted(overlap)))
    rows.sort(key=lambda r: (-r[0], -r[1]))
    seen, pairs, per_wp = set(), [], {}
    for s, oidf, i, j, overlap in rows:
        key = (df.loc[i, "text"][:60], df.loc[j, "text"][:60])
        if key in seen:
            continue
        seen.add(key)
        wp = (df.loc[i, "work"], df.loc[j, "work"])
        per_wp[wp] = per_wp.get(wp, 0) + 1
        if per_wp[wp] > MAX_PAIRS_PER_WORKPAIR:
            continue
        pairs.append({
            "similarity": round(s, 3),
            "shared_words": ", ".join(overlap[:8]),
            "east_text": df.loc[i, "text"],
            "east_source": f"{df.loc[i, 'work']} — {df.loc[i, 'section']}",
            "west_text": df.loc[j, "text"],
            "west_source": f"{df.loc[j, 'work']} — {df.loc[j, 'section']}",
        })
        if len(pairs) >= MAX_PAIRS_TOTAL:
            break
    pdf = pd.DataFrame(pairs)
    pdf.to_csv(DATA / "pairs.csv", index=False)
    return pdf


def cluster_themes(df, emb):
    import umap
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer

    km = KMeans(n_clusters=N_CLUSTERS, n_init=10, random_state=42)
    labels = km.fit_predict(emb)
    xy = umap.UMAP(n_neighbors=15, min_dist=0.1, n_components=2,
                   metric="cosine", random_state=42).fit_transform(emb)

    df = df.copy()
    df["cluster"] = labels
    df["umap_x"], df["umap_y"] = xy[:, 0], xy[:, 1]

    vec = TfidfVectorizer(max_features=8000, ngram_range=(1, 2),
                          stop_words="english", min_df=3)
    X = vec.fit_transform(df["text"])
    terms = np.array(vec.get_feature_names_out())

    clusters = []
    for c in range(N_CLUSTERS):
        g = df[df["cluster"] == c]
        east_share = float((g["tradition"] == "East").mean())
        mean_tfidf = np.asarray(X[g.index].mean(axis=0)).ravel()
        top = terms[np.argsort(-mean_tfidf)[:8]].tolist()
        works = g["work"].value_counts()
        clusters.append({
            "cluster": int(c),
            "size": int(len(g)),
            "east_share": round(east_share, 3),
            "west_share": round(1 - east_share, 3),
            "shared": bool(min(east_share, 1 - east_share) >= 0.25),
            "top_terms": top,
            "work_mix": {k: int(v) for k, v in works.items()},
        })
    df[["unit_id", "cluster", "umap_x", "umap_y"]].to_csv(
        DATA / "clusters.csv", index=False)
    return df, clusters


def discriminative_words(df):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    vec = TfidfVectorizer(max_features=6000, ngram_range=(1, 2),
                          stop_words="english", min_df=5)
    X = vec.fit_transform(df["text"])
    y = (df["tradition"] == "East").astype(int).to_numpy()
    clf = LogisticRegression(max_iter=2000, C=1.0).fit(X, y)
    terms = np.array(vec.get_feature_names_out())
    coef = clf.coef_[0]
    return {"train_accuracy": round(float(clf.score(X, y)), 3),
            "most_east": terms[np.argsort(-coef)[:25]].tolist(),
            "most_west": terms[np.argsort(coef)[:25]].tolist()}


def section_affinity(df, emb):
    # Western sections only: rank Emerson essays by Tao affinity,
    # Walden chapters by Dhammapada affinity.
    tao = emb[df["work"] == "Tao Te Ching"]
    dham = emb[df["work"] == "Dhammapada"]
    rows = []
    for (work, section), g in df[df["tradition"] == "West"].groupby(
            ["work", "section"]):
        if len(g) < 8:
            continue
        E = emb[g.index]
        rows.append({
            "work": work,
            "section": section,
            "n": int(len(g)),
            "tao_affinity": round(float((E @ tao.T).mean()), 4),
            "dhammapada_affinity": round(float((E @ dham.T).mean()), 4),
        })
    aff = pd.DataFrame(rows)
    return aff


def main():
    df, emb = load()
    print(f"loaded {len(df)} sentences, emb {emb.shape}")

    df, kin = kinship(df, emb)
    pairs = top_cross_pairs(df, emb)
    print(f"kinship: {json.dumps(kin, indent=1)}")
    print(f"{len(pairs)} cross-tradition pairs "
          f"(mutual top-5, idf-weighted overlap filter)")

    df, clusters = cluster_themes(df, emb)
    shared = [c for c in clusters if c["shared"]]
    print(f"{len(clusters)} clusters, {len(shared)} shared themes")

    disc = discriminative_words(df)
    print(f"East-vs-West classifier train acc: {disc['train_accuracy']}")

    aff = section_affinity(df, emb)
    aff.to_csv(DATA / "section_affinity.csv", index=False)
    print("most Taoist Emerson essays:")
    print(aff[aff.work == "Essays, First Series"].sort_values(
        "tao_affinity", ascending=False)[["section", "tao_affinity"]].to_string(index=False))
    print("most Buddhist Walden chapters:")
    print(aff[aff.work == "Walden"].sort_values(
        "dhammapada_affinity", ascending=False)[["section", "dhammapada_affinity"]].to_string(index=False))

    results = {
        "n_sentences": int(len(df)),
        "kinship": kin,
        "n_cross_pairs": int(len(pairs)),
        "pair_min_sim": PAIR_MIN_SIM,
        "clusters": clusters,
        "n_shared_themes": len(shared),
        "discriminative_words": disc,
    }
    (DATA / "results.json").write_text(json.dumps(results, indent=2))
    print("wrote data/results.json, data/pairs.csv, data/clusters.csv, "
          "data/section_affinity.csv")


if __name__ == "__main__":
    main()
