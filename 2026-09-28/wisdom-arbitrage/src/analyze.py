"""Wisdom arbitrage: how much of classic self-help is paraphrased ancient wisdom,
and which ancient ideas the self-help industry never productized.

Pipeline:
  1. Embed all passages (sentence-transformers MiniLM; LSA fallback).
  2. Repackaging index: for each self-help passage, best cosine sim to the
     ancient canon. Book-level paraphrase / near-duplicate rates.
  3. Cross-book pair mining (mutual top-k + hand verification list).
  4. KMeans clustering: universal clusters, industry-only clusters, and
     white-space clusters (canon-heavy, self-help-absent) = the arbitrage.
  5. UMAP projection + figures; results.json; data for wisdom.py and explorer.
"""
import argparse, csv, json, os, re, sys
import numpy as np
import pandas as pd
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DATA = os.path.join(PROJ, "data")
FIG = os.path.join(PROJ, "figures")
os.makedirs(FIG, exist_ok=True)

SELFBOOKS = ["smiles-self-help", "barnum-money", "allen-thinketh", "wattles-rich", "conwell-acres"]

def load_corpus():
    df = pd.read_csv(os.path.join(DATA, "corpus.csv"))
    return df

def clean_for_embed(texts):
    """Strip KJV verse refs (22:29) so numbering doesn't drive similarity."""
    return [re.sub(r"\b\d+:\d+\b", " ", t) for t in texts]

def embed_st(texts):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return model.encode(clean_for_embed(texts), batch_size=64, show_progress_bar=True,
                        convert_to_numpy=True, normalize_embeddings=True)

def embed_lsa(texts, dim=256):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import normalize
    vec = TfidfVectorizer(max_features=40000, ngram_range=(1, 2), min_df=3,
                          stop_words="english", sublinear_tf=True)
    X = vec.fit_transform(texts)
    svd = TruncatedSVD(n_components=dim, random_state=42)
    E = normalize(svd.fit_transform(X))
    return E, vec, svd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="st", choices=["st", "lsa"])
    args = ap.parse_args()

    df = load_corpus()
    texts = df["passage"].tolist()
    n = len(df)
    print(f"corpus: {n} passages")

    cache = os.path.join(DATA, f"embeddings_{args.backend}.npz")
    if os.path.exists(cache):
        E = np.load(cache)["E"]
        print("loaded cached embeddings", E.shape)
    else:
        if args.backend == "st":
            E = embed_st(texts)
        else:
            E, _, _ = embed_lsa(texts)
        np.savez_compressed(cache, E=E)
        print("saved embeddings", E.shape)

    canon_mask = (df["group"] == "canon").to_numpy()
    phil_mask = (df["group"] == "philosophy").to_numpy()
    self_mask = (df["group"] == "selfhelp").to_numpy()
    canon_idx = np.where(canon_mask)[0]
    self_idx = np.where(self_mask)[0]

    # ---- 1. Repackaging index ----
    # cosine sims selfhelp x canon (embeddings normalized -> dot product)
    S = E[self_idx] @ E[canon_idx].T
    best_sim = S.max(axis=1)
    best_j = S.argmax(axis=1)
    df_self = df.iloc[self_idx].copy().reset_index(drop=True)
    df_self["best_canon_sim"] = best_sim
    df_self["best_canon_passage_id"] = df.iloc[canon_idx[best_j]]["passage_id"].to_numpy()

    repack = {}
    for book in SELFBOOKS:
        b = df_self[df_self["work"] == book]
        sims = b["best_canon_sim"].to_numpy()
        repack[book] = {
            "n": int(len(b)),
            "mean_best_sim": float(sims.mean()),
            "p50": float(np.median(sims)),
            # calibrated on hand-read pairs: >=0.60 = same idea reworded;
            # >=0.70 = close paraphrase or direct quotation
            "paraphrase_rate_060": float((sims >= 0.60).mean()),
            "quotation_rate_070": float((sims >= 0.70).mean()),
            "title": b["title"].iloc[0],
            "year": int(b["year"].iloc[0]),
        }
    print(json.dumps(repack, indent=2))

    # calibration sample: pairs at sim bands for threshold sanity
    calib = []
    for lo, hi in [(0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 0.75), (0.75, 1.01)]:
        m = (best_sim >= lo) & (best_sim < hi)
        ii = np.where(m)[0][:4]
        for k in ii:
            a = df_self.iloc[k]
            c = df.iloc[canon_idx[best_j[k]]]
            calib.append({"band": f"{lo}-{hi}", "sim": round(float(best_sim[k]), 3),
                          "self": a["passage"][:280], "self_work": a["work"],
                          "canon": c["passage"][:280], "canon_work": c["work"]})
    with open(os.path.join(DATA, "calibration_pairs.json"), "w") as f:
        json.dump(calib, f, indent=2)

    # ---- 2. Pair mining: mutual top-5 cross pairs, selfhelp -> canon ----
    # for each selfhelp passage take top-5 canon neighbors; keep pairs where
    # the selfhelp passage is also in the canon passage's top-5 selfhelp neighbors
    S_top5 = np.argpartition(-S, 5, axis=1)[:, :5]
    S2 = E[canon_idx] @ E[self_idx].T
    S2_top5 = np.argpartition(-S2, 5, axis=1)[:, :5]
    pairs = []
    for si in range(len(self_idx)):
        for cj in S_top5[si]:
            if si in S2_top5[cj]:
                a = df_self.iloc[si]
                c = df.iloc[canon_idx[cj]]
                pairs.append({"sim": float(S[si, cj]),
                              "self_passage": a["passage"], "self_work": a["work"],
                              "self_id": a["passage_id"],
                              "canon_passage": c["passage"], "canon_work": c["work"],
                              "canon_id": c["passage_id"]})
    pairs.sort(key=lambda d: -d["sim"])
    # dedupe near-identical self passages, keep top 60 candidates for hand review
    seen, cand = set(), []
    for p in pairs:
        key = (p["self_work"], p["self_passage"][:60])
        if key in seen:
            continue
        seen.add(key)
        cand.append(p)
        if len(cand) >= 60:
            break
    with open(os.path.join(DATA, "pair_candidates.json"), "w") as f:
        json.dump(cand, f, indent=2)
    print(f"{len(pairs)} mutual pairs, {len(cand)} candidates")

    # ---- 2b. Resonance: the universal core ----
    # For each canon passage, count distinct traditions (excluding its own work)
    # with at least one passage at sim >= 0.55. High resonance = the idea
    # shows up independently across civilizations.
    canon_trad = df.iloc[canon_idx]["tradition"].to_numpy()
    canon_work = df.iloc[canon_idx]["work"].to_numpy()
    Scc = E[canon_idx] @ E[canon_idx].T
    np.fill_diagonal(Scc, -1)
    reso_rows = []
    for i in range(len(canon_idx)):
        hit = Scc[i] >= 0.55
        trads = set(canon_trad[hit]) - {canon_trad[i]}
        works = set(canon_work[hit]) - {canon_work[i]}
        reso_rows.append({"passage_id": df.iloc[canon_idx[i]]["passage_id"],
                          "work": canon_work[i], "tradition": canon_trad[i],
                          "n_traditions": len(trads), "n_works": len(works),
                          "passage": df.iloc[canon_idx[i]]["passage"][:400]})
    reso = pd.DataFrame(reso_rows)
    reso.sort_values(["n_traditions", "n_works"], ascending=False, inplace=True)
    reso.to_csv(os.path.join(DATA, "resonance.csv"), index=False)
    core = reso[reso["n_traditions"] >= 5]
    print(f"universal core passages (>=5 traditions resonating): {len(core)}")
    print(core[["work", "n_traditions", "n_works"]].head(12).to_string())

    # ---- 3. Clustering ----
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    k = 30
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(E)
    df["cluster"] = labels

    tv = TfidfVectorizer(max_features=20000, ngram_range=(1, 2), stop_words="english",
                         min_df=5, sublinear_tf=True)
    T = tv.fit_transform(clean_for_embed(texts))
    terms = np.array(tv.get_feature_names_out())
    clusters = []
    for c in range(k):
        m = labels == c
        idx = np.where(m)[0]
        trads = Counter(df.iloc[idx]["tradition"])
        groups = Counter(df.iloc[idx]["group"])
        # top terms by mean tfidf within cluster
        mean_tfidf = np.asarray(T[idx].mean(axis=0)).ravel()
        top_terms = terms[np.argsort(-mean_tfidf)[:8]].tolist()
        # representative passage: closest to centroid
        centroid = E[idx].mean(axis=0)
        rep = idx[np.argmax(E[idx] @ centroid)]
        clusters.append({
            "cluster": c, "size": int(m.sum()),
            "top_terms": top_terms,
            "traditions": dict(trads), "groups": dict(groups),
            "canon_share": float((df.iloc[idx]["group"] == "canon").mean()),
            "selfhelp_share": float((df.iloc[idx]["group"] == "selfhelp").mean()),
            "n_traditions": len(trads),
            "rep_passage": df.iloc[rep]["passage"][:300],
            "rep_work": df.iloc[rep]["work"],
        })
    clusters.sort(key=lambda d: -d["size"])
    with open(os.path.join(DATA, "clusters.json"), "w") as f:
        json.dump(clusters, f, indent=2)
    df[["passage_id", "work", "cluster"]].to_csv(os.path.join(DATA, "clusters.csv"), index=False)

    universal = [c for c in clusters if c["n_traditions"] >= 6 and c["canon_share"] >= 0.4]
    whitespace = [c for c in clusters if c["canon_share"] >= 0.65 and c["selfhelp_share"] <= 0.05 and c["size"] >= 60]
    industry = [c for c in clusters if c["selfhelp_share"] >= 0.65 and c["size"] >= 60]
    print(f"universal: {len(universal)}, whitespace: {len(whitespace)}, industry-only: {len(industry)}")

    # ---- 4. UMAP ----
    umap_ok = False
    try:
        import umap
        red = umap.UMAP(n_components=2, random_state=42, n_neighbors=30,
                        min_dist=0.3, metric="cosine").fit_transform(E)
        umap_ok = True
        np.savez_compressed(os.path.join(DATA, "umap2d.npz"), xy=red)
        print("umap done", red.shape)
    except ImportError:
        print("umap not installed; skipping projection")

    results = {
        "backend": args.backend, "n_passages": n,
        "repackaging": repack,
        "n_universal_clusters": len(universal),
        "n_whitespace_clusters": len(whitespace),
        "n_industry_clusters": len(industry),
        "umap": umap_ok,
    }
    with open(os.path.join(DATA, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("results.json written")

if __name__ == "__main__":
    main()
