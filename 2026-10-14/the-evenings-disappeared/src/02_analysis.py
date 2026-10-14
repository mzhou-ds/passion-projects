"""
02_analysis.py - weighted trends, the 2018->2024 break, who it hit,
marital substitution, a composition-vs-behaviour decomposition, and the
happiness association. Writes data/*.csv + data/findings.json.

GSS social-evening items (SOCFRED family), codes:
  1 Almost daily | 2 Several times a week | 3 Several times a month |
  4 Once a month | 5 Several times a year | 6 Once a year | 7 Never
Headline metric = share answering 1-4 ("at least monthly"): it needs no
frequency assumptions. Evenings-per-month (EPM) uses the stated mapping
below and is reported as a secondary, clearly-labelled approximation.
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

EPM = {1: 20.0, 2: 10.0, 3: 3.0, 4: 1.0, 5: 0.42, 6: 0.08, 7: 0.0}
ITEMS = {"friend": "socfrend", "relatives": "socrel",
         "bar": "socbar", "community": "socommun"}
MARITAL = {1: "Married", 2: "Widowed", 3: "Divorced", 4: "Separated",
           5: "Never married"}

df = pd.read_csv(os.path.join(DATA, "gss_extract.csv"))
df["wt"] = df["wtssall"].fillna(1.0)
for name, col in ITEMS.items():
    df[f"{name}_monthly"] = np.where(df[col].between(1, 4), 1.0,
                                     np.where(df[col] == 7, 0.0,
                                              np.where(df[col].between(5, 6),
                                                       0.0, np.nan)))
    df[f"{name}_never"] = np.where(df[col] == 7, 1.0,
                                   np.where(df[col].between(1, 6), 0.0, np.nan))
    df[f"{name}_epm"] = df[col].map(EPM)
df["marital_lbl"] = df["marital"].map(MARITAL)
df["ageband"] = pd.cut(df["age"], [17, 24, 34, 44, 54, 64, 200],
                       labels=["18-24", "25-34", "35-44", "45-54", "55-64",
                               "65+"])
df["any_kids"] = np.where(df["childs"].notna(), (df["childs"] > 0).astype(int),
                          np.nan)
df["employed"] = np.where(df["wrkstat"].isin([1, 2]), 1,
                          np.where(df["wrkstat"].notna(), 0, np.nan))
df.to_csv(os.path.join(DATA, "analytic.csv"), index=False)


def wprop(g, col):
    """Weighted proportion + design-naive SE using effective n."""
    g = g.dropna(subset=[col])
    if len(g) == 0:
        return np.nan, np.nan, 0
    w, x = g["wt"].to_numpy(), g[col].to_numpy()
    p = np.average(x, weights=w)
    n_eff = w.sum() ** 2 / (w ** 2).sum()
    return p, np.sqrt(max(p * (1 - p), 0) / n_eff), len(g)


def wmean(g, col):
    g = g.dropna(subset=[col])
    if len(g) == 0:
        return np.nan, 0
    return np.average(g[col], weights=g["wt"]), len(g)


F = {}

# ---------------------------------------------------------- 1. year series
rows = []
soc = df[df["socfrend"].notna()]
for yr, g in soc.groupby("year"):
    r = {"year": int(yr)}
    for name in ITEMS:
        p, se, n = wprop(g, f"{name}_monthly")
        r[f"{name}_monthly"] = 100 * p
        r[f"{name}_monthly_se"] = 100 * se
        e, _ = wmean(g, f"{name}_epm")
        r[f"{name}_epm"] = e
    p, se, n = wprop(g, "friend_never")
    r["friend_never"] = 100 * p
    r["n"] = n
    rows.append(r)
series = pd.DataFrame(rows)
series.to_csv(os.path.join(DATA, "year_series.csv"), index=False)

long_run = series[series.year.between(1974, 2018)]
recent = series[series.year.isin([2022, 2024])]
F["friend_monthly_longrun_mean"] = round(long_run.friend_monthly.mean(), 1)
F["friend_monthly_2018"] = round(float(series.set_index("year")
                                       .loc[2018, "friend_monthly"]), 1)
F["friend_monthly_2021"] = round(float(series.set_index("year")
                                       .loc[2021, "friend_monthly"]), 1)
post_pool = soc[soc.year.isin([2022, 2024])]
p, se, n = wprop(post_pool, "friend_monthly")
F["friend_monthly_2022_24"] = round(100 * p, 1)
F["friend_monthly_2022_24_se"] = round(100 * se, 2)
pre_pool = soc[soc.year.between(2014, 2018)]
p0, se0, n0 = wprop(pre_pool, "friend_monthly")
F["friend_monthly_2014_18"] = round(100 * p0, 1)
F["friend_monthly_drop_pp"] = round(100 * (p - p0), 1)
p, se, n = wprop(post_pool, "friend_never")
F["friend_never_2022_24"] = round(100 * p, 1)
p, se, n = wprop(pre_pool, "friend_never")
F["friend_never_2014_18"] = round(100 * p, 1)
for name in ITEMS:
    e_pre, _ = wmean(pre_pool, f"{name}_epm")
    e_post, _ = wmean(post_pool, f"{name}_epm")
    pm_pre, _, _ = wprop(pre_pool, f"{name}_monthly")
    pm_post, _, _ = wprop(post_pool, f"{name}_monthly")
    F[f"{name}_epm_2014_18"] = round(e_pre, 2)
    F[f"{name}_epm_2022_24"] = round(e_post, 2)
    F[f"{name}_epm_change_pct"] = round(100 * (e_post / e_pre - 1), 1)
    F[f"{name}_monthly_change_pp"] = round(100 * (pm_post - pm_pre), 1)

# ---------------------------------------------------------- 2. age x era
rows = []
for era, yrs in [("1974-1989", (1974, 1989)), ("1990-2009", (1990, 2009)),
                 ("2010-2018", (2010, 2018)), ("2022-2024", (2022, 2024))]:
    g0 = soc[soc.year.between(*yrs)]
    for band, g in g0.groupby("ageband", observed=True):
        p, se, n = wprop(g, "friend_monthly")
        e, _ = wmean(g, "friend_epm")
        rows.append({"era": era, "ageband": str(band),
                     "friend_monthly": round(100 * p, 1), "friend_epm": round(e, 2),
                     "n": n})
age_era = pd.DataFrame(rows)
age_era.to_csv(os.path.join(DATA, "age_era.csv"), index=False)
piv = age_era.pivot(index="ageband", columns="era", values="friend_monthly")
F["age_era_drop_pp"] = {b: round(piv.loc[b, "2022-2024"] -
                                 piv.loc[b, "2010-2018"], 1)
                        for b in piv.index}

# ------------------------------------------- 3. marital substitution table
rows = []
for era_lbl, pool in [("2014-2018", pre_pool), ("2022-2024", post_pool)]:
    for mlbl, g in pool.groupby("marital_lbl"):
        r = {"era": era_lbl, "marital": mlbl, "n": len(g)}
        for name in ITEMS:
            p, se, n = wprop(g, f"{name}_monthly")
            r[f"{name}_monthly"] = round(100 * p, 1)
        rows.append(r)
sub = pd.DataFrame(rows)
sub.to_csv(os.path.join(DATA, "marital_substitution.csv"), index=False)
sp = sub.pivot(index="marital", columns="era", values="friend_monthly")
F["friend_monthly_by_marital_change_pp"] = {
    m: round(sp.loc[m, "2022-2024"] - sp.loc[m, "2014-2018"], 1)
    for m in sp.index}
bp = sub.pivot(index="marital", columns="era", values="bar_monthly")
F["bar_monthly_by_marital_change_pp"] = {
    m: round(bp.loc[m, "2022-2024"] - bp.loc[m, "2014-2018"], 1)
    for m in bp.index}

# --------------------------------- 4. Oaxaca-Blinder style decomposition
# Cells: ageband x sex x marital(3-way) x kids x employed. How much of the
# drop survives if 2022-24 keeps 2014-18 behaviour within every cell?
d = soc.copy()
d["marital3"] = np.where(d["marital"] == 1, "Married",
                         np.where(d["marital"] == 5, "Never married", "Other"))
d["cell"] = (d["ageband"].astype(str) + "|" + d["sex"].astype(str) + "|" +
             d["marital3"] + "|" + d["any_kids"].astype(str) + "|" +
             d["employed"].astype(str))
d = d.dropna(subset=["friend_monthly", "any_kids", "employed"])
pre = d[d.year.between(2014, 2018)]
post = d[d.year.isin([2022, 2024])]


def cell_stats(g):
    return g.groupby("cell").apply(
        lambda x: pd.Series({"share": x["wt"].sum(),
                             "rate": np.average(x["friend_monthly"],
                                                weights=x["wt"])}),
        include_groups=False)


cs_pre, cs_post = cell_stats(pre), cell_stats(post)
cs_pre["share"] /= cs_pre["share"].sum()
cs_post["share"] /= cs_post["share"].sum()
both = cs_pre.join(cs_post, lsuffix="_pre", rsuffix="_post", how="inner")
both = both.dropna()
actual_pre = (both.share_pre * both.rate_pre).sum() / both.share_pre.sum()
actual_post = (both.share_post * both.rate_post).sum() / both.share_post.sum()
# counterfactual: post composition, pre behaviour
cf = (both.share_post * both.rate_pre).sum() / both.share_post.sum()
total = actual_post - actual_pre
composition = cf - actual_pre
behaviour = actual_post - cf
F["decomp"] = {
    "cells_used": int(len(both)), "n_pre": int(len(pre)), "n_post": int(len(post)),
    "pre_rate_common_cells": round(100 * actual_pre, 1),
    "post_rate_common_cells": round(100 * actual_post, 1),
    "total_change_pp": round(100 * total, 1),
    "composition_pp": round(100 * composition, 1),
    "behaviour_pp": round(100 * behaviour, 1),
    "behaviour_share_pct": round(100 * behaviour / total, 0) if total else None,
}

# ------------------------------------------------- 5. happiness association
h = df.dropna(subset=["happy", "socfrend"]).copy()
h["very_happy"] = (h["happy"] == 1).astype(float)
h["friend_freq"] = pd.cut(h["socfrend"], [0, 2, 4, 5, 7],
                          labels=["Weekly+", "Monthly", "A few times a year",
                                  "Once a year / never"])
rows = []
for lbl, g in h.groupby("friend_freq", observed=True):
    p, se, n = wprop(g, "very_happy")
    rows.append({"friend_freq": str(lbl), "very_happy_pct": round(100 * p, 1),
                 "se": round(100 * se, 1), "n": n})
hap = pd.DataFrame(rows)
hap.to_csv(os.path.join(DATA, "happiness_by_friend_freq.csv"), index=False)
F["very_happy_weekly_plus"] = float(hap.set_index("friend_freq")
                                   .loc["Weekly+", "very_happy_pct"])
F["very_happy_once_never"] = float(hap.set_index("friend_freq")
                                   .loc["Once a year / never", "very_happy_pct"])
# same contrast inside the post period only
hp = h[h.year.isin([2022, 2024])]
rows = []
for lbl, g in hp.groupby("friend_freq", observed=True):
    p, se, n = wprop(g, "very_happy")
    rows.append({"friend_freq": str(lbl), "very_happy_pct": round(100 * p, 1),
                 "n": n})
F["happiness_post_period"] = rows

# married respondents: is marital happiness moving with the friend drop?
hm = df.dropna(subset=["hapmar"]).copy()
hm["very_happy_marriage"] = (hm["hapmar"] == 1).astype(float)
for lbl, yrs in [("1970s", (1972, 1979)), ("1990s", (1990, 1999)),
                 ("2014-2018", (2014, 2018)), ("2022-2024", (2022, 2024))]:
    g = hm[hm.year.between(*yrs)]
    p, se, n = wprop(g, "very_happy_marriage")
    F[f"hapmar_very_happy_{lbl}"] = round(100 * p, 1)

F["n_socfrend_valid"] = int(soc.shape[0])
F["n_total"] = int(df.shape[0])
F["year_min"], F["year_max"] = int(df.year.min()), int(df.year.max())

with open(os.path.join(DATA, "findings.json"), "w") as f:
    json.dump(F, f, indent=1)
print(json.dumps(F, indent=1))
print("wrote year_series.csv, age_era.csv, marital_substitution.csv,",
      "happiness_by_friend_freq.csv, findings.json")
