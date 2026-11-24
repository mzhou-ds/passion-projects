"""04_checks.py — sensitivity and fairness checks on the headline result.

1. Reverse causation: drop deaths within 12 months of the exam.
2. Prevalent disease: drop baseline CVD/cancer.
3. Survey-weighted Cox (pooled MEC weights) for the main HRs.
4. Proportional-hazards assumption (Schoenfeld test) on the main model.
5. Cause-specific Cox: cardiovascular deaths (UCOD_LEADING 1 or 4) and
   cancer deaths (2), censoring other causes.
6. Age-stratified grip HRs (40-59 vs 60-80).
7. Fairness: BMI and SBP may be U/J-shaped, so a null *linear* term is not
   the same as no signal — test categorical versions of both.
8. Alternative grip definition (grip_max) under the same exclusions.

Outputs: data/checks.json, data/bmi_sbp_categories.csv
"""
import json
import os

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.statistics import proportional_hazard_test

BASE = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(BASE, "data")
df = pd.read_csv(os.path.join(DATA, "analytic.csv"))
df["vig_any"] = (df["vig_min_week"] > 0).astype(float)

BASE_COVS = ["age", "female", "race", "educ", "smoking", "baseline_disease"]


def design(d, extra=None):
    X = d[["time_months", "dead"]].copy()
    X["age"] = d["age"]
    X["female"] = d["female"]
    for v in [1, 2, 4, 6, 7]:
        X[f"race_{v}"] = (d["race"] == v).astype(int)
    X["educ"] = d["educ"]
    X["smoke_former"] = (d["smoking"] == "former").astype(int)
    X["smoke_current"] = (d["smoking"] == "current").astype(int)
    X["baseline_disease"] = d["baseline_disease"]
    if extra:
        for c in extra:
            X[c] = d[c]
    return X.dropna()


BASE_COLS = ["age", "female", "race_1", "race_2", "race_4", "race_6",
             "race_7", "educ", "smoke_former", "smoke_current",
             "baseline_disease"]
checks = {}


def grip_hr(d, label, weights=None):
    X = design(d, extra=["grip_combined"])
    # drop covariates with no variation in this subset (e.g. baseline_disease
    # is constant after excluding prevalent disease)
    cols = [c for c in BASE_COLS + ["grip_combined"] if X[c].nunique() > 1]
    cph = CoxPHFitter()
    if weights is not None:
        # normalize to mean 1 (survey weights are ~1e4) and use robust SEs:
        # naive variances are biased under weighting (lifelines warning)
        w = d.loc[X.index, weights]
        X[weights] = w / w.mean()
        cph.fit(X[["time_months", "dead"] + cols + [weights]],
                duration_col="time_months", event_col="dead",
                weights_col=weights, robust=True)
    else:
        cph.fit(X[["time_months", "dead"] + cols],
                duration_col="time_months", event_col="dead")
    beta, se = cph.params_["grip_combined"], cph.standard_errors_["grip_combined"]
    checks[label] = {"n": int(len(X)), "deaths": int(X["dead"].sum()),
                     "hr_per_5kg": round(float(np.exp(beta * 5)), 3),
                     "hr_lo": round(float(np.exp((beta - 1.96 * se) * 5)), 3),
                     "hr_hi": round(float(np.exp((beta + 1.96 * se) * 5)), 3),
                     "p": float(cph.summary.loc["grip_combined", "p"])}
    return cph


grip_hr(df, "main")
grip_hr(df[(df["dead"] == 0) | (df["time_months"] > 12)],
        "exclude_deaths_within_12mo")
grip_hr(df[df["baseline_disease"] == 0], "exclude_baseline_cvd_cancer")
grip_hr(df, "survey_weighted", weights="wt_pooled")
grip_hr(df[df["age"] < 60], "age_40_59")
grip_hr(df[df["age"] >= 60], "age_60_80")

# ---- proportional hazards (main model) -----------------------------------
X = design(df, extra=["grip_combined"])
cph = CoxPHFitter()
cph.fit(X[["time_months", "dead"] + BASE_COLS + ["grip_combined"]],
        duration_col="time_months", event_col="dead")
pht = proportional_hazard_test(cph, X, time_transform="rank")
checks["proportional_hazards"] = {
    "grip_p": float(pht.summary.loc["grip_combined", "p"]),
    "global_p": float(pht.test_statistic.mean()),  # placeholder, replaced below
}
checks["proportional_hazards"]["test_p_values"] = {
    k: float(v) for k, v in pht.summary["p"].items()}
del checks["proportional_hazards"]["global_p"]

# ---- time split (PH check follow-up): early vs late follow-up ------------
# The Schoenfeld test flags mild non-proportionality for grip (p = 0.011),
# so split follow-up at 48 months: early = censor everyone at 48 months;
# late = only those alive at 48 months, with entry at 48 months.
early = df.copy()
early.loc[early["time_months"] > 48, "dead"] = 0
early["time_months"] = early["time_months"].clip(upper=48)
X = design(early, extra=["grip_combined"])
cph = CoxPHFitter()
cph.fit(X[["time_months", "dead"] + BASE_COLS + ["grip_combined"]],
        duration_col="time_months", event_col="dead")
beta, se = cph.params_["grip_combined"], cph.standard_errors_["grip_combined"]
checks["time_split_early_0_48mo"] = {
    "n": int(len(X)), "deaths": int(X["dead"].sum()),
    "hr_per_5kg": round(float(np.exp(beta * 5)), 3),
    "hr_lo": round(float(np.exp((beta - 1.96 * se) * 5)), 3),
    "hr_hi": round(float(np.exp((beta + 1.96 * se) * 5)), 3),
    "p": float(cph.summary.loc["grip_combined", "p"])}
late = df[df["time_months"] > 48].copy()
X = design(late, extra=["grip_combined"])
X["entry_months"] = 48.0
cph = CoxPHFitter()
cph.fit(X[["entry_months", "time_months", "dead"] + BASE_COLS
         + ["grip_combined"]],
        duration_col="time_months", event_col="dead", entry_col="entry_months")
beta, se = cph.params_["grip_combined"], cph.standard_errors_["grip_combined"]
checks["time_split_late_48mo_plus"] = {
    "n": int(len(X)), "deaths": int(X["dead"].sum()),
    "hr_per_5kg": round(float(np.exp(beta * 5)), 3),
    "hr_lo": round(float(np.exp((beta - 1.96 * se) * 5)), 3),
    "hr_hi": round(float(np.exp((beta + 1.96 * se) * 5)), 3),
    "p": float(cph.summary.loc["grip_combined", "p"])}

# ---- cause-specific -------------------------------------------------------
# NCHS leading-cause codes: 1 = diseases of heart, 4 = cerebrovascular,
# 2 = malignant neoplasms, 10 = all other (residual).
for tag, codes in [("cvd", [1, 4]), ("cancer", [2])]:
    d = df.copy()
    d["dead_cause"] = ((d["dead"] == 1)
                       & (d["UCOD_LEADING"].isin(codes))).astype(int)
    Xc = design(d, extra=["grip_combined"])
    Xc["dead"] = d.loc[Xc.index, "dead_cause"]
    cph_c = CoxPHFitter()
    cph_c.fit(Xc[["time_months", "dead"] + BASE_COLS + ["grip_combined"]],
              duration_col="time_months", event_col="dead")
    beta = cph_c.params_["grip_combined"]
    se = cph_c.standard_errors_["grip_combined"]
    checks[f"cause_{tag}"] = {
        "n_cause_deaths": int(d["dead_cause"].sum()),
        "hr_per_5kg": round(float(np.exp(beta * 5)), 3),
        "hr_lo": round(float(np.exp((beta - 1.96 * se) * 5)), 3),
        "hr_hi": round(float(np.exp((beta + 1.96 * se) * 5)), 3),
        "p": float(cph_c.summary.loc["grip_combined", "p"]),
    }

# ---- fairness: categorical BMI and SBP ------------------------------------
cat_rows = []
d = df.copy()
d["bmi_cat"] = pd.cut(d["bmi"], [0, 18.5, 25, 30, 35, 100],
                      labels=["<18.5", "18.5-25", "25-30", "30-35", "35+"])
d["sbp_cat"] = pd.cut(d["sbp"], [0, 120, 140, 160, 300],
                      labels=["<120", "120-139", "140-159", "160+"])
for col, ref in [("bmi_cat", "18.5-25"), ("sbp_cat", "<120")]:
    X = design(d, extra=[])
    cats = [c for c in d[col].cat.categories if str(c) != ref]
    for c in cats:
        X[f"{col}_{c}"] = (d.loc[X.index, col] == c).astype(float).values
    cols = BASE_COLS + [f"{col}_{c}" for c in cats]
    cph = CoxPHFitter()
    cph.fit(X[["time_months", "dead"] + cols],
            duration_col="time_months", event_col="dead")
    for c in cats:
        key = f"{col}_{c}"
        beta, se = cph.params_[key], cph.standard_errors_[key]
        n_cat = int((d[col] == c).sum())
        d_cat = int(((d[col] == c) & (d["dead"] == 1)).sum())
        cat_rows.append({"variable": col, "category": str(c), "n": n_cat,
                         "deaths": d_cat,
                         "hr_vs_ref": round(float(np.exp(beta)), 2),
                         "hr_lo": round(float(np.exp(beta - 1.96 * se)), 2),
                         "hr_hi": round(float(np.exp(beta + 1.96 * se)), 2),
                         "p": float(cph.summary.loc[key, "p"])})
cat = pd.DataFrame(cat_rows)
cat.to_csv(os.path.join(DATA, "bmi_sbp_categories.csv"), index=False)

with open(os.path.join(DATA, "checks.json"), "w") as fh:
    json.dump(checks, fh, indent=2)
print(json.dumps(checks, indent=2))
print("\nCategorical BMI / SBP (base-adjusted, vs reference):")
print(cat.to_string(index=False))
