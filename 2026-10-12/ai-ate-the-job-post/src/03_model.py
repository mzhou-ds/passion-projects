"""Two models:
1. TF-IDF + KMeans (k=6) over hiring posts -> posting archetypes, tracked by era.
2. XGBoost + SHAP predicting whether a post is an AI post from structural
   features (stack, remote, location, salary, seniority) -- what *else*
   changed about AI postings beyond the label. Logistic baseline for AUC.
"""
import json
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier
import shap, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def main():
    df = pd.read_csv("data/posts_hiring_classified.csv")
    # --- clustering on post-2022 posts (enough AI density to separate) ---
    recent = df[df["thread_date"] >= "2023-01-01"].copy()
    vec = TfidfVectorizer(max_features=3000, stop_words="english", min_df=10)
    X = vec.fit_transform(recent["text"].fillna(""))
    km = KMeans(n_clusters=6, n_init=10, random_state=7).fit(X)
    recent["cluster"] = km.labels_
    words = np.array(vec.get_feature_names_out())
    clusters = {}
    for c in range(6):
        top = words[km.cluster_centers_[c].argsort()[::-1][:10]]
        sub = recent[recent.cluster == c]
        clusters[str(c)] = {"top_words": list(top), "n": int(len(sub)),
                            "ai_share": float(sub["is_ai"].mean()),
                            "remote_share": float(sub["remote"].mean()),
                            "sal_median": float(sub["sal_mid"].median())}
    recent.to_csv("data/posts_clustered.csv", index=False)

    # --- XGBoost: is this an AI post? ---
    feats = [c for c in df.columns if c.startswith(("stk_", "role_"))] + \
            ["remote", "sf_bay", "nyc", "founding", "senior_plus", "sal_disclosed", "n_words"]
    d = df.dropna(subset=["is_ai"]).copy()
    d["sal_mid_f"] = d["sal_mid"].fillna(d["sal_mid"].median())
    Xf = d[feats + ["sal_mid_f"]]
    Xtr, Xte, ytr, yte = train_test_split(Xf, d["is_ai"], test_size=0.25, random_state=7, stratify=d["is_ai"])
    lr = LogisticRegression(max_iter=1000).fit(Xtr, ytr)
    auc_lr = roc_auc_score(yte, lr.predict_proba(Xte)[:, 1])
    xgb = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.06,
                        subsample=0.9, colsample_bytree=0.9, eval_metric="logloss")
    xgb.fit(Xtr, ytr)
    auc_xgb = roc_auc_score(yte, xgb.predict_proba(Xte)[:, 1])
    expl = shap.TreeExplainer(xgb)
    sv = expl.shap_values(Xte)
    plt.figure(figsize=(8, 5))
    shap.summary_plot(sv, Xte, show=False, max_display=15)
    plt.tight_layout(); plt.savefig("charts/shap_ai_post.png", dpi=150); plt.close()
    out = {"auc_xgboost": float(auc_xgb), "auc_logistic": float(auc_lr),
           "clusters": clusters, "n_recent_clustered": int(len(recent))}
    json.dump(out, open("data/model.json", "w"), indent=2)
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
