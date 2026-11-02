"""XGBoost: who has a zero-friend day, and who has a zero-family day (contrast).

One diary day per respondent, so a random split is a respondent split.
Features are respondent-level only (no episode info, so nothing leaks the
outcome): age, sex, weekend diary, usual weekly work hours, kids in household,
household size, spouse present in household, labor-force status, era.
Target: zero minutes with friends (family for the contrast model).
SHAP mean |value| ranks the sorters. Survey weights used in fitting.
"""
import json, pathlib
import numpy as np, pandas as pd
import xgboost as xgb, shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

ROOT = pathlib.Path(__file__).resolve().parent.parent
day = pd.read_parquet(ROOT / "data/respondent_day.parquet")
day["work_hrs"] = day["TEHRUSL1"].where(day["TEHRUSL1"] >= 0)
day["zero_friend"] = (day["friend_min"] == 0).astype(int)
day["zero_family"] = (day["family_min"] == 0).astype(int)
feats = ["TEAGE", "TESEX", "weekend", "work_hrs", "has_kids_hh", "spouse_in_hh",
         "TRNUMHOU", "TELFS", "era"]
X = pd.get_dummies(day[feats].copy(), columns=["TELFS", "era"], drop_first=False)
X["weekend"] = X["weekend"].astype(int); X["has_kids_hh"] = X["has_kids_hh"].astype(int)
X["spouse_in_hh"] = X["spouse_in_hh"].astype(int)
for c in X.columns: X[c] = pd.to_numeric(X[c], errors="coerce")
out = {}
for target in ["zero_friend", "zero_family"]:
    Xtr, Xte, ytr, yte, wtr, wte = train_test_split(
        X, day[target], day["TUFINLWGT"], test_size=0.25, random_state=7)
    m = xgb.XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.06,
        subsample=0.8, colsample_bytree=0.8, eval_metric="logloss", n_jobs=-1)
    m.fit(Xtr, ytr, sample_weight=wtr)
    pred = m.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(yte, pred, sample_weight=wte)
    ex = shap.TreeExplainer(m)
    sv = ex.shap_values(Xte.iloc[:4000])
    imp = sorted(((c, float(np.abs(sv[:, i]).mean())) for i, c in enumerate(Xte.columns)),
                 key=lambda t: -t[1])
    out[target] = {"auc": round(float(auc), 3), "base_rate": round(float(ytr.mean()), 3),
                   "shap": [{"feature": c, "mean_abs_shap": round(v, 4)} for c, v in imp]}
    print(target, "AUC", out[target]["auc"], "top:", imp[:6])
json.dump(out, open(ROOT / "data/model.json", "w"), indent=1)
