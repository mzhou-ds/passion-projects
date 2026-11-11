#!/usr/bin/env python3
"""Supplementary checks for the Friend Recession build."""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

df = pd.read_pickle("data/merged.pkl")
df = df[df.PRTAGE >= 18].copy()
F = "TRTFRIEND"

def wm(s, w):
    return float(np.average(s, weights=w))

df["stage"] = np.where(df["TRCHILDNUM"] > 0,
                       np.where(df["TRSPPRES"].isin([1, 2]), "partnered+kids", "single+kids"),
                       np.where(df["TRSPPRES"].isin([1, 2]), "partnered, no kids", "single, no kids"))
print("=== Friend min/day by stage WITHIN age band ===")
for lo, hi in [(25, 34), (35, 44), (45, 54)]:
    sub = df[(df["PRTAGE"] >= lo) & (df["PRTAGE"] <= hi)]
    print(f"--- ages {lo}-{hi} ---")
    for s, x in sub.groupby("stage"):
        print(f"  {s:20s} n={len(x):4d}  friend={wm(x[F], x['w']):5.1f}  "
              f"days/mo={wm((x[F] > 0).astype(float), x['w']) * 30:4.1f}")

mid = df[(df["PRTAGE"] >= 25) & (df["PRTAGE"] <= 54)]
sk = mid[(mid["TRCHILDNUM"] > 0) & (~mid["TRSPPRES"].isin([1, 2]))]
print("\nsingle+kids 25-54: n =", len(sk), " weekend n =", int(sk["weekend"].sum()),
      " weekday n =", int((~sk["weekend"]).sum()))

print("\n=== eldercare (TRTEC), work hrs, childcare, alone by age band ===")
for b, x in df.groupby("age_band", observed=True):
    print(f"  {b:6s} eldercare={wm(x['TRTEC'], x['w']):5.1f}  workhrs={wm(x['TEHRUSLT'].fillna(0), x['w']):5.1f}  "
          f"childcare={wm(x['TRTCC'], x['w']):5.1f}  alone={wm(x['TRTALONE'], x['w']):5.1f}")

e = df[(df["PRTAGE"] >= 18) & (df["PRTAGE"] <= 24)]
print("\n18-24 enrolled in school (TESCHENR==1):", (e["TESCHENR"] == 1).mean().round(2))
print("  enrolled friend min:", round(wm(e[e["TESCHENR"] == 1][F], e[e["TESCHENR"] == 1]["w"]), 1),
      "| not enrolled:", round(wm(e[e["TESCHENR"] != 1][F], e[e["TESCHENR"] != 1]["w"]), 1))

p = mid[mid["TRSPPRES"].isin([1, 2])]
print("\npartnered 25-54: married friend min:",
      round(wm(p[p["TRSPPRES"] == 1][F], p[p["TRSPPRES"] == 1]["w"]), 1),
      " n =", int((p["TRSPPRES"] == 1).sum()),
      "| cohabiting:", round(wm(p[p["TRSPPRES"] == 2][F], p[p["TRSPPRES"] == 2]["w"]), 1),
      " n =", int((p["TRSPPRES"] == 2).sum()))

base = 58.4
loss = sum((base - wm(df[df["age_band"] == b][F], df[df["age_band"] == b]["w"])) * 365 / 60 * w
           for b, w in [("25-29", 5), ("30-34", 5), ("35-39", 5), ("40-44", 5), ("45-49", 5), ("50-54", 5)])
print(f"\nCumulative friend-hours lost ages 25-54 vs holding 18-24 level: {loss:,.0f} hours = {loss/24:,.0f} full days")
