"""
Part 2: Sleep is the highest-ROI biohack — NHANES 2017-2020 evidence.

Merges NHANES 2017-Mar 2020 pre-pandemic files:
  P_DEMO (age/sex/weights), P_SLQ (sleep hours, sleep_h),
  P_BMX (measured BMI), P_GHB (HbA1c), P_BPQ (told had high BP),
  P_DIQ (told had diabetes)
and relates self-reported sleep duration to measured/chronic health markers
in US adults, plus how sleep varies by age group.

All files are public-domain CDC/NCHS data. Downloads are documented in
data/DATA_SOURCES.md; the merge here uses SEQN keys.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

HERE = Path(__file__).resolve().parent.parent
DATA = HERE / "data" / "nhanes"
OUT = HERE / "charts"
OUT.mkdir(exist_ok=True)

SLEEP_BINS = [0, 5, 6, 7, 8, 9, 24]
SLEEP_LABELS = ["<5h", "5-6h", "6-7h", "7-8h", "8-9h", "9h+"]


def load():
    dfs = {}
    for name in ["P_DEMO", "P_SLQ", "P_BMX", "P_GHB", "P_BPQ", "P_DIQ"]:
        df, _ = pyreadstat.read_xport(str(DATA / f"{name}.xpt"))
        dfs[name] = df
        print(name, df.shape)
    return dfs


def build(dfs):
    demo, slq, bmx, ghb, bpq, diq = (
        dfs["P_DEMO"],
        dfs["P_SLQ"],
        dfs["P_BMX"],
        dfs["P_GHB"],
        dfs["P_BPQ"],
        dfs["P_DIQ"],
    )
    df = demo[["SEQN", "RIDAGEYR", "RIAGENDR", "WTMECPRP"]].merge(
        slq[["SEQN", "SLD012", "SLD013"]], on="SEQN", how="inner"
    )
    # Habitual sleep hours: weighted weekday/weekend average (SLD012/SLD013)
    df = df[df.SLD012.between(2, 14) & df.SLD013.between(2, 14)].copy()
    df["sleep_h"] = (df.SLD012 * 5 + df.SLD013 * 2) / 7
    df = df[df.sleep_h.between(2, 14)].copy()
    df = df.merge(bmx[["SEQN", "BMXBMI"]], on="SEQN", how="left")
    df = df.merge(ghb[["SEQN", "LBXGH"]], on="SEQN", how="left")
    df = df.merge(bpq[["SEQN", "BPQ020"]], on="SEQN", how="left")
    df = df.merge(diq[["SEQN", "DIQ010"]], on="SEQN", how="left")

    # Adults 20+, valid sleep 1..20 h
    df = df[(df.RIDAGEYR >= 20) & (df.sleep_h >= 1) & (df.sleep_h <= 20)].copy()
    df["sleep_bin"] = pd.cut(
        df.sleep_h, bins=SLEEP_BINS, labels=SLEEP_LABELS, right=False
    )
    df["obese"] = (df.BMXBMI >= 30).astype(float)
    df["hypertension"] = (df.BPQ020 == 1).astype(float)
    df["diabetes"] = (df.DIQ010 == 1).astype(float)
    df["prediabetes_plus"] = (df.LBXGH >= 5.7).astype(float)
    df["age_group"] = pd.cut(
        df.RIDAGEYR, bins=[20, 35, 50, 65, 120],
        labels=["20-34", "35-49", "50-64", "65+"],
    )
    return df


def weighted(df, col):
    """Survey-weighted mean of col, dropping missing; returns (mean, n, se)."""
    sub = df[df[col].notna() & df.WTMECPRP.notna() & (df.WTMECPRP > 0)]
    if len(sub) == 0:
        return float("nan"), 0, float("nan")
    w = sub.WTMECPRP
    m = np.average(sub[col], weights=w)
    n = len(sub)
    # Kish effective n for se
    neff = w.sum() ** 2 / (w**2).sum()
    var = np.average((sub[col] - m) ** 2, weights=w)
    se = np.sqrt(var / neff)
    return m, n, se


def main():
    dfs = load()
    df = build(dfs)
    print("analysis n =", len(df))

    # 1) Sleep distribution by age group
    g = df.groupby(["age_group", "sleep_bin"], observed=True)["WTMECPRP"].sum()
    dist = (100 * g / g.groupby(level=0, observed=True).transform("sum")).reset_index(name="pct")
    dist.to_csv(DATA / "sleep_dist_by_age.csv", index=False)

    # 2) Health markers by sleep bin (weighted)
    rows = []
    for b in SLEEP_LABELS:
        sub = df[df.sleep_bin == b]
        row = {"sleep_bin": b, "n": len(sub)}
        for col in ["BMXBMI", "LBXGH", "obese", "hypertension", "diabetes",
                    "prediabetes_plus"]:
            m, n, se = weighted(sub, col)
            row[f"{col}_mean"] = m
            row[f"{col}_n"] = n
            row[f"{col}_se"] = se
        rows.append(row)
    health = pd.DataFrame(rows)
    health.to_csv(DATA / "health_by_sleep.csv", index=False)

    # 3) Mean sleep hours by age group
    age_sleep = []
    for g, sub in df.groupby("age_group", observed=True):
        m, n, se = weighted(sub, "sleep_h")
        age_sleep.append({"age_group": g, "mean_sleep": m, "se": se, "n": n})
    pd.DataFrame(age_sleep).to_csv(DATA / "mean_sleep_by_age.csv", index=False)

    # headline stats
    total = df.WTMECPRP.sum()
    short = df[df.sleep_h < 7].WTMECPRP.sum() / total * 100
    long9 = df[df.sleep_h >= 9].WTMECPRP.sum() / total * 100
    ideal = df[(df.sleep_h >= 7) & (df.sleep_h < 9)].WTMECPRP.sum() / total * 100
    m7, _, _ = weighted(df[(df.sleep_h >= 7) & (df.sleep_h < 8)], "obese")
    m5, _, _ = weighted(df[df.sleep_h < 6], "obese")
    stats = {
        "n_unweighted": len(df),
        "pct_sleeping_under_7h": round(short, 1),
        "pct_sleeping_7_to_9h": round(ideal, 1),
        "pct_sleeping_9h_plus": round(long9, 1),
        "obesity_prev_sleep_7_8h": round(m7 * 100, 1),
        "obesity_prev_sleep_under_6h": round(m5 * 100, 1),
    }
    (DATA / "sleep_headlines.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
