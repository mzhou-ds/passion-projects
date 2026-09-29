"""Embed Confucius leadership passages + modern management statements (Oxygen 8, Q12),
measure rediscovery: how much of modern people-science did Confucius already say?

Backend: --backend minilm (sentence-transformers, preferred) or lsa (offline TF-IDF/SVD).
Outputs: data/scores_*.json, data/pairs_topk.json
"""
import argparse, csv, json, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DATA = os.path.join(PROJ, "data")

def load_tsv(path):
    return list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"))

def embed_lsa(texts, n_comp=256):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import normalize
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.9,
                          stop_words="english", sublinear_tf=True)
    X = vec.fit_transform(texts)
    k = min(n_comp, X.shape[0] - 1, X.shape[1] - 1)
    svd = TruncatedSVD(n_components=k, random_state=42)
    return normalize(svd.fit_transform(X))

def embed_minilm(texts):
    from sentence_transformers import SentenceTransformer
    from sklearn.preprocessing import normalize
    m = SentenceTransformer("/home/hatch/workspace/models/all-MiniLM-L6-v2")
    return normalize(m.encode(texts, show_progress_bar=False))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="minilm", choices=["minilm", "lsa"])
    args = ap.parse_args()

    lead = load_tsv(os.path.join(DATA, "leadership.tsv"))
    allp = load_tsv(os.path.join(DATA, "all_passages.tsv"))
    lead_ids = {r["passage_id"] for r in lead}
    nonlead = [r for r in allp if r["passage_id"] not in lead_ids]
    modern = load_tsv(os.path.join(DATA, "modern.tsv"))

    texts = [r["text"] for r in lead] + [r["text"] for r in nonlead] + [r["text"] for r in modern]
    n_lead, n_non = len(lead), len(nonlead)
    E = (embed_minilm if args.backend == "minilm" else embed_lsa)(texts)
    El, En, Em = E[:n_lead], E[n_lead:n_lead+n_non], E[n_lead+n_non:]

    cos = lambda A, B: A @ B.T
    S_lead = cos(Em, El)      # modern x leadership
    S_non = cos(Em, En)       # modern x non-leadership (baseline)

    out = {"backend": args.backend, "modern": []}
    for j, m in enumerate(modern):
        s = S_lead[j]
        order = np.argsort(-s)
        best = int(order[0])
        base = float(np.max(S_non[j]))
        out["modern"].append({
            "id": m["id"], "shelf": m["shelf"], "label": m["label"],
            "text": m["text"],
            "best_score": float(s[best]),
            "baseline_score": base,
            "margin": float(s[best]) - base,
            "top3": [
                {"passage_id": lead[k]["passage_id"], "book": lead[k]["book"],
                 "chap": lead[k]["chap"], "theme": lead[k]["theme"],
                 "label": lead[k]["label"], "text": lead[k]["text"],
                 "score": float(s[k])}
                for k in order[:3]],
        })

    # Reverse direction: leadership passages with no strong modern match
    S_rev = S_lead.T
    rev = []
    for i, r in enumerate(lead):
        k = int(np.argmax(S_rev[i]))
        rev.append({"passage_id": r["passage_id"], "book": r["book"], "chap": r["chap"],
                    "theme": r["theme"], "label": r["label"], "text": r["text"],
                    "best_modern": modern[k]["label"], "best_modern_id": modern[k]["id"],
                    "score": float(S_rev[i][k])})
    rev.sort(key=lambda d: d["score"])
    out["reverse"] = rev
    json.dump(out, open(os.path.join(DATA, "scores_%s.json" % args.backend), "w"),
              indent=1, ensure_ascii=False)
    print("backend=%s wrote scores for %d modern items, %d leadership passages"
          % (args.backend, len(modern), len(lead)))

if __name__ == "__main__":
    main()
