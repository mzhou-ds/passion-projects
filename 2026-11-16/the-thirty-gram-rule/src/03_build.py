"""
Build #66 — "The 30-Gram Rule Is a Lab Artifact"
Question: does how you split protein across meals predict lean mass / strength
in free-living adults, once TOTAL protein is accounted for?

Data: NHANES 2013-2014 (the last cycle with BOTH whole-body DXA and grip strength)
  - DR1IFF_H / DR2IFF_H : meal-level 24h recalls (protein per eating occasion)
  - DR1TOT_H / DR2TOT_H : daily totals + survey weights (WTDR2D)
  - DXX_H               : whole-body DXA (appendicular lean mass)
  - MGX_H               : combined grip strength (MGDCGSZ)
  - DEMO_H / BMX_H / PAQ_H : demographics, measured weight/height, activity

The per-meal ceiling (~25-30 g for maximal muscle protein synthesis) comes from
acute lab studies (Moore et al. 2009; Areta et al. 2013). It has never been tested
against measured body composition in a free-living population.
"""
import json
import os

import numpy as np
import pandas as pd
import pyreadstat
import statsmodels.api as sm
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import HistGradientBoostingRegressor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "..", "data")
OUT = os.path.join(BASE, "..", "output")
os.makedirs(OUT, exist_ok=True)

MEAL_MAP = {
    1: "breakfast", 10: "breakfast",          # Breakfast / Desayuno
    2: "lunch", 11: "lunch",                  # Lunch / Almuerzo
    3: "dinner", 4: "dinner", 12: "dinner", 14: "dinner",  # Dinner / Supper / Comida / Cena
    6: "snack", 13: "snack", 15: "snack", 16: "snack", 17: "snack", 18: "snack",
    7: "drink", 19: "drink",                  # Beverage/Drink / Bebida
}
MAIN_MEALS = ["breakfast", "lunch", "dinner"]


def load(name):
    df, _ = pyreadstat.read_xport(os.path.join(DATA, name + ".xpt"))
    return df


def meal_day(iff, prefix, reliable_col):
    """Aggregate one recall day to per-person per-meal protein."""
    d = iff[iff[reliable_col] == 1].copy()
    d["bucket"] = d[f"{prefix}_030Z"].map(MEAL_MAP)
    d = d[d["bucket"].notna()]
    g = d.groupby(["SEQN", "bucket"])[f"{prefix}IPROT"].sum().unstack(fill_value=0.0)
    for m in MAIN_MEALS + ["snack", "drink"]:
        if m not in g:
            g[m] = 0.0
    g["total_protein"] = g[MAIN_MEALS + ["snack", "drink"]].sum(axis=1)
    g["total_kcal"] = d.groupby("SEQN")[f"{prefix}IKCAL"].sum()
    g["n_foods"] = d.groupby("SEQN").size()
    return g.reset_index()


# ---------------------------------------------------------------- diet
d1 = meal_day(load("DR1IFF_H"), "DR1", "DR1DRSTZ")
d2 = meal_day(load("DR2IFF_H"), "DR2", "DR2DRSTZ")
diet = d1.merge(d2, on="SEQN", suffixes=("_d1", "_d2"), how="inner")
print(f"both recall days: {len(diet):,}")

tot1 = load("DR1TOT_H")[["SEQN", "WTDRD1", "WTDR2D", "DR1TKCAL", "DR1TPROT"]]
tot2 = load("DR2TOT_H")[["SEQN", "DR2TKCAL", "DR2TPROT"]]
diet = diet.merge(tot1, on="SEQN").merge(tot2, on="SEQN")
# 2-day averages of the meal-level aggregates (cross-check totals vs TOT files)
for m in MAIN_MEALS + ["snack", "drink"]:
    diet[m] = (diet[f"{m}_d1"] + diet[f"{m}_d2"]) / 2
diet["protein_g"] = (diet["total_protein_d1"] + diet["total_protein_d2"]) / 2
diet["kcal"] = (diet["DR1TKCAL"] + diet["DR2TKCAL"]) / 2
# sanity: IFF-derived totals vs TOT-file totals
print("IFF vs TOT protein corr:",
      np.corrcoef(diet["protein_g"], (diet["DR1TPROT"] + diet["DR2TPROT"]) / 2)[0, 1].round(4))

# ---------------------------------------------------------------- distribution metrics
for m in MAIN_MEALS:
    diet[f"ge25_{m}"] = (diet[m] >= 25).astype(int)
    diet[f"ge30_{m}"] = (diet[m] >= 30).astype(int)
diet["meals_ge25"] = diet[[f"ge25_{m}" for m in MAIN_MEALS]].sum(axis=1)
diet["meals_ge30"] = diet[[f"ge30_{m}" for m in MAIN_MEALS]].sum(axis=1)
diet["max_meal"] = diet[MAIN_MEALS].max(axis=1)
diet["share_largest"] = diet["max_meal"] / diet["protein_g"]
diet["cv_meals"] = diet[MAIN_MEALS].std(axis=1) / diet[MAIN_MEALS].mean(axis=1)
diet["breakfast_share"] = diet["breakfast"] / diet["protein_g"]

# ---------------------------------------------------------------- people
demo = load("DEMO_H")[["SEQN", "RIAGENDR", "RIDAGEYR", "RIDRETH3", "RIDEXPRG"]]
bmx = load("BMX_H")[["SEQN", "BMXWT", "BMXHT", "BMXBMI"]]
paq = load("PAQ_H")[["SEQN", "PAQ650", "PAQ665", "PAD680"]]
dxx = load("DXX_H")
dxx["ALM"] = (dxx["DXDLALE"] + dxx["DXDRALE"] + dxx["DXDLLLE"] + dxx["DXDRLLE"]) / 1000.0
dxx = dxx[["SEQN", "DXAEXSTS", "ALM"]]
mgx = load("MGX_H")[["SEQN", "MGDEXSTS", "MGDCGSZ"]]

df = diet.merge(demo, on="SEQN").merge(bmx, on="SEQN").merge(paq, on="SEQN", how="left")
df = df.merge(dxx, on="SEQN", how="left").merge(mgx, on="SEQN", how="left")

# ---------------------------------------------------------------- sample restrictions
df = df[(df["RIDAGEYR"] >= 20) & (df["RIDAGEYR"] <= 59)]          # DXA age range
df = df[df["RIDEXPRG"] != 1]                                       # not pregnant
df = df[(df["kcal"] >= 500) & (df["kcal"] <= 6000)]                # plausible energy
df = df[df["BMXWT"].notna() & df["BMXHT"].notna()]
df["height_m"] = df["BMXHT"] / 100.0
df["protein_per_kg"] = df["protein_g"] / df["BMXWT"]
df["ALMI"] = df["ALM"] / df["height_m"] ** 2
df["sex"] = np.where(df["RIAGENDR"] == 1, "M", "F")
df["vigorous"] = (df["PAQ650"] == 1).astype(float)
df["moderate"] = (df["PAQ665"] == 1).astype(float)
df["sedentary_min"] = df["PAD680"]
df["grip"] = df["MGDCGSZ"]

dxa = df[df["ALM"].notna()].copy()
grip = df[df["grip"].notna()].copy()
print(f"analytic sample (DXA): {len(dxa):,} | (grip): {len(grip):,}")
print(f"DXA sample: {dxa['sex'].value_counts().to_dict()}, age {dxa['RIDAGEYR'].mean():.1f} "
      f"(range {dxa['RIDAGEYR'].min():.0f}-{dxa['RIDAGEYR'].max():.0f})")
dxa.to_csv(os.path.join(OUT, "analytic_dxa.csv"), index=False)
grip.to_csv(os.path.join(OUT, "analytic_grip.csv"), index=False)

# ---------------------------------------------------------------- descriptives (survey-weighted, WTDR2D)
w = dxa["WTDR2D"]
def wmean(s, w):
    return float(np.average(s, weights=w))

desc = {
    "n_dxa": int(len(dxa)),
    "n_grip": int(len(grip)),
    "weighted_mean_protein_g": wmean(dxa["protein_g"], w),
    "weighted_mean_protein_per_kg": wmean(dxa["protein_per_kg"], w),
    "weighted_mean_kcal": wmean(dxa["kcal"], w),
    "weighted_mean_by_meal": {m: wmean(dxa[m], w) for m in MAIN_MEALS + ["snack"]},
    "pct_breakfast_ge25": float(np.average(dxa["ge25_breakfast"], weights=w) * 100),
    "pct_lunch_ge25": float(np.average(dxa["ge25_lunch"], weights=w) * 100),
    "pct_dinner_ge25": float(np.average(dxa["ge25_dinner"], weights=w) * 100),
    "pct_breakfast_ge30": float(np.average(dxa["ge30_breakfast"], weights=w) * 100),
    "pct_zero_meals_ge30": float(np.average(dxa["meals_ge30"] == 0, weights=w) * 100),
    "pct_three_meals_ge30": float(np.average(dxa["meals_ge30"] == 3, weights=w) * 100),
    "pct_protein_lt_0.8gkg": float(np.average(dxa["protein_per_kg"] < 0.8, weights=w) * 100),
    "pct_protein_lt_1.2gkg": float(np.average(dxa["protein_per_kg"] < 1.2, weights=w) * 100),
    "mean_breakfast_share_pct": float(wmean(dxa["breakfast_share"], w) * 100),
    "mean_ALMI": wmean(dxa["ALMI"], w),
    "mean_grip": wmean(grip["grip"], grip["WTDR2D"]),
}
print(json.dumps(desc, indent=2))

# ---------------------------------------------------------------- regressions
RACE = {1: "MexicanAm", 2: "OtherHisp", 3: "NHWhite", 4: "NHBlack", 6: "NHAsian", 7: "Other"}


def design(data, extra_cols):
    X = pd.DataFrame(index=data.index)
    X["const"] = 1.0
    X["age"] = data["RIDAGEYR"]
    X["age2"] = data["RIDAGEYR"] ** 2 / 100.0
    X["male"] = (data["RIAGENDR"] == 1).astype(float)
    X["bmi"] = data["BMXBMI"]
    X["kcal_k"] = data["kcal"] / 1000.0
    X["vigorous"] = data["vigorous"]
    X["moderate"] = data["moderate"]
    X["sedentary_h"] = data["sedentary_min"] / 60.0
    for code, name in RACE.items():
        if code != 3:
            X[f"race_{name}"] = (data["RIDRETH3"] == code).astype(float)
    for c in extra_cols:
        X[c] = data[c]
    return X


def ols(data, y, extra_cols, weights=None, label=""):
    X = design(data, extra_cols)
    yv = data[y].astype(float)
    wv = weights.astype(float) if weights is not None else None
    keep = X.notna().all(axis=1) & yv.notna()
    if wv is not None:
        keep &= wv.notna()
    X, yv = X[keep], yv[keep]
    wv = wv[keep] if wv is not None else None
    model = sm.WLS(yv, X, weights=wv).fit(cov_type="HC1")
    rows = {}
    for c in extra_cols:
        rows[c] = {"coef": float(model.params[c]), "se": float(model.bse[c]),
                   "p": float(model.pvalues[c]),
                   "ci_lo": float(model.conf_int().loc[c, 0]),
                   "ci_hi": float(model.conf_int().loc[c, 1])}
    return {"label": label, "y": y, "n": int(len(data)), "r2": float(model.rsquared),
            "adj_r2": float(model.rsquared_adj), "coefs": rows}


results = {}
for y, data in [("ALMI", dxa), ("grip", grip)]:
    wts = data["WTDR2D"]
    results[f"{y}_total_only"] = ols(data, y, ["protein_per_kg"], wts, "total protein only")
    results[f"{y}_total_plus_meals30"] = ols(data, y, ["protein_per_kg", "meals_ge30"], wts,
                                            "total + #meals>=30g")
    results[f"{y}_total_plus_meals25"] = ols(data, y, ["protein_per_kg", "meals_ge25"], wts,
                                            "total + #meals>=25g")
    results[f"{y}_total_plus_breakfast"] = ols(data, y, ["protein_per_kg", "breakfast"], wts,
                                              "total + breakfast protein (g)")
    results[f"{y}_total_plus_evenness"] = ols(data, y, ["protein_per_kg", "share_largest", "cv_meals"],
                                             wts, "total + evenness")
    results[f"{y}_total_plus_maxmeal"] = ols(data, y, ["protein_per_kg", "max_meal"], wts,
                                            "total + largest meal (g)")
    results[f"{y}_dist_only"] = ols(data, y, ["meals_ge30", "breakfast", "share_largest"], wts,
                                    "distribution only (no total)")

# subgroup: low vs adequate total protein
for name, sub in [("low_protein_lt1.2", dxa[dxa["protein_per_kg"] < 1.2]),
                  ("adequate_protein_ge1.2", dxa[dxa["protein_per_kg"] >= 1.2]),
                  ("men", dxa[dxa["RIAGENDR"] == 1]),
                  ("women", dxa[dxa["RIAGENDR"] == 2]),
                  ("age20_39", dxa[dxa["RIDAGEYR"] < 40]),
                  ("age40_59", dxa[dxa["RIDAGEYR"] >= 40])]:
    if len(sub) > 200:
        results[f"ALMI_sub_{name}"] = ols(sub, "ALMI", ["protein_per_kg", "meals_ge30"],
                                          sub["WTDR2D"], f"ALMI subgroup {name}")

# ---------------------------------------------------------------- XGBoost + SHAP (unweighted, DXA sample)
from sklearn.model_selection import train_test_split
import xgboost as xgb
import shap

feat_cols = ["protein_per_kg", "meals_ge30", "meals_ge25", "breakfast", "lunch", "dinner",
             "max_meal", "share_largest", "cv_meals", "kcal", "RIDAGEYR", "BMXBMI",
             "vigorous", "moderate", "sedentary_min"]
X = dxa[feat_cols].copy()
X["male"] = (dxa["RIAGENDR"] == 1).astype(float)
X = X.fillna(X.median(numeric_only=True))
y = dxa["ALMI"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42)
m = xgb.XGBRegressor(n_estimators=400, max_depth=4, learning_rate=0.05,
                     subsample=0.9, colsample_bytree=0.9, random_state=42)
m.fit(Xtr, ytr)
r2 = float(m.score(Xte, yte))
print(f"XGB ALMI test R2 = {r2:.3f}")
expl = shap.TreeExplainer(m)
sv = expl.shap_values(Xte)
mean_abs = np.abs(sv).mean(axis=0)
shap_rank = sorted(zip(X.columns, mean_abs), key=lambda t: -t[1])
print("SHAP ranking (ALMI):")
for f, v in shap_rank:
    print(f"   {f:16s} {v:.4f}")

results["xgb_almi_test_r2"] = r2
results["shap_ranking_almi"] = [{"feature": f, "mean_abs_shap": float(v)} for f, v in shap_rank]

# same for grip
y2 = grip["ALMI"]  # placeholder overwritten below
Xg = grip[feat_cols].copy()
Xg["male"] = (grip["RIAGENDR"] == 1).astype(float)
Xg = Xg.fillna(Xg.median(numeric_only=True))
y2 = grip["grip"]
Xtr, Xte, ytr, yte = train_test_split(Xg, y2, test_size=0.25, random_state=42)
m2 = xgb.XGBRegressor(n_estimators=400, max_depth=4, learning_rate=0.05,
                      subsample=0.9, colsample_bytree=0.9, random_state=42)
m2.fit(Xtr, ytr)
r2g = float(m2.score(Xte, yte))
expl2 = shap.TreeExplainer(m2)
sv2 = expl2.shap_values(Xte)
shap_rank2 = sorted(zip(Xg.columns, np.abs(sv2).mean(axis=0)), key=lambda t: -t[1])
print(f"XGB grip test R2 = {r2g:.3f}")
print("SHAP ranking (grip):")
for f, v in shap_rank2:
    print(f"   {f:16s} {v:.4f}")
results["xgb_grip_test_r2"] = r2g
results["shap_ranking_grip"] = [{"feature": f, "mean_abs_shap": float(v)} for f, v in shap_rank2]

# ---------------------------------------------------------------- adjusted means: ALMI by meals>=30 (marginal, holding total protein fixed)
dxa2 = dxa.copy()
Xa = design(dxa2, ["protein_per_kg", "meals_ge30"])
keep = Xa.notna().all(axis=1) & dxa2["ALMI"].notna()
dxa2, Xa = dxa2[keep], Xa[keep]
fit = sm.WLS(dxa2["ALMI"], Xa, weights=dxa2["WTDR2D"]).fit(cov_type="HC1")
adj = []
for k in range(4):
    tmp = dxa2.copy()
    tmp["meals_ge30"] = k
    pred = fit.predict(design(tmp, ["protein_per_kg", "meals_ge30"]))
    adj.append({"meals_ge30": k, "adj_ALMI": float(np.average(pred, weights=dxa2["WTDR2D"])),
                "n": int((dxa2["meals_ge30"] == k).sum())})
results["adjusted_ALMI_by_meals_ge30"] = adj
print(json.dumps(adj, indent=2))

with open(os.path.join(OUT, "results.json"), "w") as f:
    json.dump({"descriptives": desc, "regressions": results}, f, indent=2)
print("wrote output/results.json")
