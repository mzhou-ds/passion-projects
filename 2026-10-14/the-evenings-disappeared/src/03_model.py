"""
03_model.py - three modelling pieces.

A. Temporal honesty test. Train an XGBoost classifier for "spends social
   evenings with friends at least monthly" on 1974-2018, then score
   2022-2024 untouched. If the world only changed composition, a model
   that knows who you are should still calibrate. It doesn't - and the
   size of the miss is the behaviour change, in model units.
B. Pooled XGBoost + SHAP (all years, year included) - what actually
   sorts Americans into friend-evening people and everyone else.
C. The friendlessness penalty in happiness: g-computation adjusted
   P("very happy") by friend-evening frequency, fit separately on
   2014-2018 and 2022-2024. Plus the site grid: predicted friend-evening
   rates by life profile, old world vs new world.

Outputs: data/model.json, data/shap_importance.csv, site/data.js
"""
import json
import os

import numpy as np
import pandas as pd
import shap
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
SITE = os.path.join(HERE, "..", "site")
os.makedirs(SITE, exist_ok=True)
rng = np.random.default_rng(7)

df = pd.read_csv(os.path.join(DATA, "analytic.csv"))
d = df.dropna(subset=["friend_monthly"]).copy()

# ------------------------------------------------------------ features
d["race3"] = np.where(d["race"] == 1, "White",
                      np.where(d["race"] == 2, "Black", "Other"))
d["sex_lbl"] = np.where(d["sex"] == 1, "Male", "Female")
d["tvhours_c"] = d["tvhours"].clip(0, 16)
d["hrs1_c"] = d["hrs1"].clip(0, 80)
d["log_size"] = np.log10(d["size"].clip(lower=1))
d["log_rinc"] = np.log10(d["realrinc"].clip(lower=100))
for c in ["tvhours_c", "hrs1_c", "log_rinc", "attend", "educ", "childs"]:
    d[c + "_miss"] = d[c].isna().astype(int)
    d[c] = d[c].fillna(d[c].median())

CATS = ["marital_lbl", "race3", "sex_lbl", "ageband"]
X = pd.get_dummies(
    d[["age", "educ", "childs", "any_kids", "employed", "hrs1_c",
       "tvhours_c", "attend", "log_rinc", "log_size"] + CATS],
    columns=CATS, drop_first=False, dtype=float)
y = d["friend_monthly"].astype(int)
w = d["wt"]

M = {}

# ------------------------------------------------- A. temporal test
pre = d.year <= 2018
post = d.year.isin([2022, 2024])
idx_pre = np.where(pre)[0]
rng.shuffle(idx_pre)
cut = int(0.8 * len(idx_pre))
tr, te = idx_pre[:cut], idx_pre[cut:]

clf = XGBClassifier(n_estimators=400, max_depth=4, learning_rate=0.05,
                    subsample=0.9, colsample_bytree=0.9, eval_metric="logloss",
                    random_state=7)
clf.fit(X.iloc[tr], y.iloc[tr], sample_weight=w.iloc[tr])
p_te = clf.predict_proba(X.iloc[te])[:, 1]
p_post = clf.predict_proba(X[post])[:, 1]
M["temporal"] = {
    "auc_holdout_pre": round(roc_auc_score(y.iloc[te], p_te,
                                           sample_weight=w.iloc[te]), 3),
    "auc_post": round(roc_auc_score(y[post], p_post,
                                    sample_weight=w[post]), 3),
    "pred_mean_post": round(100 * np.average(p_post, weights=w[post]), 1),
    "actual_mean_post": round(100 * np.average(y[post], weights=w[post]), 1),
    "overprediction_pp": round(100 * (np.average(p_post, weights=w[post]) -
                                      np.average(y[post], weights=w[post])), 1),
    "n_train": int(len(tr)), "n_post": int(post.sum()),
}

# ------------------------------------------- B. pooled model + SHAP
Xp = X.copy()
Xp["year"] = d["year"]
clf2 = XGBClassifier(n_estimators=400, max_depth=4, learning_rate=0.05,
                     subsample=0.9, colsample_bytree=0.9,
                     eval_metric="logloss", random_state=7)
clf2.fit(Xp, y, sample_weight=w)
M["pooled_auc_insample"] = round(roc_auc_score(y, clf2.predict_proba(Xp)[:, 1],
                                               sample_weight=w), 3)
sample = Xp.sample(min(6000, len(Xp)), random_state=7)
sv = shap.TreeExplainer(clf2).shap_values(sample)
imp = pd.DataFrame({"feature": Xp.columns,
                    "mean_abs_shap": np.abs(sv).mean(axis=0)}).sort_values(
                        "mean_abs_shap", ascending=False)
imp.to_csv(os.path.join(DATA, "shap_importance.csv"), index=False)
M["shap_top10"] = [(r.feature, round(r.mean_abs_shap, 3))
                   for r in imp.head(10).itertuples()]
# SHAP dependence sign for the three continuous headliners
for feat in ["tvhours_c", "age", "year"]:
    j = list(Xp.columns).index(feat)
    pair = pd.DataFrame({"x": sample[feat].to_numpy(dtype=float),
                         "s": sv[:, j]}).dropna()
    M[f"shap_corr_{feat}"] = round(float(np.corrcoef(pair.x, pair.s)[0, 1]), 2)

# ------------------------------- C1. happiness penalty, g-computation
h = df.dropna(subset=["happy", "socfrend", "health"]).copy()
h["sex_lbl"] = np.where(h["sex"] == 1, "Male", "Female")
h["very_happy"] = (h["happy"] == 1).astype(int)
h["freq"] = pd.cut(h["socfrend"], [0, 2, 4, 5, 7],
                   labels=["Weekly+", "Monthly", "Yearly", "Rarely/never"])
h["freq"] = h["freq"].astype(str)
h["poor_health"] = (h["health"] >= 3).astype(int)
h["log_rinc"] = np.log10(h["realrinc"].clip(lower=100)).fillna(
    np.log10(h["realrinc"].clip(lower=100)).median())
h["educ_f"] = h["educ"].fillna(h["educ"].median())
for c in ["age", "childs"]:
    h[c] = h[c].fillna(h[c].median())
XH = pd.get_dummies(h[["age", "educ_f", "log_rinc", "poor_health", "childs",
                       "marital_lbl", "sex_lbl", "freq"]],
                    columns=["marital_lbl", "sex_lbl", "freq"],
                    drop_first=False, dtype=float)
freq_cols = [c for c in XH.columns if c.startswith("freq_")]


def adjusted_by_freq(pool_mask):
    lr = LogisticRegression(max_iter=2000, C=1.0)
    lr.fit(XH[pool_mask], h.loc[pool_mask, "very_happy"],
           sample_weight=h.loc[pool_mask, "wt"])
    out = {}
    base = XH[pool_mask].copy()
    for fc in freq_cols:
        cf = base.copy()
        cf[freq_cols] = 0.0
        cf[fc] = 1.0
        out[fc.replace("freq_", "")] = round(
            100 * np.average(lr.predict_proba(cf)[:, 1],
                             weights=h.loc[pool_mask, "wt"]), 1)
    auc = roc_auc_score(h.loc[pool_mask, "very_happy"],
                        lr.predict_proba(base)[:, 1],
                        sample_weight=h.loc[pool_mask, "wt"])
    return out, round(auc, 3)


adj_pre, auc_pre = adjusted_by_freq(h.year.between(2014, 2018))
adj_post, auc_post = adjusted_by_freq(h.year.isin([2022, 2024]))
M["happiness_adjusted"] = {"pre_2014_18": adj_pre, "post_2022_24": adj_post,
                           "logit_auc_pre": auc_pre, "logit_auc_post": auc_post}
M["happiness_penalty_pre_pp"] = round(adj_pre["Weekly+"] -
                                      adj_pre["Rarely/never"], 1)
M["happiness_penalty_post_pp"] = round(adj_post["Weekly+"] -
                                       adj_post["Rarely/never"], 1)

# ------------------------------- C2. site grid: empirical cell rates
# Deliberately not a model: weighted % with friend evenings at least
# monthly inside each (age band x marital x kids x employed x sex) cell,
# per era, shrunk toward the era's age-band rate when a cell is thin
# (k=25 pseudo-respondents). Calibrated by construction.
d["marital3"] = np.where(d["marital"] == 1, "Married",
                         np.where(d["marital"] == 5, "Never married",
                                  "Divorced / widowed / separated"))
grid_rows = []
for ageband in ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]:
    for marital in ["Married", "Never married",
                    "Divorced / widowed / separated"]:
        for kids in [0, 1]:
            for emp in [0, 1]:
                for sex in ["Male", "Female"]:
                    r = {"ageband": ageband, "marital": marital,
                         "kids": kids, "employed": emp, "sex": sex}
                    ok = True
                    for lbl, mask in [("world_2014_18",
                                       d.year.between(2014, 2018)),
                                      ("world_2022_24",
                                       d.year.isin([2022, 2024]))]:
                        era = d[mask]
                        band = era[era.ageband == ageband]
                        band_rate = np.average(band.friend_monthly,
                                               weights=band.wt)
                        cell = band[(band.marital3 == marital) &
                                    (band.any_kids == kids) &
                                    (band.employed == emp) &
                                    (band.sex_lbl == sex)]
                        n = len(cell)
                        if n == 0:
                            ok = False
                            break
                        raw = np.average(cell.friend_monthly,
                                         weights=cell.wt)
                        shrunk = (n * raw + 25 * band_rate) / (n + 25)
                        r[lbl] = round(100 * shrunk, 1)
                        r[f"n_{lbl}"] = int(n)
                    if ok:
                        grid_rows.append(r)
grid = pd.DataFrame(grid_rows)
grid.to_csv(os.path.join(DATA, "site_grid.csv"), index=False)
M["grid_cells"] = int(len(grid))
M["grid_min_cell_n_post"] = int(grid["n_world_2022_24"].min())

with open(os.path.join(SITE, "data.js"), "w") as f:
    f.write("const GRID = " + json.dumps(grid_rows) + ";\n")
    f.write("const FINDINGS = " + json.dumps(
        {"drop_pp": -7.8, "pre": 64.6, "post": 56.8}) + ";\n")

with open(os.path.join(DATA, "model.json"), "w") as f:
    json.dump(M, f, indent=1)
print(json.dumps(M, indent=1))
