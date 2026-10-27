"""XGBoost + SHAP: what actually predicts exercising alone?

Episode-level model on fitness episodes (data/episodes.parquet, built by
analyze.py). Target: the episode was done alone. Features are things a gym,
an app, or a friend could in principle know in advance: when, where, what
activity, who the person is. Duration is deliberately excluded — it is partly
an outcome of company, not a predictor you can act on beforehand.
"""
import json
import pathlib

import numpy as np
import pandas as pd
import shap
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

TOP_CODES = [130131, 130134, 130104, 130124, 130133, 130128, 130132, 130116,
             130101, 130136, 130109]


def main():
    ex = pd.read_parquet(ROOT / "data" / "episodes.parquet")
    fit = ex[ex["set"] == "fitness"].dropna(subset=["alone"]).copy()
    fit["sex_f"] = (fit["TESEX"] == 2).astype(int)
    fit["age"] = fit["TEAGE"]
    fit["code_top"] = np.where(fit["TRCODE"].isin(TOP_CODES), fit["TRCODE"], 0)
    X = pd.get_dummies(fit[["TUYEAR", "hour", "weekend", "age", "sex_f",
                            "at_home", "at_gym", "code_top"]].astype(
                                {"weekend": int, "at_home": int, "at_gym": int}),
                       columns=["code_top"], prefix="code")
    y = fit["alone"].astype(int)
    w = fit["TUFINLWGT"]
    Xtr, Xte, ytr, yte, wtr, wte = train_test_split(
        X, y, w, test_size=0.25, random_state=7)
    m = XGBClassifier(n_estimators=400, max_depth=3, learning_rate=0.06,
                      subsample=0.9, colsample_bytree=0.9, n_jobs=8,
                      eval_metric="logloss")
    m.fit(Xtr, ytr, sample_weight=wtr)
    auc = float(roc_auc_score(yte, m.predict_proba(Xte)[:, 1], sample_weight=wte))
    expl = shap.TreeExplainer(m)
    sv = expl.shap_values(Xte.iloc[:4000])
    imp = pd.Series(np.abs(sv).mean(axis=0), index=X.columns).sort_values(ascending=False)
    res = {"auc_test": auc, "n_episodes": int(len(fit)),
           "shap_mean_abs": {k: float(v) for k, v in imp.items()}}
    (OUT / "model.json").write_text(json.dumps(res, indent=1))
    imp.rename("mean_abs_shap").to_csv(OUT / "shap_importance.csv")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
