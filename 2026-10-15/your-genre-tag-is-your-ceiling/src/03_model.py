"""Model: what gets a genre-chart track into the overall Top 100?

Target: in_main (100 of 1,700 unique charting tracks).
Three nested XGBoost classifiers show where the signal lives:
  A. track-only   — bpm, length, age, artist count, remixer, format, key
  B. + shelf      — the track's single genre tag (one-hot)
  C. + incumbency — the artists' and label's OTHER charting tracks today
                    (computed excluding the track itself, so the target
                    track never leaks into its own features), and the lead
                    artist's cross-genre spread across their other tracks.

SHAP (TreeExplainer) on model C. Writes data/model.json and
data/shap_importance.csv. AUCs are 75/25 stratified holdout, seed fixed.
Snapshot-internal caveat: incumbency is measured on the same day's charts —
it answers 'who else is hot today', not a causal claim.
"""
import json, os
from collections import Counter

import numpy as np
import pandas as pd
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def build_features(T):
    T = T.copy()
    T["artist_list"] = T.artists.str.split("; ")
    # per-artist counters over the whole snapshot, then subtract this track
    artist_tracks = Counter(a for ns in T.artist_list for a in ns)
    artist_genres = {}
    for _, r in T.iterrows():
        for a in r.artist_list:
            artist_genres.setdefault(a, Counter())[r.genre_slug] += 1
    label_tracks = T.label.value_counts().to_dict()

    def feats(r):
        others, spreads = [], []
        for a in r.artist_list:
            others.append(artist_tracks[a] - 1)
            g = artist_genres[a].copy()
            g[r.genre_slug] -= 1
            spreads.append(len([k for k, v in g.items() if v > 0]))
        return pd.Series({
            "artist_other_tracks": max(others) if others else 0,
            "artist_other_genres": max(spreads) if spreads else 0,
            "label_other_tracks": label_tracks[r.label] - 1,
        })

    F = T.apply(feats, axis=1)
    T = pd.concat([T, F], axis=1)
    T["minor"] = (T.key_mode == "Minor").astype(int)
    return T


def run(feats, T, label):
    X = pd.get_dummies(T[feats], columns=["genre_slug"] if "genre_slug" in feats
                       else [], dtype=float)
    y = T.in_main.astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25,
                                          random_state=7, stratify=y)
    clf = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.06,
                        subsample=0.9, colsample_bytree=0.9,
                        eval_metric="logloss")
    clf.fit(Xtr, ytr)
    auc = roc_auc_score(yte, clf.predict_proba(Xte)[:, 1])
    print(f"{label}: AUC {auc:.3f}  ({X.shape[1]} features)")
    return clf, X, auc


def main():
    T = pd.read_csv(os.path.join(DATA, "tracks.csv"))
    T = build_features(T)
    base = ["bpm", "len_min", "age_days", "n_artists", "has_remixer",
            "extended", "explicit", "minor", "price_usd"]
    T["has_remixer"] = T.has_remixer.astype(int) if T.has_remixer.dtype != int \
        else T.has_remixer
    T["extended"] = T.extended.astype(int)
    T["explicit"] = T.explicit.astype(int)
    ladder = {}
    _, _, a = run(base, T, "A track-only")
    ladder["track_only_auc"] = round(a, 3)
    _, _, a = run(base + ["genre_slug"], T, "B +shelf")
    ladder["plus_shelf_auc"] = round(a, 3)
    full_feats = base + ["genre_slug", "artist_other_tracks",
                         "artist_other_genres", "label_other_tracks"]
    clf, X, a = run(full_feats, T, "C +incumbency")
    ladder["full_auc"] = round(a, 3)

    explainer = shap.TreeExplainer(clf)
    sv = explainer.shap_values(X)
    imp = pd.Series(np.abs(sv).mean(axis=0), index=X.columns)
    # fold one-hot shelf dummies back into one 'genre shelf' importance
    shelf_cols = [c for c in imp.index if c.startswith("genre_slug_")]
    shelf_total = float(imp[shelf_cols].sum())
    imp = imp.drop(shelf_cols)
    imp["genre_shelf (all 17 tags)"] = shelf_total
    imp = imp.sort_values(ascending=False)
    imp.to_csv(os.path.join(DATA, "shap_importance.csv"),
               header=["mean_abs_shap"])
    ladder["shap_top"] = {k: round(float(v), 3) for k, v in imp.head(10).items()}
    ladder["n_tracks"] = int(len(T))
    ladder["n_positive"] = int(T.in_main.sum())
    with open(os.path.join(DATA, "model.json"), "w") as f:
        json.dump(ladder, f, indent=2)
    print(json.dumps(ladder, indent=2))


if __name__ == "__main__":
    main()
