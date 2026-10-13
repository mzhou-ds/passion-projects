"""
03_model.py - what moves the discount, and where it goes next.

Two small-n annual models (2001-2024, n=24). Honest about it: these are
decomposition aids, not forecasting machines. XGBoost with SHAP is run
against an OLS baseline and leave-one-out CV, and the IMF's own WEO
projection is reported alongside a naive trend extension.

Targets:
  d_log_ratio_ppp  - the real gap (strips out the exchange rate)
  d_log_ratio_nom  - the lived gap (what a cross-border salary feels like)
Features:
  d_log_fx         - change in CAD per USD (+ = loonie weakened)
  d_log_oil        - change in WTI
  popgrowth_diff   - Canada minus US population growth (pp)
  hp_growth_diff   - Canada minus US real house-price growth (pp)
  unemp_diff       - Canada minus US unemployment (pp, level)
"""
import json
import os

import numpy as np
import pandas as pd
import shap
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import LeaveOneOut
from xgboost import XGBRegressor

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

panel = pd.read_csv(os.path.join(DATA, "annual_panel.csv"))
p = panel[(panel.year >= 2000) & (panel.year <= 2024)].copy().sort_values("year")
p["d_log_ratio_ppp"] = np.log(p.ratio_ppp).diff()
p["d_log_ratio_nom"] = np.log(p.ratio_nom).diff()
p["d_log_fx"] = np.log(p.fx_cad_per_usd).diff()
p["d_log_oil"] = np.log(p.oil_wti).diff()
p["popgrowth_diff"] = p.popgrowth_wb_can - p.popgrowth_wb_usa
p["hp_growth_diff"] = (p.hp_can.pct_change() - p.hp_usa.pct_change()) * 100
p["unemp_diff"] = p.unemp_can - p.unemp_usa
feat = ["d_log_fx", "d_log_oil", "popgrowth_diff", "hp_growth_diff", "unemp_diff"]
m = p.dropna(subset=feat + ["d_log_ratio_ppp", "d_log_ratio_nom"])
print(f"model panel: {len(m)} years ({int(m.year.min())}-{int(m.year.max())})")
m.to_csv(os.path.join(DATA, "model_panel.csv"), index=False)

out = {"n_years": int(len(m)), "features": feat, "models": {}}


def run(target):
    X, y = m[feat].values, m[target].values
    loo = LeaveOneOut()
    for name, make in [("ols", lambda: LinearRegression()),
                       ("xgboost", lambda: XGBRegressor(
                           n_estimators=300, max_depth=2, learning_rate=0.05,
                           subsample=0.9, colsample_bytree=0.9, random_state=7))]:
        preds = np.zeros(len(y))
        for tr, te in loo.split(X):
            mdl = make().fit(X[tr], y[tr])
            preds[te] = mdl.predict(X[te])
        rmse = float(np.sqrt(np.mean((preds - y) ** 2)))
        out["models"].setdefault(target, {})[name] = {"loocv_rmse": round(rmse, 4)}
    xgb = XGBRegressor(n_estimators=300, max_depth=2, learning_rate=0.05,
                       subsample=0.9, colsample_bytree=0.9, random_state=7).fit(X, y)
    sv = shap.TreeExplainer(xgb)(X).values
    imp = {f: round(float(np.abs(sv[:, i]).mean()), 4) for i, f in enumerate(feat)}
    out["models"][target]["shap_mean_abs"] = dict(
        sorted(imp.items(), key=lambda kv: -kv[1]))
    out["models"][target]["train_r2"] = round(float(xgb.score(X, y)), 3)
    np.save(os.path.join(DATA, f"shap_{target}.npy"), sv)
    return imp


run("d_log_ratio_ppp")
run("d_log_ratio_nom")

# variance-style decomposition for the nominal gap, 2019 -> 2024, accounting identity:
# log nominal ratio change = log PPP ratio change + log(FX/PPP conversion) change.
# We report the split between the real (PPP) move and everything priced in dollars.
sub = panel.set_index("year")
d_nom = float(np.log(sub.loc[2024, "ratio_nom"]) - np.log(sub.loc[2019, "ratio_nom"]))
d_ppp = float(np.log(sub.loc[2024, "ratio_ppp"]) - np.log(sub.loc[2019, "ratio_ppp"]))
out["decomp_2019_2024_logpts"] = {"nominal": round(d_nom, 3), "ppp_real": round(d_ppp, 3),
                                  "dollar_pricing_residual": round(d_nom - d_ppp, 3)}

# projections: IMF WEO path + naive 2015-2024 trend on the PPP ratio
fc = panel[panel.year >= 2025][["year", "ratio_nom", "ratio_ppp"]].dropna()
out["imf_forecast"] = {int(r.year): {"nom": round(float(r.ratio_nom), 4),
                                     "ppp": round(float(r.ratio_ppp), 4)}
                       for r in fc.itertuples()}
hist = p[(p.year >= 2015) & (p.year <= 2024)]
coef = np.polyfit(hist.year, np.log(hist.ratio_ppp), 1)
out["trend_ppp_ratio"] = {y: round(float(np.exp(np.polyval(coef, y))), 4)
                          for y in [2030, 2035]}
out["trend_slope_log_per_year"] = round(float(coef[0]), 4)

json.dump(out, open(os.path.join(DATA, "model.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
