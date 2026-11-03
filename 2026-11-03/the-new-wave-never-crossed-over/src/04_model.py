"""Step 4: cluster release strategies and model who still releases.

Both pieces are deliberately small-n and reported as such (32 artists):
1. KMeans (k=4) on per-artist release-strategy features -> named clusters.
2. XGBoost regressor predicting recent (2023-25) singles+EPs per year
   from career features, 5-fold CV R^2, with SHAP importances.
"""

import json

import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.cluster import KMeans
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

S = "data/artist_summary.csv"
FEATS = ["career_age_2025", "lifetime_single_ep", "single_share",
         "collab_share", "pop_share", "peak_year_output"]


def main():
    s = pd.read_csv(S)
    X = s[FEATS].fillna(s[FEATS].median())
    Xs = StandardScaler().fit_transform(X)
    km = KMeans(n_clusters=4, n_init=20, random_state=7).fit(Xs)
    s["cluster"] = km.labels_
    prof = s.groupby("cluster")[["lifetime_single_ep", "recent_rate",
                                 "single_share", "collab_share",
                                 "pop_share"]].mean()
    print(prof.round(2))
    names = {}
    for c, row in prof.iterrows():
        if row["pop_share"] > 0.3:
            names[c] = "pop crossovers"
        elif row["lifetime_single_ep"] > 150 and row["recent_rate"] > 12:
            names[c] = "catalog engines"
        elif row["lifetime_single_ep"] < 60 and row["recent_rate"] < 5:
            names[c] = "quiet craftsmen"
        else:
            names[c] = "single machines"
    s["cluster_name"] = s["cluster"].map(names)
    print(s[["artist", "cohort", "cluster_name", "recent_rate",
             "lifetime_single_ep"]].to_string(index=False))
    s.to_csv(S, index=False)

    model = xgb.XGBRegressor(n_estimators=200, max_depth=3, learning_rate=0.05,
                             subsample=0.9, colsample_bytree=0.9,
                             random_state=7)
    scores = cross_val_score(model, X, s["recent_rate"], cv=5, scoring="r2")
    model.fit(X, s["recent_rate"])
    print(f"XGB CV R^2: mean {scores.mean():.2f}, folds {np.round(scores, 2)}")
    expl = shap.TreeExplainer(model)
    sv = expl.shap_values(X)
    imp = pd.Series(np.abs(sv).mean(axis=0), index=FEATS).sort_values()
    print(imp.round(3))
    imp.to_csv("data/shap_importance.csv")
    with open("data/model_summary.json", "w") as f:
        json.dump({"cv_r2_mean": float(scores.mean()),
                   "cv_r2_folds": [float(v) for v in scores],
                   "cluster_names": {str(k): v for k, v in names.items()},
                   "cluster_profiles": prof.round(2).to_dict("index")},
                  f, indent=2)


if __name__ == "__main__":
    main()
