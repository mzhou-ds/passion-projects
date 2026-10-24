#!/usr/bin/env python3
"""
04_model.py — Two XGBoost + SHAP models.

A) Can you date a dance track from its preview audio alone?
   Binary: pre-2010 vs 2020-26 dance previews, features from 03_audio.
   If the intro really died, audio structure should carry the era —
   and SHAP should point at the intro features, not loudness.

B) What predicts a long (>= 5:30) cut in the full catalog?
   All panels, features: era, panel, version tag, remix flag, and
   stem-level context (does a short sibling exist?). SHAP ranks the
   levers; the question is whether the version tag system or the
   calendar does the work.

Outputs: data/model_stats.json (+ SHAP summary CSVs for charting)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import shap
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parent.parent
OUT = {"models": {}}


def shap_table(model, X: pd.DataFrame) -> pd.DataFrame:
    expl = shap.TreeExplainer(model)
    vals = np.abs(expl.shap_values(X)).mean(axis=0)
    return (
        pd.DataFrame({"feature": X.columns, "mean_abs_shap": vals})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------- A: audio era
# Among LONG dance cuts only: can the preview's spectral shape date the
# track (pre-2010 vs 2020-26)? If the DJ intro died inside the long cut,
# brightness/darkness features should carry the era.
pf = pd.read_csv(ROOT / "data" / "preview_features.csv")
a = pf[(pf["panel_query"] == "dance") & (pf["bucket"] == "long")
       & (pf["coarse"].isin(["pre2010", "2020s"]))].copy()
a["y"] = (a["coarse"] == "2020s").astype(int)
feats_a = ["cent_first3", "cent_mean", "cent_last5", "cent_rise",
           "dark_share_10", "dark_share_30", "lf_share_mean",
           "rms_cv_10", "rms_slope_15", "rms_first3_share", "seconds"]
Xa = a[feats_a].fillna(a[feats_a].median())
Xtr, Xte, ytr, yte = train_test_split(Xa, a["y"], test_size=0.3, random_state=7, stratify=a["y"])
ma = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05,
                   subsample=0.9, colsample_bytree=0.9, eval_metric="logloss")
ma.fit(Xtr, ytr)
auc_a = roc_auc_score(yte, ma.predict_proba(Xte)[:, 1])
tab_a = shap_table(ma, Xa)
tab_a.to_csv(ROOT / "data" / "shap_audio_era.csv", index=False)
OUT["models"]["audio_era"] = {
    "n": int(len(a)), "auc_heldout": round(float(auc_a), 3),
    "shap": tab_a.to_dict("records"),
}
print(f"[A] audio->era AUC {auc_a:.3f} (n={len(a)})")
print(tab_a.to_string(index=False))

# ---------------------------------------------------------------- B: long cut
df = pd.read_csv(ROOT / "data" / "tracks_clean.csv")
stems = pd.read_csv(ROOT / "data" / "stems.csv")[["stem", "n_versions", "spread_s", "multi"]]
df = df.merge(stems, on="stem", how="left")
df["y"] = (df["seconds"] >= 330).astype(int)
df["is_remix_tag"] = (df["version"] == "remix").astype(int)
df["is_extended_tag"] = (df["version"] == "extended").astype(int)
df["is_radio_tag"] = (df["version"] == "radio_edit").astype(int)
df["is_club_tag"] = (df["version"] == "club").astype(int)
df["collection_is_remix_pkg"] = df["collection"].str.lower().str.contains("remix").astype(int)
Xb = pd.get_dummies(
    df[["year", "panel_query", "is_remix_tag", "is_extended_tag", "is_radio_tag",
        "is_club_tag", "collection_is_remix_pkg", "n_versions", "spread_s", "multi"]],
    columns=["panel_query"],
)
Xb["multi"] = Xb["multi"].astype(int)
Xb = Xb.fillna(0)
Xtr, Xte, ytr, yte = train_test_split(Xb, df["y"], test_size=0.3, random_state=7, stratify=df["y"])
mb = XGBClassifier(n_estimators=400, max_depth=4, learning_rate=0.05,
                   subsample=0.9, colsample_bytree=0.9, eval_metric="logloss")
mb.fit(Xtr, ytr)
auc_b = roc_auc_score(yte, mb.predict_proba(Xte)[:, 1])
tab_b = shap_table(mb, Xb)
tab_b.to_csv(ROOT / "data" / "shap_long_cut.csv", index=False)
OUT["models"]["long_cut"] = {
    "n": int(len(df)), "base_rate_long": round(float(df["y"].mean()), 4),
    "auc_heldout": round(float(auc_b), 3),
    "shap": tab_b.to_dict("records"),
}
print(f"[B] long-cut AUC {auc_b:.3f} (n={len(df)}, base rate {df['y'].mean():.1%})")
print(tab_b.to_string(index=False))

(ROOT / "data" / "model_stats.json").write_text(json.dumps(OUT, indent=2, default=str))
