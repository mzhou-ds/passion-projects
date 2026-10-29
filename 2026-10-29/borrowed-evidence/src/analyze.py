"""Borrowed-evidence analysis.

Key constructs (all from registry fields, no hand-coding of conditions):
- healthy_flag: registry healthyVolunteers == True.
- healthy_condition: at least one listed condition normalises to 'healthy'.
- patient_trial: healthy_volunteers is False (registry says no healthy
  volunteers accepted). Trials with a missing flag are 'unknown'.
- young_healthy_trial: healthy_flag AND min_age <= 40 AND the trial is not
  restricted to older adults (std_ages contains ADULT).
- disease trial share: patient_trial share; the complement is NOT 'healthy
  evidence', because many trials accept both patients and healthy controls.
  So we report both the strict patient share and the stricter
  young-healthy share, and never over-claim the middle.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "data" / "trials.csv")
df["healthy_volunteers"] = df["healthy_volunteers"].map(
    lambda v: True if v is True or str(v).lower() == "true"
    else (False if str(v).lower() == "false" else np.nan))
df["start_year"] = pd.to_numeric(df["start_year"], errors="coerce")
df["enrollment"] = pd.to_numeric(df["enrollment"], errors="coerce")


def healthy_cond(conds):
    return any(c.strip().lower() == "healthy" for c in str(conds).split(";"))


df["healthy_condition"] = df["conditions"].apply(healthy_cond)
df["young_healthy"] = (
    (df["healthy_volunteers"] == True)
    & (df["min_age"].fillna(99) <= 40)
    & (df["std_ages"].str.contains("ADULT", na=False))
    & (~df["std_ages"].str.contains("OLDER_ADULT", na=False)
       | df["std_ages"].str.contains("ADULT", na=False))
    & (df["std_ages"] != "OLDER_ADULT")
)
# tighten: young-healthy also requires the trial not be older-adult-only
df["young_healthy"] = (
    (df["healthy_volunteers"] == True)
    & (df["min_age"].fillna(99) <= 40)
    & (df["std_ages"].str.contains("ADULT", na=False))
    & (~df["std_ages"].isin(["OLDER_ADULT"]))
)

rows = []
for name, g in df.groupby("intervention"):
    known = g[g["healthy_volunteers"].notna()]
    rows.append({
        "intervention": name, "category": g["category"].iloc[0], "n": len(g),
        "pct_patient_only": (known["healthy_volunteers"] == False).mean() * 100,
        "pct_healthy_flag": (known["healthy_volunteers"] == True).mean() * 100,
        "pct_healthy_condition": g["healthy_condition"].mean() * 100,
        "pct_young_healthy": g["young_healthy"].mean() * 100,
        "median_min_age": g["min_age"].median(),
        "median_max_age": g["max_age"].median(),
        "pct_min_age_ge_50": (g["min_age"] >= 50).mean() * 100,
        "pct_older_adult_only": (g["std_ages"] == "OLDER_ADULT").mean() * 100,
        "median_enrollment": g["enrollment"].median(),
        "pct_completed": (g["overall_status"] == "COMPLETED").mean() * 100,
        "pct_industry": (g["sponsor_class"] == "INDUSTRY").mean() * 100,
        "median_start_year": g["start_year"].median(),
    })
summary = pd.DataFrame(rows).sort_values("pct_young_healthy")
summary.to_csv(ROOT / "data" / "summary.csv", index=False)
print(summary.round(1).to_string(index=False))

# pooled stats
known = df[df["healthy_volunteers"].notna()]
print(f"\nTOTAL n={len(df)}; known flag n={len(known)}")
print(f"patient-only (flag False): {(known['healthy_volunteers'] == False).mean()*100:.1f}%")
print(f"young-healthy share of all: {df['young_healthy'].mean()*100:.1f}%")
print(f"healthy-condition share: {df['healthy_condition'].mean()*100:.1f}%")
print(f"median min age overall: {df['min_age'].median():.0f}; "
      f"share min_age>=50: {(df['min_age'] >= 50).mean()*100:.1f}%")
print(f"median enrollment healthy-flag vs patient: "
      f"{df[df['healthy_volunteers']==True]['enrollment'].median():.0f} vs "
      f"{df[df['healthy_volunteers']==False]['enrollment'].median():.0f}")
print(f"completed healthy-flag vs patient: "
      f"{(df[df['healthy_volunteers']==True]['overall_status']=='COMPLETED').mean()*100:.1f}% vs "
      f"{(df[df['healthy_volunteers']==False]['overall_status']=='COMPLETED').mean()*100:.1f}%")

# top conditions per intervention (disease burden behind the counts)
top = {}
for name, g in df.groupby("intervention"):
    conds = g["conditions"].str.split("; ").explode().str.strip()
    conds = conds[~conds.str.lower().isin(["healthy", ""])]
    top[name] = conds.value_counts().head(5).to_dict()
json.dump(top, open(ROOT / "data" / "top_conditions.json", "w"), indent=1)
for k, v in top.items():
    print(f"\n{k}: {v}")

# trend: trials started per year, pooled + by category.
# EXCLUDE rapamycin: it is the one capped term (pagination stopped at 5 pages),
# and capped pagination skews toward recent records, so it would inflate the
# recent years. All other terms ran to exhaustion (n < cap or no next page).
trend = df[df["intervention"] != "Rapamycin"].dropna(subset=["start_year"])
trend = trend[(trend["start_year"] >= 2000) & (trend["start_year"] <= 2026)]
print("\nTrials started by year (pooled):")
print(trend.groupby("start_year").size().to_string())
trend.groupby(["start_year", "category"]).size().unstack(fill_value=0).to_csv(
    ROOT / "data" / "trend_by_category.csv")
# young-healthy share by era
trend = trend.assign(era=pd.cut(trend["start_year"], [1999, 2010, 2015, 2020, 2026],
                                labels=["<=2010", "2011-15", "2016-20", "2021+"]))
print("\nYoung-healthy share by era:")
print(trend.groupby("era", observed=True)["young_healthy"].agg(["mean", "count"]).round(3))
df.to_csv(ROOT / "data" / "trials_enriched.csv", index=False)
