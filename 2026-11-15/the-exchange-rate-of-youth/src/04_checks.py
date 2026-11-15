"""04_checks.py — ground the model in raw numbers before writing anything up.

1. Peak age: where does the model put peak total at fixed bodyweight?
2. Raw check: median total by bodyweight bin within age bands (no model).
3. Honest aging: within-lifter slope using only meets at age >= 45, span >= 5 yr.
4. Sample density by age, so the README can say where the curve is solid.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
DATA = HERE / "data"

curves = pd.read_csv(DATA / "age_curves.csv")
d = pd.read_csv(DATA / "clean_lifts.csv", parse_dates=["Date"])
long_df = pd.read_csv(DATA / "longitudinal.csv")
out = {}

# 1. peak age at reference bodyweight (total only)
for sex, bw in [("M", 90), ("F", 65)]:
    sub = curves[(curves.sex == sex) & (curves.lift == "total")]
    peak = sub.loc[sub.pred_kg.idxmax()]
    out[f"peak_age_{sex}"] = {"age": int(peak.age), "pred_total_kg": float(peak.pred_kg),
                              "bw": bw}

# 2. raw medians: total by BW bin, within age bands
d["bw_bin"] = pd.cut(d["BodyweightKg"], [40, 60, 70, 80, 90, 100, 110, 125, 200],
                     labels=["40-60", "60-70", "70-80", "80-90", "90-100",
                             "100-110", "110-125", "125+"])
d["age_band"] = pd.cut(d["Age"], [14, 29, 39, 49, 59, 85],
                       labels=["15-29", "30-39", "40-49", "50-59", "60+"])
raw = (d.groupby(["Sex", "age_band", "bw_bin"], observed=True)["TotalKg"]
       .agg(["median", "count"]).reset_index())
raw.to_csv(DATA / "raw_medians.csv", index=False)
# headline raw contrast: men 40-49, 80-90kg vs 100-110kg
for sex, band in [("M", "40-49"), ("M", "50-59"), ("F", "40-49")]:
    sub = raw[(raw.Sex == sex) & (raw.age_band == band)]
    out.setdefault("raw_median_check", {})[f"{sex}_{band}"] = {
        str(r.bw_bin): {"median_total": round(float(r.median), 1), "n": int(r.count)}
        for r in sub.itertuples() if r.count >= 30}

# 3. honest aging: meets at age >= 45 only
rows = []
g = d[d["Age"] >= 45].sort_values("Date").groupby(["Name", "Sex"])
for (name, sex), grp in g:
    if len(grp) >= 4 and grp["Age"].max() - grp["Age"].min() >= 5:
        x = grp["Age"].values.astype(float)
        y = np.log(grp["TotalKg"].values)
        rows.append({"sex": sex, "age_first": float(x.min()),
                     "span": float(x.max() - x.min()), "n_meets": len(grp),
                     "slope_pct_per_year": float(np.polyfit(x, y, 1)[0] * 100)})
h45 = pd.DataFrame(rows)
h45.to_csv(DATA / "longitudinal_45plus.csv", index=False)
out["longitudinal_45plus"] = {
    sex: {"lifters": int((h45.sex == sex).sum()),
          "median_slope_pct_per_year": round(float(
              h45[h45.sex == sex]["slope_pct_per_year"].median()), 2)}
    for sex in ["M", "F"]}

# 4. density by age
dens = (d.assign(age_bin=pd.cut(d["Age"], [14, 24, 29, 34, 39, 44, 49, 54, 59, 64, 69, 85]))
        .groupby(["Sex", "age_bin"], observed=True).size().unstack(fill_value=0))
out["rows_by_age_band"] = {sex: {str(k): int(v) for k, v in row.items()}
                           for sex, row in dens.iterrows()}

(DATA / "checks.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
