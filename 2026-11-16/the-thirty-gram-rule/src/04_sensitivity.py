"""Sensitivity checks for build #66.

Q1: Is the null for meals>=30 robust to NOT controlling for BMI?
    (BMI contains lean mass, so it can soak up the diet signal.)
Q2: Does total protein become significant without BMI control?
Q3: Is the breakfast-protein signal robust (skippers, quartiles)?
Q4: Grip: does the negative protein-per-kg coefficient survive
    height+weight controls instead of BMI, or protein in grams?
"""
import json
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "..", "output")
dxa = pd.read_csv(os.path.join(OUT, "analytic_dxa.csv"))
grip = pd.read_csv(os.path.join(OUT, "analytic_grip.csv"))

RACE = {1: "MexicanAm", 2: "OtherHisp", 3: "NHWhite", 4: "NHBlack", 6: "NHAsian", 7: "Other"}


def design(data, extra, size="bmi"):
    X = pd.DataFrame(index=data.index)
    X["const"] = 1.0
    X["age"] = data["RIDAGEYR"]
    X["age2"] = data["RIDAGEYR"] ** 2 / 100.0
    X["male"] = (data["RIAGENDR"] == 1).astype(float)
    if size == "bmi":
        X["bmi"] = data["BMXBMI"]
    elif size == "ht_wt":
        X["height_m"] = data["height_m"]
        X["weight_kg"] = data["BMXWT"]
    elif size == "height":
        X["height_m"] = data["height_m"]
    X["kcal_k"] = data["kcal"] / 1000.0
    X["vigorous"] = data["vigorous"]
    X["moderate"] = data["moderate"]
    X["sedentary_h"] = data["sedentary_min"] / 60.0
    for code, name in RACE.items():
        if code != 3:
            X[f"race_{name}"] = (data["RIDRETH3"] == code).astype(float)
    for c in extra:
        X[c] = data[c]
    return X


def ols(data, y, extra, size="bmi"):
    X = design(data, extra, size)
    yv = data[y].astype(float)
    wv = data["WTDR2D"].astype(float)
    keep = X.notna().all(axis=1) & yv.notna() & wv.notna()
    m = sm.WLS(yv[keep], X[keep], weights=wv[keep]).fit(cov_type="HC1")
    out = {"n": int(keep.sum()), "r2": round(float(m.rsquared), 4)}
    for c in extra:
        out[c] = {"coef": round(float(m.params[c]), 4), "p": float(m.pvalues[c]),
                  "ci": [round(float(m.conf_int().loc[c, 0]), 4),
                         round(float(m.conf_int().loc[c, 1]), 4)]}
    return out


res = {}

# predictor correlations
res["corr_protein_features"] = dxa[["protein_per_kg", "protein_g", "meals_ge30",
                                    "breakfast", "max_meal", "share_largest",
                                    "BMXBMI", "BMXWT"]].corr().round(2).to_dict()

# Q1/Q2: ALMI without BMI
for size in ["bmi", "ht_wt", "height", "none"]:
    res[f"ALMI_total_size={size}"] = ols(dxa, "ALMI", ["protein_per_kg"], size)
    res[f"ALMI_meals30_size={size}"] = ols(dxa, "ALMI", ["protein_per_kg", "meals_ge30"], size)
    res[f"ALMI_breakfast_size={size}"] = ols(dxa, "ALMI", ["protein_per_kg", "breakfast"], size)

# protein in grams (not per kg)
res["ALMI_protein_grams_bmi"] = ols(dxa, "ALMI", ["protein_g"], "bmi")
res["ALMI_protein_grams_htwt"] = ols(dxa, "ALMI", ["protein_g"], "ht_wt")

# Q3: breakfast robustness
res["ALMI_breakfast_no_skippers"] = ols(dxa[dxa["breakfast"] > 0], "ALMI",
                                        ["protein_per_kg", "breakfast"], "bmi")
dxa_q = dxa.copy()
dxa_q["bf_q"] = pd.qcut(dxa_q["breakfast"], 4, labels=False, duplicates="drop")
res["ALMI_by_breakfast_quartile_raw"] = (
    dxa_q.groupby("bf_q").apply(
        lambda g: {"n": int(len(g)),
                   "bf_range_g": [round(float(g["breakfast"].min()), 1),
                                  round(float(g["breakfast"].max()), 1)],
                   "mean_ALMI": round(float(g["ALMI"].mean()), 3),
                   "mean_protein_per_kg": round(float(g["protein_per_kg"].mean()), 2)},
        include_groups=False).to_dict())
res["pct_skip_breakfast"] = float((dxa["breakfast"] == 0).mean() * 100)

# Q4: grip with different size controls / protein units
for size in ["bmi", "ht_wt", "height"]:
    res[f"grip_total_size={size}"] = ols(grip, "grip", ["protein_per_kg"], size)
    res[f"grip_meals30_size={size}"] = ols(grip, "grip", ["protein_per_kg", "meals_ge30"], size)
res["grip_protein_grams_htwt"] = ols(grip, "grip", ["protein_g"], "ht_wt")
res["grip_protein_grams_bmi"] = ols(grip, "grip", ["protein_g"], "bmi")
# grip normalized by body weight
grip2 = grip.copy()
grip2["grip_per_kg"] = grip2["grip"] / grip2["BMXWT"]
res["grip_per_kg_total"] = ols(grip2, "grip_per_kg", ["protein_per_kg"], "ht_wt")
res["grip_per_kg_meals30"] = ols(grip2, "grip_per_kg", ["protein_per_kg", "meals_ge30"], "ht_wt")

# effect-size translation for breakfast signal (BMI model)
b = res["ALMI_breakfast_size=bmi"]["breakfast"]["coef"]
res["breakfast_effect_17g_more"] = round(b * 17, 3)  # mean 13g -> 30g
res["ALMI_sd"] = round(float(dxa["ALMI"].std()), 3)
res["grip_sd"] = round(float(grip["grip"].std()), 2)

print(json.dumps(res, indent=2))
with open(os.path.join(OUT, "sensitivity.json"), "w") as f:
    json.dump(res, f, indent=2)
