#!/usr/bin/env python3
"""
The Peak Is a Start Date — within-lifter career analysis of OpenIPF powerlifting.

Question: the cross-sectional age curve says strength peaks at ~26 and fades.
But that curve compares different people at each age. This pipeline follows the
SAME lifters across their careers and asks: when does a lifter actually peak,
how fast do they decline after their own peak, and what makes them quit?

Data: OpenIPF bulk CSV (IPF affiliates), Raw, full-power (SBD) entries only.
Careers are Name+Sex+Country segments, split when reported age is inconsistent
with elapsed calendar time (|age change - years elapsed| > 2.5), which breaks
most same-name collisions into separate careers.

Reproduce: python3 src/download.py && python3 src/analyze.py
"""
import glob, json, os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")
CHARTS = os.path.join(ROOT, "charts")
os.makedirs(OUT, exist_ok=True)
os.makedirs(CHARTS, exist_ok=True)
rng = np.random.default_rng(42)
R = {}

# ---------------------------------------------------------------- load & clean
f = sorted(glob.glob(os.path.join(DATA, "openipf-*", "openipf-*.csv")))[-1]
R["data_file"] = os.path.basename(f)
cols = ["Name", "Sex", "Event", "Equipment", "Age", "BodyweightKg", "TotalKg",
        "Goodlift", "Country", "Date"]
df = pd.read_csv(f, usecols=cols, low_memory=False)
n_raw = len(df)
df = df[(df.Event == "SBD") & (df.Equipment == "Raw") & df.TotalKg.notna()
        & (df.TotalKg > 0) & df.Goodlift.notna() & (df.Goodlift > 0)
        & df.Age.notna() & df.Date.notna() & df.Sex.isin(["M", "F"])]
df["Date"] = pd.to_datetime(df.Date)
df = df[(df.Date.dt.year >= 1990) & (df.Age >= 14) & (df.Age <= 90)]
df = df.sort_values(["Name", "Sex", "Country", "Date"]).reset_index(drop=True)
R["entries"] = int(len(df)); R["entries_raw_file"] = int(n_raw)

# ------------------------------------------------------- career segmentation
df["prev_date"] = df.groupby(["Name", "Sex", "Country"]).Date.shift()
df["prev_age"] = df.groupby(["Name", "Sex", "Country"]).Age.shift()
elapsed = (df.Date - df.prev_date).dt.days / 365.25
inconsistent = ((df.Age - df.prev_age) - elapsed).abs() > 2.5
df["seg_break"] = (df.prev_date.isna() | inconsistent).astype(int)
df["seg"] = df.groupby(["Name", "Sex", "Country"]).seg_break.cumsum() - 1
df["career_id"] = (df.Name + "|" + df.Sex + "|" + df.Country.fillna("?") + "|"
                   + df.seg.astype(str))
df = df.drop(columns=["prev_date", "prev_age", "seg_break", "seg"])
R["careers_total"] = int(df.career_id.nunique())
df.to_parquet(os.path.join(DATA, "careers.parquet"))

g = df.groupby("career_id")
career = g.agg(sex=("Sex", "first"), n_meets=("Date", "size"),
               first_date=("Date", "min"), last_date=("Date", "max"),
               first_age=("Age", "first"), best_gl=("Goodlift", "max")).reset_index()
career["span_yrs"] = (career.last_date - career.first_date).dt.days / 365.25
peak_idx = df.loc[g.Goodlift.idxmax()].set_index("career_id")
career = career.set_index("career_id").join(
    peak_idx[["Age", "Date"]].rename(columns={"Age": "peak_age", "Date": "peak_date"}))
career["yrs_to_peak"] = (career.peak_date - career.first_date).dt.days / 365.25
career["yrs_after_peak_obs"] = (career.last_date - career.peak_date).dt.days / 365.25

# ------------------------------------------------- Part A: cross-section curve
xs = df.groupby("Age").Goodlift.median()
cnt = df.groupby("Age").size()
ages = [a for a in xs.index if cnt[a] >= 100 and 18 <= a <= 75]
xs_med = xs[ages]; xs_peak_age = float(xs_med.idxmax()); xs_peak = float(xs_med.max())
xs_ret = (xs_med / xs_peak * 100)
R["xsection"] = {"peak_age": xs_peak_age,
                 "retained": {str(int(a)): round(float(xs_ret[a]), 1) for a in [40, 45, 50, 55, 60, 65, 70] if a in xs_ret.index}}

# ------------------------------------------------- Part B: when do lifters peak?
long = career[(career.n_meets >= 5) & (career.span_yrs >= 8)].copy()
R["long_careers"] = int(len(long))
def slope_ci(x, y, B=500):
    x = np.asarray(x, float); y = np.asarray(y, float)
    sl = np.polyfit(x, y, 1)[0]; bs = []
    for _ in range(B):
        i = rng.integers(0, len(x), len(x))
        if np.std(x[i]) > 0: bs.append(np.polyfit(x[i], y[i], 1)[0])
    return float(sl), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
fit = long[(long.first_age >= 16) & (long.first_age <= 60)]
sl, lo, hi = slope_ci(fit.first_age, fit.peak_age)
ic = float(np.polyfit(fit.first_age, fit.peak_age, 1)[1])
R["peak_regression"] = {"slope": round(sl, 3), "slope_ci": [round(lo, 3), round(hi, 3)],
                        "intercept": round(ic, 2), "n": int(len(fit))}
bands = [(16, 20), (20, 25), (25, 30), (30, 35), (35, 40), (40, 45), (45, 50), (50, 60)]
band_rows = []
for a, b in bands:
    s = long[(long.first_age >= a) & (long.first_age < b)]
    if len(s) >= 25:
        band_rows.append({"band": f"{a}-{b-1}", "n": int(len(s)),
                          "peak_age_med": round(float(s.peak_age.median()), 1),
                          "yrs_to_peak_med": round(float(s.yrs_to_peak.median()), 1),
                          "peak_gl_med": round(float(s.best_gl.median()), 1)})
R["peak_by_start_band"] = band_rows
by_sex = {}
for sx in ["M", "F"]:
    s = fit[fit.sex == sx]
    if len(s) >= 100:
        slx, lox, hix = slope_ci(s.first_age, s.peak_age, B=300)
        by_sex[sx] = {"slope": round(slx, 3), "ci": [round(lox, 3), round(hix, 3)], "n": int(len(s)),
                      "yrs_to_peak_med": round(float(s.yrs_to_peak.median()), 1)}
R["peak_regression_by_sex"] = by_sex
# finished-career sensitivity (last meet <= 2022: peak unlikely still ahead)
fin = fit[fit.last_date <= "2022-12-31"]
sl2, lo2, hi2 = slope_ci(fin.first_age, fin.peak_age, B=300)
R["peak_regression_finished"] = {"slope": round(sl2, 3), "ci": [round(lo2, 3), round(hi2, 3)], "n": int(len(fin))}
# how long careers last, and share whose peak is their LAST observed phase
R["career_span_med"] = round(float(long.span_yrs.median()), 1)
R["peak_in_final_year_share"] = round(float((long.yrs_after_peak_obs < 1).mean()), 3)

# ------------------------------------- Part C: within-lifter post-peak decline
# annual best per career
df["year"] = df.Date.dt.year
ann = df.groupby(["career_id", "year"]).Goodlift.max().rename("gl").reset_index()
ann = ann.merge(career[["first_date"]].reset_index(), on="career_id")
ann["year0"] = ann.first_date.dt.year
ann["career_year"] = ann.year - ann.year0
pk = career.reset_index()[["career_id", "peak_date", "best_gl"]]
ann = ann.merge(pk, on="career_id")
ann["yrs_since_peak"] = ann.year - ann.peak_date.dt.year
ann["retained"] = ann.gl / ann.best_gl * 100
hor = {}
for h in [5, 10, 15]:
    s = ann[(ann.yrs_since_peak >= h - 1) & (ann.yrs_since_peak <= h + 1)]
    s = s.groupby("career_id").retained.max()
    if len(s) >= 30: hor[str(h)] = {"n": int(len(s)), "retained_med": round(float(s.median()), 1)}
R["retained_post_peak"] = hor
# retained AT ages (within-lifter): lifters observed at that age, vs their own peak
df_pk = df.merge(pk, on="career_id")
df_pk["retained"] = df_pk.Goodlift / df_pk.best_gl * 100
at_age = {}
for a in [50, 60, 70]:
    s = df_pk[(df_pk.Age >= a - 1) & (df_pk.Age <= a + 1)]
    s = s[s.career_id.isin(long.index)]  # long careers only
    best_at = s.groupby("career_id").retained.max()
    if len(best_at) >= 30:
        at_age[str(a)] = {"n": int(len(best_at)), "retained_med": round(float(best_at.median()), 1),
                          "xsection_retained": R["xsection"]["retained"].get(str(a))}
R["retained_at_age_within"] = at_age

# ------------------------------------------------------- Part D: why lifters quit
d = df.sort_values(["career_id", "Date"]).copy()
gd = d.groupby("career_id")
d["prior_best"] = gd.Goodlift.apply(lambda s: s.cummax().shift()).reset_index(level=0, drop=True)
d["meets_so_far"] = gd.cumcount() + 1
d["career_year"] = (d.Date - gd.Date.transform("min")).dt.days / 365.25
d["days_since_last"] = (d.Date - gd.Date.shift()).dt.days
d["next_date"] = gd.Date.shift(-1)
d["vs_pb_pct"] = (d.Goodlift / d.prior_best - 1) * 100
panel = d[(d.meets_so_far >= 2) & d.prior_best.notna()
          & (d.Date <= "2023-10-17")].copy()  # 3y follow-up observable
panel["exit3"] = (panel.next_date.isna()
                  | ((panel.next_date - panel.Date).dt.days > 3 * 365.25)).astype(int)
R["exit_panel_n"] = int(len(panel)); R["exit_base_rate"] = round(float(panel.exit3.mean()), 3)
bins = [(-100, -10), (-10, -5), (-5, -2), (-2, 0), (0, 100)]
er = []
for a, b in bins:
    s = panel[(panel.vs_pb_pct > a) & (panel.vs_pb_pct <= b)]
    if len(s) >= 200:
        er.append({"bin": f"{a} to {b}% vs PB" if a != 0 else "new PR",
                   "n": int(len(s)), "exit_rate": round(float(s.exit3.mean()), 3)})
R["exit_by_vs_pb"] = er
pr = panel[panel.vs_pb_pct > 0]; bad = panel[panel.vs_pb_pct <= -5]
R["exit_pr_vs_bad"] = {"pr_exit": round(float(pr.exit3.mean()), 3), "pr_n": int(len(pr)),
                       "bad_exit": round(float(bad.exit3.mean()), 3), "bad_n": int(len(bad))}

import xgboost as xgb, shap
feats = ["vs_pb_pct", "Age", "career_year", "meets_so_far", "days_since_last",
         "Goodlift", "BodyweightKg"]
X = panel[feats].fillna({"days_since_last": 365}).copy()
X["sex_m"] = (panel.Sex == "M").astype(int); feats2 = feats + ["sex_m"]
y = panel.exit3.values
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
Xtr, Xte, ytr, yte = train_test_split(X[feats2], y, test_size=0.3, random_state=42, stratify=y)
m = xgb.XGBClassifier(n_estimators=400, max_depth=3, learning_rate=0.05,
                      subsample=0.9, colsample_bytree=0.9, eval_metric="logloss")
m.fit(Xtr, ytr)
auc = float(roc_auc_score(yte, m.predict_proba(Xte)[:, 1]))
expl = shap.TreeExplainer(m)
sv = np.abs(expl.shap_values(Xte)).mean(axis=0)
R["exit_model"] = {"auc": round(auc, 3),
                   "shap": {f: round(float(v), 4) for f, v in sorted(zip(feats2, sv), key=lambda t: -t[1])}}
np.save(os.path.join(OUT, "exit_shap.npy"), sv)
panel.to_parquet(os.path.join(DATA, "exit_panel.parquet"))

# ------------------------------------------- Part E: early-career velocity
vel = []
for a, b in bands:
    ids = career[(career.first_age >= a) & (career.first_age < b)].index
    sub = ann[ann.career_id.isin(ids)]
    p0 = sub[sub.career_year == 0].set_index("career_id").gl
    p3 = sub[(sub.career_year >= 2) & (sub.career_year <= 3)].groupby("career_id").gl.max()
    j = pd.concat([p0.rename("g0"), p3.rename("g3")], axis=1, join="inner").dropna()
    if len(j) >= 30:
        gain = (j.g3 / j.g0 - 1) * 100 / 3
        vel.append({"band": f"{a}-{b-1}", "n": int(len(j)), "gain_pct_per_yr_med": round(float(gain.median()), 1)})
R["early_velocity"] = vel

# explorer payload: peak prediction by start band + retained-at-age
explorer = {"bands": band_rows, "at_age": at_age, "slope": R["peak_regression"]["slope"],
            "intercept": R["peak_regression"]["intercept"]}
with open(os.path.join(OUT, "explorer_model.json"), "w") as fh: json.dump(explorer, fh, indent=1)
with open(os.path.join(OUT, "results.json"), "w") as fh: json.dump(R, fh, indent=1)
long.reset_index().to_csv(os.path.join(OUT, "long_careers.csv"), index=False)
print(json.dumps(R, indent=1, default=str))
