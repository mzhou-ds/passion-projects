"""03_analysis.py — the head-to-head: grip strength vs the standard vitals.

Models are Cox proportional hazards on months from exam to death / Dec 31 2019.
Base covariates: age, sex, race, education, smoking, baseline CVD/cancer.
Candidates added one at a time (per-SD hazard ratios) and in combination.
Model comparison uses repeated 5-fold cross-validated Harrell's C-index,
so the contest is out-of-sample, not in-sample fit.

Outputs: data/table1.csv, data/prevalence.csv, data/hr_per_sd.csv,
data/cv_cindex.csv, data/quintiles.csv, data/dose_response.csv,
data/grip_years.csv, data/analysis.json
"""
import json
import os

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.utils import concordance_index
from sklearn.model_selection import KFold

BASE = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(BASE, "data")
df = pd.read_csv(os.path.join(DATA, "analytic.csv"))
df["vig_any"] = (df["vig_min_week"] > 0).astype(float)
rng = np.random.default_rng(7)

# ------------------------------------------------------------------ design
BASE_COVS = ["age", "female", "race", "educ", "smoking", "baseline_disease"]


def design(d, extra=None, standardize=None):
    """Build a modelling frame: dummies for race/smoking, optional extras.

    standardize: list of columns to z-score (uses the passed frame's own
    mean/sd; for CV we standardize inside each fold — see cv_cindex).
    """
    X = d[["time_months", "dead"]].copy()
    X["age"] = d["age"]
    X["female"] = d["female"]
    for v in [1, 2, 4, 6, 7]:  # race dummies vs NH White (3)
        X[f"race_{v}"] = (d["race"] == v).astype(int)
    X["educ"] = d["educ"]
    X["smoke_former"] = (d["smoking"] == "former").astype(int)
    X["smoke_current"] = (d["smoking"] == "current").astype(int)
    X["baseline_disease"] = d["baseline_disease"]
    if extra:
        for c in extra:
            X[c] = d[c]
    if standardize:
        for c in standardize:
            X[c] = (X[c] - X[c].mean()) / X[c].std(ddof=0)
    return X.dropna()


def fit_cph(X, cols):
    cph = CoxPHFitter()
    cph.fit(X[["time_months", "dead"] + cols], duration_col="time_months",
            event_col="dead")
    return cph


def cindex(cph, X, cols):
    pred = cph.predict_partial_hazard(X[cols])
    return concordance_index(X["time_months"], -pred.values.ravel(),
                             X["dead"])


# ------------------------------------------------------------- Table 1
cont = ["age", "grip_combined", "grip_max", "grip_relative", "bmi",
        "weight_kg", "waist_cm", "sbp", "dbp", "pulse", "vig_min_week"]
rows = []
for c in cont:
    a = df.loc[df["dead"] == 0, c]
    b = df.loc[df["dead"] == 1, c]
    rows.append({"variable": c,
                 "alive_median": round(a.median(), 1),
                 "alive_iqr": f"{a.quantile(.25):.1f}-{a.quantile(.75):.1f}",
                 "dead_median": round(b.median(), 1),
                 "dead_iqr": f"{b.quantile(.25):.1f}-{b.quantile(.75):.1f}",
                 "n": int(df[c].notna().sum())})
rows.append({"variable": "strength_any (% yes)",
             "alive_median": round(100 * df.loc[df["dead"] == 0,
                                                "strength_any"].mean(), 1),
             "alive_iqr": "-",
             "dead_median": round(100 * df.loc[df["dead"] == 1,
                                               "strength_any"].mean(), 1),
             "dead_iqr": "-",
             "n": int(df["strength_any"].notna().sum())})
t1 = pd.DataFrame(rows)
t1.to_csv(os.path.join(DATA, "table1.csv"), index=False)
print(t1.to_string(index=False))

# ------------------------------------------- EWGSOP2 weak-grip prevalence
# survey-weighted share below 27 kg (men) / 16 kg (women) max grip
prev = []
for (sex, band), g in df.groupby(["female", "age_band"], observed=True):
    w = g["wt_pooled"]
    prev.append({"female": int(sex), "age_band": str(band),
                 "n": len(g),
                 "weak_pct_weighted": round(
                     100 * np.average(g["weak_ewgsop"], weights=w), 1),
                 "weak_pct_unweighted": round(
                     100 * g["weak_ewgsop"].mean(), 1)})
prev = pd.DataFrame(prev)
prev.to_csv(os.path.join(DATA, "prevalence.csv"), index=False)
print("\nEWGSOP2 weak-grip prevalence (weighted %):")
print(prev.to_string(index=False))

# --------------------------------------- cause-of-death codes (for checks)
print("\nUCOD_LEADING among deaths:")
print(df.loc[df["dead"] == 1, "UCOD_LEADING"].value_counts(dropna=False)
      .head(12))

# --------------------------------------------- per-SD hazard ratios (base-adj)
CANDIDATES = {
    "grip_combined": ("Grip strength, combined (kg)", 5.0),
    "grip_max": ("Grip strength, max (kg)", 5.0),
    "grip_relative": ("Grip / bodyweight", 0.1),
    "bmi": ("BMI", 5.0),
    "sbp": ("Systolic BP (mmHg)", 10.0),
    "pulse": ("Resting pulse (bpm)", 10.0),
    "waist_cm": ("Waist (cm)", 10.0),
    "strength_any": ("Any strength training (yes vs no)", 1.0),
    "vig_any": ("Any vigorous activity (yes vs no)", 1.0),
}
base_cols = ["age", "female", "race_1", "race_2", "race_4", "race_6",
             "race_7", "educ", "smoke_former", "smoke_current",
             "baseline_disease"]

hr_rows = []
for var, (label, unit) in CANDIDATES.items():
    sub = df[["time_months", "dead", "age", "female", "race", "educ",
              "smoking", "baseline_disease", var]].copy()
    X = design(sub, extra=[var])
    # fit on raw units for the per-unit HR, then rescale to `unit`
    cph = fit_cph(X, base_cols + [var])
    beta = cph.params_[var]
    se = cph.standard_errors_[var]
    hr_rows.append({
        "variable": var, "label": label, "unit": unit,
        "hr_per_unit": round(float(np.exp(beta * unit)), 3),
        "hr_lo": round(float(np.exp((beta - 1.96 * se) * unit)), 3),
        "hr_hi": round(float(np.exp((beta + 1.96 * se) * unit)), 3),
        "p": float(cph.summary.loc[var, "p"]),
        "c_index": round(cindex(cph, X, base_cols + [var]), 4),
        "n": int(len(X)),
    })
hr = pd.DataFrame(hr_rows)
hr.to_csv(os.path.join(DATA, "hr_per_sd.csv"), index=False)
print("\nBase-adjusted HR per stated unit:")
print(hr.to_string(index=False))

# also: base model alone, and each candidate's per-SD HR
sd_rows = []
for var, (label, unit) in CANDIDATES.items():
    sub = df[["time_months", "dead", "age", "female", "race", "educ",
              "smoking", "baseline_disease", var]].copy()
    X = design(sub, extra=[var], standardize=[var])
    cph = fit_cph(X, base_cols + [var])
    beta = cph.params_[var]
    se = cph.standard_errors_[var]
    sd_rows.append({"variable": var, "label": label,
                    "sd": round(float(sub[var].std(ddof=0)), 2),
                    "hr_per_sd": round(float(np.exp(beta)), 3),
                    "hr_per_sd_lo": round(float(np.exp(beta - 1.96 * se)), 3),
                    "hr_per_sd_hi": round(float(np.exp(beta + 1.96 * se)), 3),
                    "p": float(cph.summary.loc[var, "p"])})
sd = pd.DataFrame(sd_rows)
sd.to_csv(os.path.join(DATA, "hr_per_sd_only.csv"), index=False)
print("\nBase-adjusted HR per SD:")
print(sd.to_string(index=False))

# ------------------------------------------------- repeated 5-fold CV C-index
MODELS = {
    "base": [],
    "base+grip_combined": ["grip_combined"],
    "base+grip_max": ["grip_max"],
    "base+grip_relative": ["grip_relative"],
    "base+bmi": ["bmi"],
    "base+sbp": ["sbp"],
    "base+pulse": ["pulse"],
    "base+waist": ["waist_cm"],
    "base+strength_any": ["strength_any"],
    "base+vigorous": ["vig_any"],
    "base+all_vitals": ["bmi", "sbp", "pulse", "waist_cm"],
    "base+all_vitals+grip": ["bmi", "sbp", "pulse", "waist_cm",
                             "grip_combined"],
    "base+all_vitals+grip+activity": ["bmi", "sbp", "pulse", "waist_cm",
                                      "grip_combined", "strength_any",
                                      "vig_any"],
    "base+grip+activity": ["grip_combined", "strength_any",
                           "vig_any"],
}


def cv_cindex(extra, seeds=(0, 1, 2)):
    """Repeated 5-fold CV Harrell's C. Standardization refit per fold."""
    cols_all = base_cols + extra
    scores = []
    all_cands = ["grip_combined", "grip_max", "grip_relative", "bmi",
                 "sbp", "pulse", "waist_cm", "strength_any", "vig_any"]
    d = df[["time_months", "dead", "age", "female", "race", "educ",
            "smoking", "baseline_disease"] + all_cands].dropna().copy()
    d = d[["time_months", "dead", "age", "female", "race", "educ",
           "smoking", "baseline_disease"] + extra]
    for seed in seeds:
        kf = KFold(n_splits=5, shuffle=True, random_state=seed)
        for tr, te in kf.split(d):
            trd, ted = d.iloc[tr], d.iloc[te]
            Xtr = design(trd, extra=extra)
            Xte = design(ted, extra=extra)
            # standardize continuous extras using TRAIN fold only
            for c in extra:
                mu, sdv = Xtr[c].mean(), Xtr[c].std(ddof=0)
                Xtr[c] = (Xtr[c] - mu) / sdv
                Xte[c] = (Xte[c] - mu) / sdv
            ok = Xtr.dropna().index.intersection(Xte.dropna().index)
            Xtr, Xte = Xtr.dropna(), Xte.dropna()
            cph = fit_cph(Xtr, cols_all)
            scores.append(cindex(cph, Xte, cols_all))
    return float(np.mean(scores)), float(np.std(scores) / np.sqrt(len(scores)))


cv_rows = []
for name, extra in MODELS.items():
    m, se = cv_cindex(extra)
    cv_rows.append({"model": name, "cv_cindex": round(m, 4),
                    "se": round(se, 4)})
    print(f"CV {name:38s} C = {m:.4f} (SE {se:.4f})")
cv = pd.DataFrame(cv_rows)
cv.to_csv(os.path.join(DATA, "cv_cindex.csv"), index=False)

# ------------------------------------------------------- grip-age pricing
# From the base+grip model (raw units): years of aging equivalent to a
# 5/10/15 kg weaker grip = |beta_grip| * dkg / beta_age.
pricing = []
for sex_label, sub in [("all", df), ("men", df[df["female"] == 0]),
                       ("women", df[df["female"] == 1])]:
    X = design(sub, extra=["grip_combined"])
    cols = base_cols + ["grip_combined"]
    if sex_label != "all":
        cols = [c for c in cols if c != "female"]
    cph = fit_cph(X, cols)
    b_age = cph.params_["age"]
    b_grip = cph.params_["grip_combined"]
    pricing.append({
        "group": sex_label, "n": int(len(X)),
        "beta_age_per_year": round(float(b_age), 4),
        "beta_grip_per_kg": round(float(b_grip), 4),
        "hr_age_per_year": round(float(np.exp(b_age)), 3),
        "hr_grip_per_5kg": round(float(np.exp(b_grip * 5)), 3),
        "years_per_5kg_weaker": round(float(5 * abs(b_grip) / b_age), 2),
        "years_per_10kg_weaker": round(float(10 * abs(b_grip) / b_age), 2),
        "kg_to_buy_back_one_year": round(float(b_age / abs(b_grip)), 2),
    })
pricing = pd.DataFrame(pricing)
pricing.to_csv(os.path.join(DATA, "grip_years.csv"), index=False)
print("\nGrip-age pricing:")
print(pricing.to_string(index=False))

# ------------------------------------------------- quintiles + dose response
q_rows = []
for sex_label, sub in [("men", df[df["female"] == 0]),
                       ("women", df[df["female"] == 1])]:
    s = sub.copy()
    s["grip_q"] = pd.qcut(s["grip_combined"], 5, labels=False,
                          duplicates="drop") + 1
    X = design(s, extra=["grip_q"])
    # dummies for Q1..Q4 vs Q5 (strongest)
    for q in [1, 2, 3, 4]:
        X[f"q{q}"] = (s["grip_q"] == q).astype(int)
    cols = base_cols + ["q1", "q2", "q3", "q4"]
    cols = [c for c in cols if c != "female"]
    cph = fit_cph(X, cols)
    for q in [1, 2, 3, 4]:
        beta, se = cph.params_[f"q{q}"], cph.standard_errors_[f"q{q}"]
        g = s[s["grip_q"] == q]
        q_rows.append({
            "sex": sex_label, "quintile": q,
            "grip_median": round(float(g["grip_combined"].median()), 1),
            "grip_range": f"{g['grip_combined'].min():.0f}-"
                          f"{g['grip_combined'].max():.0f}",
            "n": int(len(g)), "deaths": int(g["dead"].sum()),
            "hr_vs_strongest": round(float(np.exp(beta)), 2),
            "hr_lo": round(float(np.exp(beta - 1.96 * se)), 2),
            "hr_hi": round(float(np.exp(beta + 1.96 * se)), 2),
            "p": float(cph.summary.loc[f"q{q}", "p"]),
        })
    g5 = s[s["grip_q"] == 5]
    q_rows.append({"sex": sex_label, "quintile": 5,
                   "grip_median": round(float(g5["grip_combined"].median()), 1),
                   "grip_range": f"{g5['grip_combined'].min():.0f}-"
                                 f"{g5['grip_combined'].max():.0f}",
                   "n": int(len(g5)), "deaths": int(g5["dead"].sum()),
                   "hr_vs_strongest": 1.0, "hr_lo": 1.0, "hr_hi": 1.0,
                   "p": np.nan})
q = pd.DataFrame(q_rows)
q.to_csv(os.path.join(DATA, "quintiles.csv"), index=False)
print("\nSex-specific grip quintiles (HR vs strongest quintile):")
print(q.to_string(index=False))

# ------------------------------------------------------------ interactions
inter = []
X = design(df, extra=["grip_combined"])
X["grip_x_female"] = X["grip_combined"] * X["female"]
X["age60"] = (X["age"] >= 60).astype(int)
X["grip_x_age60"] = X["grip_combined"] * X["age60"]
for cols, tag in [(base_cols + ["grip_combined", "grip_x_female"],
                   "grip x female"),
                  (base_cols + ["grip_combined", "age60", "grip_x_age60"],
                   "grip x age60+")]:
    cph = fit_cph(X, cols)
    last = cols[-1]
    inter.append({"interaction": tag,
                  "beta": round(float(cph.params_[last]), 4),
                  "p": float(cph.summary.loc[last, "p"])})
print("\nInteractions:")
print(pd.DataFrame(inter).to_string(index=False))

# ------------------------------------------- does strength training explain it?
X = design(df, extra=["grip_combined", "strength_any", "vig_any"])
cph_full = fit_cph(X, base_cols + ["grip_combined", "strength_any",
                                   "vig_any"])
X0 = design(df, extra=["grip_combined"])
cph_g = fit_cph(X0, base_cols + ["grip_combined"])
Xa = design(df, extra=["strength_any", "vig_any"])
cph_a = fit_cph(Xa, base_cols + ["strength_any", "vig_any"])
print("\nStrength-training mediation:")
print(f"  grip beta alone:        {cph_g.params_['grip_combined']:.4f}")
print(f"  grip beta + activity:   {cph_full.params_['grip_combined']:.4f}")
print(f"  strength_any HR (yes vs no): "
      f"{np.exp(cph_a.params_['strength_any']):.3f} "
      f"(p={cph_a.summary.loc['strength_any', 'p']:.3f})")
print(f"  vigorous HR (any vs none): "
      f"{np.exp(cph_a.params_['vig_any']):.3f} "
      f"(p={cph_a.summary.loc['vig_any', 'p']:.3f})")

summary = {
    "n": int(len(df)), "deaths": int(df["dead"].sum()),
    "hr_per_sd": sd.set_index("variable")["hr_per_sd"].to_dict(),
    "cv_cindex": cv.set_index("model")["cv_cindex"].to_dict(),
    "grip_years": pricing.set_index("group")[
        ["years_per_5kg_weaker", "years_per_10kg_weaker",
         "kg_to_buy_back_one_year"]].to_dict(orient="index"),
    "interactions": inter,
    "grip_beta_alone": float(cph_g.params_["grip_combined"]),
    "grip_beta_with_activity": float(cph_full.params_["grip_combined"]),
}
with open(os.path.join(DATA, "analysis.json"), "w") as fh:
    json.dump(summary, fh, indent=2)
print("\nanalysis.json written.")
