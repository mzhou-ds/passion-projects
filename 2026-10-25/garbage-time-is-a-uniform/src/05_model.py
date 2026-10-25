"""Part 5: Two XGBoost models, read with SHAP.

Model A (the uniform model): predict a player's decided-goal share
next season from his own share this season, his team's share, his
NEXT team's share, and whether he switched. If 'garbage-time scorer'
were a trait, his own history would dominate. It does not.

Model B (the pay-for-it model): predict next season's goals per
attempt from this season's scoring split into decided / middle /
coin-flip goals per attempt plus xG per attempt. Shows which slice of
a scoring record carries signal about the next one.

Outputs: data/model_stats.json, data/shap_uniform.csv, data/shap_pay.csv
"""
import json
import os

import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.model_selection import train_test_split

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def fit_report(X, y, names, seed=7):
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=seed)
    m = xgb.XGBRegressor(
        n_estimators=300, max_depth=3, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.9, random_state=seed,
    )
    m.fit(Xtr, ytr)
    pred = m.predict(Xte)
    r = float(np.corrcoef(pred, yte)[0, 1])
    ex = shap.TreeExplainer(m)
    sv = ex.shap_values(X)
    imp = pd.DataFrame({
        "feature": names,
        "mean_abs_shap": np.abs(sv).mean(axis=0),
    }).sort_values("mean_abs_shap", ascending=False)
    return r, imp, float(y.mean())


def main() -> None:
    panel = pd.read_csv(os.path.join(DATA, "switcher_panel.csv"))
    stats = {}

    Xa = panel[[
        "decided_share", "team_decided_share", "next_team_decided_share", "switched",
    ]].astype(float)
    ya = panel["next_decided_share"].astype(float)
    r_a, imp_a, mean_a = fit_report(
        Xa.values, ya.values,
        ["own share this season", "own team share", "next team share", "switched teams"],
    )
    imp_a.to_csv(os.path.join(DATA, "shap_uniform.csv"), index=False)
    stats["model_a_uniform"] = {"heldout_corr": r_a, "target_mean": mean_a, "n": int(len(panel))}

    ps = pd.read_csv(os.path.join(DATA, "player_seasons.csv"))
    ps = ps[ps.attempts >= 200].copy()
    ps["decided_rate"] = ps.decided_goals / ps.attempts
    ps["clutch_rate"] = ps.clutch_goals / ps.attempts
    ps["mid_rate"] = (ps.goals - ps.decided_goals - ps.clutch_goals) / ps.attempts
    ps["xg_rate"] = ps.attempt_xg / ps.attempts
    ps["goal_rate"] = ps.goals / ps.attempts
    ps = ps.sort_values(["shooterPlayerId", "season"])
    for c in ["goal_rate", "season"]:
        ps["next_" + c] = ps.groupby("shooterPlayerId")[c].shift(-1)
    pb = ps[ps.next_season == ps.season + 1]
    Xb = pb[["decided_rate", "mid_rate", "clutch_rate", "xg_rate"]].astype(float)
    yb = pb["next_goal_rate"].astype(float)
    r_b, imp_b, mean_b = fit_report(
        Xb.values, yb.values,
        ["decided goals/att", "middle goals/att", "coin-flip goals/att", "xG/att"],
    )
    imp_b.to_csv(os.path.join(DATA, "shap_pay.csv"), index=False)
    stats["model_b_pay"] = {"heldout_corr": r_b, "target_mean": mean_b, "n": int(len(pb))}

    # plain-language linear read of model B for the README
    import numpy.linalg as la
    Xl = np.column_stack([np.ones(len(pb)), Xb.values])
    beta, *_ = la.lstsq(Xl, yb.values, rcond=None)
    stats["model_b_linear_betas"] = {
        n: float(b) for n, b in zip(
            ["const", "decided_rate", "mid_rate", "clutch_rate", "xg_rate"], beta
        )
    }
    with open(os.path.join(DATA, "model_stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))
    print(imp_a.to_string(index=False))
    print(imp_b.to_string(index=False))


if __name__ == "__main__":
    main()
