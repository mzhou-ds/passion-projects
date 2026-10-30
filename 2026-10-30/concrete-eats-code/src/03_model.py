"""Does this year's build-out predict next year's growth? Panel test.

Rows: one per company-year (MSFT/GOOGL/META, 2016+). Target: next-year
revenue growth. Features: capex intensity, R&D intensity, capex growth,
capex/depreciation, lagged revenue growth, log revenue. Validation:
leave-one-company-out CV (the honest test with 3 companies: can a model
trained on two hyperscalers predict the third?). Baselines: predict the
training mean, and predict lagged growth (persistence). XGBoost + SHAP
are reported for explanation, not as a production forecaster: n is small
and the honest result may be that nothing predicts 1-year growth.
"""
import pandas as pd, numpy as np, json, os
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_squared_error, r2_score
import xgboost as xgb, shap

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(HERE, "data", "derived.csv"))
df = df[df.ticker.isin(["MSFT", "GOOGL", "META"])].sort_values(["ticker", "cal_year"]).copy()
df["target_next_growth"] = df.groupby("ticker").rev_growth_1yr.shift(-1)
feats = ["capex_intensity", "rnd_intensity", "capex_growth_1yr",
         "capex_over_depr", "rev_growth_1yr"]
df["log_revenue"] = np.log(df.revenue)
feats = feats + ["log_revenue"]
d = df.dropna(subset=feats + ["target_next_growth"]).copy()
print("panel rows:", len(d), "companies:", sorted(d.ticker.unique()),
      "years:", int(d.cal_year.min()), "-", int(d.cal_year.max()))

X, y, groups = d[feats].values, d.target_next_growth.values, d.ticker.values

def loco(model_fn):
    preds = np.full(len(y), np.nan)
    for g in sorted(set(groups)):
        tr, te = groups != g, groups == g
        m = model_fn()
        m.fit(X[tr], y[tr])
        preds[te] = m.predict(X[te])
    return preds

def rmse(a, b): return float(np.sqrt(mean_squared_error(a, b)))

results = {}
for name, fn in [("ridge", lambda: make_pipeline(StandardScaler(), Ridge(alpha=1.0))),
                 ("xgboost", lambda: xgb.XGBRegressor(n_estimators=100, max_depth=2,
                                                      learning_rate=0.1, subsample=0.9,
                                                      random_state=0))]:
    p = loco(fn)
    results[name] = {"loco_rmse": rmse(y, p), "loco_r2": float(r2_score(y, p))}
    print(name, results[name])
# Baselines
mean_pred = np.array([y[groups != g].mean() for g in groups])
persist = d.rev_growth_1yr.values  # predict next growth = this growth
results["baseline_mean"] = {"loco_rmse": rmse(y, mean_pred)}
results["baseline_persistence"] = {"loco_rmse": rmse(y, persist)}
print("baselines:", results["baseline_mean"], results["baseline_persistence"])

# SHAP on a full-sample XGBoost (explanation only)
full = xgb.XGBRegressor(n_estimators=100, max_depth=2, learning_rate=0.1, random_state=0)
full.fit(X, y)
ex = shap.TreeExplainer(full)
sv = ex.shap_values(X)
mean_abs = np.abs(sv).mean(axis=0)
results["shap_mean_abs"] = {f: round(float(v), 4) for f, v in zip(feats, mean_abs)}
results["n"] = int(len(d))
print("SHAP mean|.|:", results["shap_mean_abs"])
json.dump(results, open(os.path.join(HERE, "data", "model.json"), "w"), indent=1)
np.save(os.path.join(HERE, "data", "shap_values.npy"), sv)
d[["ticker", "cal_year"] + feats + ["target_next_growth"]].to_csv(
    os.path.join(HERE, "data", "panel.csv"), index=False)
