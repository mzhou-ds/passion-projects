"""XGBoost + SHAP: who has an unstable eating clock?

Target: absolute calorie-midpoint shift between the two recall days (hours).
Features are all person-level or day-pair-level, known before either day's
timing is observed in a study design sense: demographics, BMI, cycle, the
weekday/weekend composition of the pair, and the person's average level
(midpoint, window, kcal) across the two days.
"""
import json
import os
import numpy as np
import pandas as pd
import shap
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

FEATS = ["RIDAGEYR", "RIAGENDR", "RIDRETH1", "DMDEDUC2", "DMDMARTL",
         "INDFMPIR", "BMXBMI", "mean_mid", "mean_window", "mean_kcal",
         "mean_after20", "pair_mixed", "pair_weekend", "cycle_idx"]


def main():
    pairs = pd.read_parquet(os.path.join(ROOT, "data", "pairs_enriched.parquet"))
    pairs["mean_mid"] = (pairs["mid_h_1"] + pairs["mid_h_2"]) / 2
    pairs["mean_window"] = (pairs["window_h_1"] + pairs["window_h_2"]) / 2
    pairs["mean_kcal"] = (pairs["kcal_1"] + pairs["kcal_2"]) / 2
    pairs["mean_after20"] = (pairs["after20_1"] + pairs["after20_2"]) / 2
    pairs["pair_mixed"] = (pairs["pair_type"] == "mixed").astype(int)
    pairs["pair_weekend"] = (pairs["pair_type"] == "both_weekend").astype(int)
    pairs["cycle_idx"] = pairs["cycle"].str[:4].astype(int)
    df = pairs.dropna(subset=FEATS + ["abs_shift_mid"]).copy()
    X, y = df[FEATS], df["abs_shift_mid"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=52)
    m = XGBRegressor(n_estimators=500, max_depth=3, learning_rate=0.05,
                     subsample=0.9, colsample_bytree=0.9, random_state=52)
    m.fit(Xtr, ytr)
    pred = m.predict(Xte)
    ss_res = float(np.sum((yte - pred) ** 2))
    ss_tot = float(np.sum((yte - yte.mean()) ** 2))
    out = {"n_model": int(len(df)), "r2_test": 1 - ss_res / ss_tot,
           "mae_test_h": float(np.mean(np.abs(yte - pred))),
           "baseline_mae_h": float(np.mean(np.abs(yte - ytr.median())))}
    expl = shap.TreeExplainer(m)
    sv = expl.shap_values(Xte)
    imp = (pd.DataFrame({"feature": FEATS,
                         "mean_abs_shap_h": np.abs(sv).mean(axis=0)})
           .sort_values("mean_abs_shap_h", ascending=False))
    imp.to_csv(os.path.join(ROOT, "output", "shap_importance.csv"), index=False)
    out["shap_top"] = imp.head(8).to_dict("records")
    with open(os.path.join(ROOT, "output", "model.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
