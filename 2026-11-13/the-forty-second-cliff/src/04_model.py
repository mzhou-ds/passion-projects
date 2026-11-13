"""XGBoost goal-probability model: does shift age predict goals once you
control for shot quality? Two models, identical except one drops every
shift-age feature. Held out by game. SHAP ranks the predictors.
"""
import json, os
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
import xgboost as xgb

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

shots = pd.read_csv(os.path.join(DATA, "shots_5v5.csv")).dropna(subset=["dist", "angle"])
SHIFT_FEATS = ["att_mean_age", "def_mean_age", "def_max_age", "def_n_over60",
               "def_n_fresh", "shooter_age"]
SHOT_FEATS = ["dist", "angle", "rebound", "score_diff", "period"]
X = pd.get_dummies(shots[SHOT_FEATS + SHIFT_FEATS + ["shot_type"]],
                   columns=["shot_type"]).astype(float)
y = shots["is_goal"].astype(int)
games = shots["game_id"].values
cut = np.quantile(games, 0.8)
tr, te = games <= cut, games > cut

def fit_predict(cols):
    m = xgb.XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                          subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
                          n_jobs=4, random_state=7)
    m.fit(X.loc[tr, cols], y[tr])
    return m, roc_auc_score(y[te], m.predict_proba(X.loc[te, cols])[:, 1])

full_cols = list(X.columns)
shot_only = [c for c in full_cols if c not in SHIFT_FEATS]
m_full, auc_full = fit_predict(full_cols)
m_shot, auc_shot = fit_predict(shot_only)
print(f"AUC shot-only: {auc_shot:.4f} | AUC + shift features: {auc_full:.4f} "
      f"| lift: {auc_full - auc_shot:+.4f}")

try:
    import shap
    ex = shap.TreeExplainer(m_full)
    sv = ex.shap_values(X.loc[te, full_cols])
    mean_abs = pd.Series(np.abs(sv).mean(axis=0), index=full_cols).sort_values(ascending=False)
    shap_rank = mean_abs.to_dict()
    print("mean |SHAP| ranking:")
    print(mean_abs.round(4).to_string())
    np.save(os.path.join(DATA, "shap_values.npy"), sv)
except Exception as e:
    print("SHAP unavailable, using gain importance:", e)
    imp = pd.Series(m_full.feature_importances_, index=full_cols).sort_values(ascending=False)
    shap_rank = imp.to_dict()
    print(imp.round(4).to_string())

json.dump({"auc_shot_only": round(float(auc_shot), 4),
           "auc_with_shift": round(float(auc_full), 4),
           "auc_lift": round(float(auc_full - auc_shot), 4),
           "shap_rank": {k: round(float(v), 4) for k, v in shap_rank.items()}},
          open(os.path.join(DATA, "model.json"), "w"), indent=2)
