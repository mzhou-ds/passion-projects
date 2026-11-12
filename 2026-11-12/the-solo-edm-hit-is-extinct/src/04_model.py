"""04_model.py — What actually predicts a top-40 EDM song?

Song-level XGBoost classifier: P(peak <= 40) from features known at debut —
debut year, billing type (solo vs collab, EDM-as-feature), number of credited
artists, and the lead artist's Hot 100 track record before that debut (prior
songs, prior top-40s). 192 songs is small, so: shallow trees, strong
regularization, 5-fold CV for the AUC, then a full-data fit for SHAP.

Question the model answers: once you know the year and the billing, does
anything about the artist still matter? If billing + year dominate, the chart
slot is a format decision, not a talent contest.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def main():
    songs = pd.read_csv(DATA / "edm_songs.csv", parse_dates=["debut"])
    songs = songs.sort_values("debut").reset_index(drop=True)

    # lead-artist track record BEFORE each debut (no leakage)
    prior_songs, prior_top40 = [], []
    seen = {}
    for _, r in songs.iterrows():
        a = r["lead_artist"]
        prior_songs.append(seen.get(a, (0, 0))[0])
        prior_top40.append(seen.get(a, (0, 0))[1])
        seen[a] = (seen.get(a, (0, 0))[0] + 1,
                   seen.get(a, (0, 0))[1] + int(r["top40"] == 1))
    songs["prior_songs"] = prior_songs
    songs["prior_top40"] = prior_top40

    songs["is_solo"] = (songs["edm_type"] == "solo").astype(int)
    songs["is_featured"] = (songs["edm_type"] == "edm_featured").astype(int)
    songs["is_edm_collab"] = (songs["edm_type"] == "edm_collab").astype(int)
    songs["era_toll_plus"] = (songs["debut_year"] >= 2015).astype(int)
    songs["era_remnant"] = (songs["debut_year"] >= 2021).astype(int)

    feats = ["debut_year", "is_solo", "is_featured", "is_edm_collab",
             "n_artists", "prior_songs", "prior_top40",
             "era_toll_plus", "era_remnant"]
    X = songs[feats]
    y = songs["top40"].astype(int)
    print(f"n={len(songs)}, base rate top-40 = {y.mean():.3f}")

    clf = xgb.XGBClassifier(
        n_estimators=200, max_depth=2, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0,
        min_child_weight=5, eval_metric="logloss", random_state=7)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=7)
    pred = cross_val_predict(clf, X, y, cv=cv, method="predict_proba")[:, 1]
    auc = roc_auc_score(y, pred)
    print(f"5-fold CV AUC (top-40): {auc:.3f}")

    clf.fit(X, y)
    expl = shap.TreeExplainer(clf)
    sv = expl.shap_values(X)
    mean_abs = np.abs(sv).mean(axis=0)
    order = np.argsort(-mean_abs)
    shap_rank = [{"feature": feats[i], "mean_abs_shap": round(float(mean_abs[i]), 4)}
                 for i in order]
    print("SHAP ranking:", shap_rank)

    # raw hit rates for the headline contrast
    rates = (songs.groupby("is_solo")["top40"].agg(["mean", "size"]).round(3))
    print(rates.to_string())

    out = {"n_songs": int(len(songs)), "base_rate_top40": round(float(y.mean()), 3),
           "cv_auc_top40": round(float(auc), 3), "features": feats,
           "shap_ranking": shap_rank,
           "top40_rate_solo": round(float(songs[songs["is_solo"] == 1]["top40"].mean()), 3),
           "top40_rate_collab": round(float(songs[songs["is_solo"] == 0]["top40"].mean()), 3),
           "n_solo": int(songs["is_solo"].sum()),
           "n_collab": int((1 - songs["is_solo"]).sum())}
    (DATA / "model.json").write_text(json.dumps(out, indent=1))
    np.save(DATA / "shap_values.npy", sv)
    songs[feats + ["top40", "peak", "title", "lead_artist"]].to_csv(
        DATA / "model_frame.csv", index=False)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
