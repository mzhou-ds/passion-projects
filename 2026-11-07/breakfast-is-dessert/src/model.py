"""Classifier for build #61: can nutrients tell a breakfast occasion from
a snack occasion? Train/test split by person (no leakage across a
person's occasions). XGBoost + logistic regression; SHAP on the XGBoost.
"""
import json
import os
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "output")


def main():
    occ = pd.read_parquet(os.path.join(DATA, "occasions.parquet"))
    a1 = occ[(occ["day"] == 1) & (occ["reliable"] == 1)
             & (occ["age"] >= 20) & (occ["age"] <= 79)
             & (occ["day_kcal"] >= 500) & (occ["day_kcal"] <= 6000)
             & (occ["WTDRD1"] > 0)
             & (occ["meal"].isin(["breakfast", "snack"]))].copy()
    a1["y"] = (a1["meal"] == "breakfast").astype(int)
    a1["fat_share"] = a1["fat"] * 9.0 / a1["kcal"]
    a1["carb_share"] = a1["carb"] * 4.0 / a1["kcal"]
    a1["sodium_per_100kcal"] = a1["sodium"] / a1["kcal"] * 100.0
    a1["caffeine_per_100kcal"] = a1["caffeine"] / a1["kcal"] * 100.0
    a1["log_kcal"] = np.log(a1["kcal"])
    # Ratio features blow up on near-zero-kcal occasions (a spoon of sugar
    # in black coffee). Sugar density cannot exceed 25 g/100 kcal (4 kcal/g);
    # clip every per-100-kcal feature at a physical/plausible ceiling.
    for c, cap in [("sugar_per_100kcal", 25.0), ("fiber_per_100kcal", 50.0),
                   ("sodium_per_100kcal", 20000.0),
                   ("caffeine_per_100kcal", 5000.0)]:
        a1[c] = a1[c].replace([np.inf, -np.inf], np.nan).clip(0, cap)
    a1["prot_share"] = a1["prot_share"].clip(0, 1)
    a1["fat_share"] = a1["fat_share"].clip(0, 1)
    a1["carb_share"] = a1["carb_share"].clip(0, 1)
    feats = ["sugar_per_100kcal", "prot_share", "fat_share", "carb_share",
             "fiber_per_100kcal", "sodium_per_100kcal",
             "caffeine_per_100kcal", "log_kcal", "t_h", "n_items"]
    X = a1[feats].fillna(0).to_numpy()
    y = a1["y"].to_numpy()
    w = a1["WTDRD1"].to_numpy()
    gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=7)
    tr, te = next(gss.split(X, y, groups=a1["SEQN"].to_numpy()))
    res = {"n_breakfast": int((a1["y"] == 1).sum()),
           "n_snack": int((a1["y"] == 0).sum())}

    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    lr.fit(X[tr], y[tr], logisticregression__sample_weight=w[tr])
    p_lr = lr.predict_proba(X[te])[:, 1]
    res["logreg_auc"] = float(roc_auc_score(y[te], p_lr, sample_weight=w[te]))

    clf = xgb.XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8,
                            random_state=7, n_jobs=-1)
    clf.fit(X[tr], y[tr], sample_weight=w[tr])
    p_xgb = clf.predict_proba(X[te])[:, 1]
    res["xgb_auc"] = float(roc_auc_score(y[te], p_xgb, sample_weight=w[te]))
    # nutrients only (no clock time, no size): is the composition alone enough?
    nutr = ["sugar_per_100kcal", "prot_share", "fat_share", "carb_share",
            "fiber_per_100kcal", "sodium_per_100kcal", "caffeine_per_100kcal"]
    idx = [feats.index(f) for f in nutr]
    clf2 = xgb.XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                             subsample=0.8, colsample_bytree=0.8,
                             random_state=7, n_jobs=-1)
    clf2.fit(X[tr][:, idx], y[tr], sample_weight=w[tr])
    p2 = clf2.predict_proba(X[te][:, idx])[:, 1]
    res["xgb_nutrients_only_auc"] = float(
        roc_auc_score(y[te], p2, sample_weight=w[te]))

    # SHAP on the nutrients-only model (test sample, capped)
    import shap
    te_idx = te[:4000]
    ex = shap.TreeExplainer(clf2)
    sv = ex.shap_values(X[te_idx][:, idx])
    mean_abs = np.abs(sv).mean(axis=0)
    res["shap_nutrients_only"] = [
        {"feature": f, "mean_abs_shap": float(v)}
        for f, v in sorted(zip(nutr, mean_abs), key=lambda t: -t[1])]
    # direction: mean SHAP value by feature sign vs sugar
    res["shap_sugar_direction"] = float(
        np.corrcoef(X[te_idx][:, idx][:, 0], sv[:, 0])[0, 1])

    # single-feature AUCs: which one nutrient separates best?
    res["single_feature_auc"] = {}
    for j, f in enumerate(feats):
        try:
            res["single_feature_auc"][f] = float(
                roc_auc_score(y[te], X[te][:, j], sample_weight=w[te]))
        except ValueError:
            pass

    with open(os.path.join(OUT, "model.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(json.dumps(res, indent=2, default=float))


if __name__ == "__main__":
    main()
