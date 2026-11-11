#!/usr/bin/env python3
"""Explore ATUS 2023: time with friends by age and life stage.

Validates BLS's TRTFRIEND against a from-scratch computation from the
Activity + Who files (friends = TUWHO_CODE 54), then prints the headline
numbers that drive the build.
"""
import pandas as pd
import numpy as np
import zipfile
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# extract the .dat files from the zips (intermediates; the zips are the source)
for z in ["atusact-2023.zip", "atuswho-2023.zip", "atusresp-2023.zip", "atuscps-2023.zip"]:
    with zipfile.ZipFile(DATA / z) as zf:
        zf.extractall(DATA)

resp = pd.read_csv(DATA / "atusresp_2023.dat", dtype={"TUCASEID": str})
cps = pd.read_csv(DATA / "atuscps_2023.dat", dtype={"TUCASEID": str}, low_memory=False)
act = pd.read_csv(DATA / "atusact_2023.dat", dtype={"TUCASEID": str})
who = pd.read_csv(DATA / "atuswho_2023.dat", dtype={"TUCASEID": str})

print("respondents:", len(resp), "| cps rows:", len(cps), "| activities:", len(act), "| who rows:", len(who))

# --- validate TRTFRIEND from activity + who -------------------------------
# BLS: nonwork time with friends; work = TRCODE 0501xx; sleep/grooming have
# no who info. Sum TUACTDUR24 for activities with any TUWHO_CODE == 54,
# excluding work activities.
friend_acts = who.loc[who.TUWHO_CODE == 54, ["TUCASEID", "TUACTIVITY_N"]].drop_duplicates()
m = act.merge(friend_acts, on=["TUCASEID", "TUACTIVITY_N"], how="inner")
m = m[~m.TRCODE.astype(str).str.startswith("501")]  # exclude work (0501xx)
mine = m.groupby("TUCASEID")["TUACTDUR24"].sum().rename("mine")
chk = resp.set_index("TUCASEID").join(mine)
chk["mine"] = chk["mine"].fillna(0)
diff = (chk.TRTFRIEND if "TRTFRIEND" in chk else chk.TRTFRIEND) if False else chk["TRTFRIEND"] - chk["mine"]
print("\nTRTFRIEND validation (BLS minus recomputed):")
print(f"  exact match: {(diff == 0).mean():.3f}  |  within 5 min: {(diff.abs() <= 5).mean():.3f}  |  mean abs diff: {diff.abs().mean():.2f} min")
print("  (small diffs expected: BLS excludes some activities/secondary childcare nuances)")

# --- merge respondent + CPS (respondent row only) --------------------------
cps_r = cps[cps.TULINENO == 1][["TUCASEID", "PRTAGE", "PEMARITL", "PESEX", "PEHRUSLT", "PRNMCHLD"]]
df = resp.merge(cps_r, on="TUCASEID", how="left", validate="one_to_one").copy()
print("\nmerged rows:", len(df), "| missing age:", df.PRTAGE.isna().sum())
print("TRSPPRES values:\n", df.TRSPPRES.value_counts(dropna=False))
print("PEMARITL values:\n", df.PEMARITL.value_counts(dropna=False))
print("TRCHILDNUM describe:\n", df.TRCHILDNUM.describe())

df["w"] = df.TUFINLWGT
df["age_band"] = pd.cut(df.PRTAGE, [17, 24, 29, 34, 39, 44, 49, 54, 59, 64, 74, 120],
                        labels=["18-24", "25-29", "30-34", "35-39", "40-44", "45-49",
                                "50-54", "55-59", "60-64", "65-74", "75+"])
df["weekend"] = df.TUDIARYDAY.isin([1, 7])
df["married"] = df.PEMARITL == 1
df["partnered"] = df.TRSPPRES.isin([1, 2])
df["any_kid"] = df.TRCHILDNUM > 0
df["female"] = df.PESEX == 2

def wmean(s, w):
    return np.average(s, weights=w)

print("\n=== Friend minutes/day by age band (weighted) ===")
g = df.groupby("age_band", observed=True).apply(
    lambda x: pd.Series({"n": len(x), "friend_min": wmean(x.TRTFRIEND, x.w),
                         "any_friend": wmean((x.TRTFRIEND > 0).astype(float), x.w),
                         "cond_min": wmean(x.loc[x.TRTFRIEND > 0, "TRTFRIEND"], x.loc[x.TRTFRIEND > 0, "w"]) if (x.TRTFRIEND > 0).any() else np.nan,
                         "family_min": wmean(x.TRTFAMILY, x.w),
                         "spouse_min": wmean(x.TRTSPOUSE, x.w),
                         "alone_min": wmean(x.TRTALONE, x.w)}),
    include_groups=False)
print(g.round(1).to_string())

print("\n=== Life-stage groups (weighted friend min/day) ===")
def stage(r):
    if r.PRTAGE >= 55 and r.TRCHILDNUM == 0:
        return "55+ no kids at home"
    if r.any_kid and r.partnered:
        return "partnered + kids"
    if r.any_kid and not r.partnered:
        return "single + kids"
    if r.partnered:
        return "partnered, no kids"
    return "single, no kids"
df["stage"] = df.apply(stage, axis=1)
for s, x in df.groupby("stage"):
    print(f"  {s:22s} n={len(x):5d}  friend={wmean(x.TRTFRIEND, x.w):6.1f} min  any={wmean((x.TRTFRIEND>0).astype(float), x.w):.2f}  cond={wmean(x.loc[x.TRTFRIEND>0,'TRTFRIEND'], x.loc[x.TRTFRIEND>0,'w']):6.1f}")

print("\n=== By youngest child age (TRYHHCHILD) ===")
print(df.TRYHHCHILD.describe())
for lab, mask in [("no kids <18", df.TRCHILDNUM == 0),
                  ("youngest 0-2", (df.TRCHILDNUM > 0) & (df.TRYHHCHILD <= 2)),
                  ("youngest 3-5", (df.TRCHILDNUM > 0) & (df.TRYHHCHILD >= 3) & (df.TRYHHCHILD <= 5)),
                  ("youngest 6-12", (df.TRCHILDNUM > 0) & (df.TRYHHCHILD >= 6) & (df.TRYHHCHILD <= 12)),
                  ("youngest 13-17", (df.TRCHILDNUM > 0) & (df.TRYHHCHILD >= 13))]:
    x = df[mask]
    if len(x):
        print(f"  {lab:16s} n={len(x):5d}  friend={wmean(x.TRTFRIEND, x.w):6.1f} min  any={wmean((x.TRTFRIEND>0).astype(float), x.w):.2f}")

df.to_pickle(DATA / "merged.pkl")
print("\nsaved merged.pkl")
