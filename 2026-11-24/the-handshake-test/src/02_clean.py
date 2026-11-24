"""02_clean.py — build the analytic cohort from NHANES 2011-2014 + linked mortality.

Cohort: adults 40-80 with a complete grip-strength exam, linked to mortality
follow-up through Dec 31, 2019 (NCHS public-use LMF, 2019 release).

Grip variables (NHANES MGX: 3 trials per hand, alternating):
- hand1_max / hand2_max: best valid trial per hand (values < 5 kg treated as
  invalid; one 5.4e-79 artifact exists in the raw file)
- grip_combined = hand1_max + hand2_max  (literature standard)
- grip_max = max(hand1_max, hand2_max)   (EWGSOP2 sarcopenia definition)
- grip_relative = grip_combined / bodyweight

Other vitals: BMI (BMXBMI), systolic BP (mean of BPXSY1-3), resting pulse
(BPXPLS), waist (BMXWAIST). Covariates: age, sex, race (RIDRETH3), education
(DMDEDUC2), smoking (SMQ020/SMQ040), baseline CVD/cancer (MCQ160B-F, MCQ220),
muscle-strengthening days/week (PAQ650), vigorous recreational minutes/week
(PAQ665 x PAQ670). Survey weight: WTMEC2YR / 2 (pooled 2 cycles).

Mortality layout (SAS_ReadInProgramAllSurveys.sas, NHANES section):
SEQN cols 1-6, ELIGSTAT col 15, MORTSTAT col 16, UCOD_LEADING cols 17-19,
PERMTH_INT cols 43-45, PERMTH_EXM cols 46-48. MORTSTAT 1 = deceased,
0 = assumed alive; '.' = not linkage-eligible.

Output: data/analytic.csv, data/sample_flow.json
"""
import json
import os

import numpy as np
import pandas as pd

BASE = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(BASE, "data", "raw")
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)

FLOW = {}


def read_xpt(name):
    return pd.read_sas(os.path.join(RAW, f"{name}.xpt"))


def load_mort(fname):
    m = pd.read_fwf(
        os.path.join(RAW, fname),
        colspecs=[(0, 6), (14, 15), (15, 16), (16, 19), (42, 45), (45, 48)],
        names=["SEQN", "ELIGSTAT", "MORTSTAT", "UCOD_LEADING",
               "PERMTH_INT", "PERMTH_EXM"],
    )
    for c in m.columns:
        m[c] = pd.to_numeric(m[c], errors="coerce")
    return m


def best_trial(df, cols):
    """Best valid trial (>= 5 kg) across listed columns, NaN if none valid."""
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    sub = sub.where(sub >= 5.0)
    return sub.max(axis=1)


# ---- load and pool cycles -----------------------------------------------
mgx = pd.concat([read_xpt("MGX_G"), read_xpt("MGX_H")], ignore_index=True)
demo = pd.concat([read_xpt("DEMO_G"), read_xpt("DEMO_H")], ignore_index=True)
bmx = pd.concat([read_xpt("BMX_G"), read_xpt("BMX_H")], ignore_index=True)
bpx = pd.concat([read_xpt("BPX_G"), read_xpt("BPX_H")], ignore_index=True)
smq = pd.concat([read_xpt("SMQ_G"), read_xpt("SMQ_H")], ignore_index=True)
paq = pd.concat([read_xpt("PAQ_G"), read_xpt("PAQ_H")], ignore_index=True)
mcq = pd.concat([read_xpt("MCQ_G"), read_xpt("MCQ_H")], ignore_index=True)
mort = pd.concat([
    load_mort("NHANES_2011_2012_MORT_2019_PUBLIC.dat"),
    load_mort("NHANES_2013_2014_MORT_2019_PUBLIC.dat"),
], ignore_index=True)

FLOW["mgx_rows"] = int(len(mgx))
FLOW["mort_rows"] = int(len(mort))
FLOW["mort_deaths_total"] = int((mort["MORTSTAT"] == 1).sum())

# ---- grip ---------------------------------------------------------------
df = mgx[["SEQN", "MGDEXSTS"]].copy()
df["hand1_max"] = best_trial(mgx, ["MGXH1T1", "MGXH1T2", "MGXH1T3"])
df["hand2_max"] = best_trial(mgx, ["MGXH2T1", "MGXH2T2", "MGXH2T3"])
df["grip_combined"] = df["hand1_max"] + df["hand2_max"]
df["grip_max"] = df[["hand1_max", "hand2_max"]].max(axis=1)
FLOW["grip_complete_exam"] = int(df["MGDEXSTS"].eq(1).sum())
FLOW["grip_combined_nonnull"] = int(df["grip_combined"].notna().sum())

# ---- demographics -------------------------------------------------------
d = demo[["SEQN", "RIDAGEYR", "RIAGENDR", "RIDRETH3", "DMDEDUC2",
          "WTMEC2YR"]].rename(columns={
              "RIDAGEYR": "age", "RIAGENDR": "sex", "RIDRETH3": "race",
              "DMDEDUC2": "educ", "WTMEC2YR": "wtmec"})
df = df.merge(d, on="SEQN", how="left")

# ---- body measures / vitals ---------------------------------------------
b = bmx[["SEQN", "BMXBMI", "BMXWT", "BMXWAIST"]].rename(columns={
    "BMXBMI": "bmi", "BMXWT": "weight_kg", "BMXWAIST": "waist_cm"})
df = df.merge(b, on="SEQN", how="left")
p = bpx[["SEQN", "BPXSY1", "BPXSY2", "BPXSY3", "BPXDI1", "BPXDI2",
         "BPXDI3", "BPXPLS"]].copy()
p["sbp"] = p[["BPXSY1", "BPXSY2", "BPXSY3"]].mean(axis=1)
p["dbp"] = p[["BPXDI1", "BPXDI2", "BPXDI3"]].mean(axis=1)
df = df.merge(p[["SEQN", "sbp", "dbp", "BPXPLS"]].rename(
    columns={"BPXPLS": "pulse"}), on="SEQN", how="left")

# ---- smoking ------------------------------------------------------------
s = smq[["SEQN", "SMQ020", "SMQ040"]].copy()
s["smoking"] = np.where(s["SMQ040"].isin([1, 2]), "current",
                np.where((s["SMQ020"] == 1) & (s["SMQ040"] == 3), "former",
                np.where(s["SMQ020"] == 2, "never", np.nan)))
df = df.merge(s[["SEQN", "smoking"]], on="SEQN", how="left")

# ---- activity -----------------------------------------------------------
# PAQ650 is a YES/NO item in these cycles (1 = did any muscle-strengthening
# activity in past 30 days, 2 = did not) — there is no days/week variable.
# PAQ665 = vigorous recreational days/week; PAQ670 = minutes/day (skipped,
# hence NaN, when days = 0, so fill minutes with 0 there only).
a = paq[["SEQN", "PAQ650", "PAQ665", "PAQ670"]].copy()
a["strength_any"] = np.where(pd.to_numeric(a["PAQ650"], errors="coerce") == 1,
                             1.0, np.where(pd.to_numeric(a["PAQ650"],
                                                         errors="coerce") == 2,
                                           0.0, np.nan))
_days = pd.to_numeric(a["PAQ665"], errors="coerce")
_mins = pd.to_numeric(a["PAQ670"], errors="coerce")
a["vig_min_week"] = _days * _mins.fillna(0)
df = df.merge(a[["SEQN", "strength_any", "vig_min_week"]],
              on="SEQN", how="left")

# ---- baseline disease ----------------------------------------------------
mc = mcq[["SEQN", "MCQ160B", "MCQ160C", "MCQ160D", "MCQ160E", "MCQ160F",
          "MCQ220"]].copy()
cvd_cols = ["MCQ160B", "MCQ160C", "MCQ160D", "MCQ160E", "MCQ160F"]
mc["baseline_cvd"] = mc[cvd_cols].eq(1).any(axis=1).astype(float)
mc["baseline_cancer"] = mc["MCQ220"].eq(1).astype(float)
mc["baseline_disease"] = ((mc["baseline_cvd"] == 1)
                          | (mc["baseline_cancer"] == 1)).astype(float)
df = df.merge(mc[["SEQN", "baseline_cvd", "baseline_cancer",
                  "baseline_disease"]], on="SEQN", how="left")

# ---- mortality ----------------------------------------------------------
df = df.merge(mort, on="SEQN", how="left")
FLOW["merged_rows"] = int(len(df))

# ---- cohort restrictions -------------------------------------------------
df["age40plus"] = df["age"] >= 40
FLOW["age_40plus"] = int(df["age40plus"].sum())
cohort = df[df["age40plus"]].copy()
FLOW["after_age40"] = int(len(cohort))
cohort = cohort[cohort["ELIGSTAT"] == 1]
FLOW["after_eligibility"] = int(len(cohort))
cohort = cohort[cohort["grip_combined"].notna()]
FLOW["after_grip"] = int(len(cohort))
cohort = cohort[cohort[["bmi", "sbp", "pulse"]].notna().all(axis=1)]
FLOW["after_vitals"] = int(len(cohort))

# ---- derived ------------------------------------------------------------
# DMDEDUC2 = 9 is "don't know" — treat as missing.
cohort["educ"] = cohort["educ"].replace(9, np.nan)
cohort["vig_any"] = (cohort["vig_min_week"] > 0).astype(float)
cohort["grip_relative"] = cohort["grip_combined"] / cohort["weight_kg"]
cohort["female"] = (cohort["sex"] == 2).astype(int)
cohort["dead"] = (cohort["MORTSTAT"] == 1).astype(int)
cohort["time_months"] = cohort["PERMTH_EXM"]
cohort["wt_pooled"] = cohort["wtmec"] / 2.0
cohort["weak_ewgsop"] = np.where(
    cohort["female"] == 0, cohort["grip_max"] < 27, cohort["grip_max"] < 16)
cohort["age_band"] = pd.cut(cohort["age"], [40, 50, 60, 70, 81],
                            labels=["40-49", "50-59", "60-69", "70-80"])
FLOW["cohort_n"] = int(len(cohort))
FLOW["cohort_deaths"] = int(cohort["dead"].sum())
FLOW["cohort_death_rate_pct"] = round(100 * cohort["dead"].mean(), 2)
FLOW["followup_months_median"] = float(cohort["time_months"].median())
FLOW["followup_months_range"] = [float(cohort["time_months"].min()),
                                 float(cohort["time_months"].max())]

cols = ["SEQN", "age", "age_band", "sex", "female", "race", "educ",
        "smoking", "bmi", "weight_kg", "waist_cm", "sbp", "dbp", "pulse",
        "grip_combined", "grip_max", "grip_relative", "hand1_max",
        "hand2_max", "strength_any", "vig_min_week", "vig_any",
        "baseline_cvd", "baseline_cancer", "baseline_disease",
        "weak_ewgsop", "dead", "time_months", "UCOD_LEADING",
        "wt_pooled"]
cohort[cols].to_csv(os.path.join(DATA, "analytic.csv"), index=False)
with open(os.path.join(DATA, "sample_flow.json"), "w") as fh:
    json.dump(FLOW, fh, indent=2)
print(json.dumps(FLOW, indent=2))
