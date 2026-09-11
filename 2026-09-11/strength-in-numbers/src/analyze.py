"""Compute every statistic behind Strength in Numbers.

Reads output/entries_sbd.csv, output/lifter_bests_raw.csv and
output/lifter_bests_sp.csv (see prepare.py) and writes:

  output/standards.csv      — total-kg percentiles by sex/equipment/bodyweight bin
  output/age_curve.csv      — median Goodlift by integer age and sex (raw SBD)
  output/yearly.csv         — per-year participation + median total/GL by sex (raw SBD)
  output/dots_bias.csv      — median Dots by bodyweight bin and sex (raw SBD)
  output/equipment.csv      — raw vs single-ply median totals by sex
  output/summary.json       — headline numbers for the README / Threads draft
"""
import json
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "output")

PCTS = [5, 10, 25, 50, 75, 90, 95, 99]
BW_BINS = list(range(40, 185, 5))  # 5 kg bins from 40 to 180 kg


def bw_bin(w):
    if pd.isna(w):
        return None
    b = int(w // 5 * 5)
    return min(max(b, 40), 180)


def main():
    entries = pd.read_csv(os.path.join(OUT, "entries_sbd.csv"))
    raw = pd.read_csv(os.path.join(OUT, "lifter_bests_raw.csv"))
    sp = pd.read_csv(os.path.join(OUT, "lifter_bests_sp.csv"))
    print(f"entries={len(entries):,} raw lifters={len(raw):,} sp lifters={len(sp):,}")

    # ------------------------------------------------------------------
    # 1. Strength standards: percentiles of best total by sex/equipment/bw bin
    # ------------------------------------------------------------------
    std_rows = []
    for equip, frame in [("Raw", raw), ("Single-ply", sp)]:
        f = frame.dropna(subset=["BodyweightKg"]).copy()
        f["bw_bin"] = f["BodyweightKg"].apply(bw_bin)
        for (sex, b), g in f.groupby(["Sex", "bw_bin"]):
            if len(g) < 30:
                continue
            q = np.percentile(g["TotalKg"], PCTS)
            row = {"sex": sex, "equipment": equip, "bw_bin": b, "n": len(g)}
            row.update({f"p{p}": round(float(v), 1) for p, v in zip(PCTS, q)})
            std_rows.append(row)
    standards = pd.DataFrame(std_rows)
    standards.to_csv(os.path.join(OUT, "standards.csv"), index=False)
    print(f"standards rows: {len(standards)}")

    # Overall (all bodyweights) percentiles per sex/equipment, for the explorer.
    overall = {}
    for equip, frame in [("Raw", raw), ("Single-ply", sp)]:
        for sex in ["M", "F"]:
            g = frame[frame["Sex"] == sex]["TotalKg"]
            overall[f"{sex}_{equip}"] = {
                "n": int(len(g)),
                **{f"p{p}": round(float(v), 1)
                   for p, v in zip(PCTS, np.percentile(g, PCTS))},
            }

    # ------------------------------------------------------------------
    # 2. Age curve: median Goodlift by age (raw SBD entries, cross-sectional)
    # ------------------------------------------------------------------
    a = entries[(entries["Equipment"] == "Raw")
                & entries["Age"].between(14, 80)
                & (entries["Goodlift"] > 0)].copy()
    a["age_int"] = a["Age"].astype(int)
    age_rows = []
    for (sex, age), g in a.groupby(["Sex", "age_int"]):
        if len(g) < 100:
            continue
        age_rows.append({"sex": sex, "age": age, "n": len(g),
                         "median_gl": round(float(g["Goodlift"].median()), 2),
                         "p90_gl": round(float(g["Goodlift"].quantile(0.90)), 2),
                         "p25_gl": round(float(g["Goodlift"].quantile(0.25)), 2),
                         "p75_gl": round(float(g["Goodlift"].quantile(0.75)), 2)})
    age_curve = pd.DataFrame(age_rows).sort_values(["sex", "age"])
    age_curve.to_csv(os.path.join(OUT, "age_curve.csv"), index=False)

    # Peak age per sex (median GL), plus value at 25 and 55 for the decline.
    # NOTE: IPF Goodlift points are sex-specific by design, so cross-sex GL
    # ratios are not a raw strength gap. The true gap uses totals below.
    peaks = {}
    for sex in ["M", "F"]:
        g = age_curve[age_curve["sex"] == sex]
        peak = g.loc[g["median_gl"].idxmax()]
        peak90 = g.loc[g["p90_gl"].idxmax()]
        at55 = g[g["age"] == 55]["median_gl"].iloc[0] if (g["age"] == 55).any() else None
        peaks[sex] = {"peak_age": int(peak["age"]),
                      "peak_gl": float(peak["median_gl"]),
                      "peak90_age": int(peak90["age"]),
                      "peak90_gl": float(peak90["p90_gl"]),
                      "gl_at_55": float(at55) if at55 else None}

    # ------------------------------------------------------------------
    # 3. Yearly trends (raw SBD): participation + median total + sex gap
    # ------------------------------------------------------------------
    y = entries[(entries["Equipment"] == "Raw") & entries["Year"].between(1990, 2026)]
    y_rows = []
    for (year, sex), g in y.groupby(["Year", "Sex"]):
        if len(g) < 50:
            continue
        y_rows.append({"year": int(year), "sex": sex, "n": len(g),
                       "lifters": int(g["Name"].nunique()),
                       "median_total": round(float(g["TotalKg"].median()), 1),
                       "median_gl": round(float(g.loc[g["Goodlift"] > 0,
                                                     "Goodlift"].median()), 2)})
    yearly = pd.DataFrame(y_rows).sort_values(["sex", "year"])
    yearly.to_csv(os.path.join(OUT, "yearly.csv"), index=False)

    # True sex gap: women's median TOTAL as % of men's, per year (raw SBD).
    piv = yearly.pivot(index="year", columns="sex", values="median_total")
    gap = (piv["F"] / piv["M"] * 100).dropna()
    gap_first = {"year": int(gap.index[0]), "pct": round(float(gap.iloc[0]), 1)}
    gap_last = {"year": int(gap.index[-1]), "pct": round(float(gap.iloc[-1]), 1)}

    yr = yearly[yearly["year"] >= 2010]
    growth = {}
    for sex in ["M", "F"]:
        g = yr[yr["sex"] == sex].sort_values("year")
        growth[sex] = {"lifters_2010": int(g.iloc[0]["lifters"]),
                       "lifters_2025": int(g.iloc[-1]["lifters"]),
                       "total_2010": float(g.iloc[0]["median_total"]),
                       "total_2025": float(g.iloc[-1]["median_total"])}

    # ------------------------------------------------------------------
    # 4. Dots bias: does the formula fully correct for bodyweight?
    # ------------------------------------------------------------------
    d = entries[(entries["Equipment"] == "Raw") & (entries["Dots"] > 0)].copy()
    d["bw_bin"] = d["BodyweightKg"].apply(bw_bin)
    d_rows = []
    for (sex, b), g in d.groupby(["Sex", "bw_bin"]):
        if len(g) < 100:
            continue
        d_rows.append({"sex": sex, "bw_bin": b, "n": len(g),
                       "median_dots": round(float(g["Dots"].median()), 2)})
    dots_bias = pd.DataFrame(d_rows).sort_values(["sex", "bw_bin"])
    dots_bias.to_csv(os.path.join(OUT, "dots_bias.csv"), index=False)

    # ------------------------------------------------------------------
    # 5. Equipment effect, paired: lifters with BOTH a raw and a single-ply
    #    best total — what does the suit actually add for the same person?
    # ------------------------------------------------------------------
    paired = pd.merge(
        raw[["Name", "Sex", "TotalKg"]].rename(columns={"TotalKg": "raw_total"}),
        sp[["Name", "Sex", "TotalKg"]].rename(columns={"TotalKg": "sp_total"}),
        on=["Name", "Sex"], how="inner")
    equip_rows = []
    for sex in ["M", "F"]:
        g = paired[paired["Sex"] == sex]
        uplift = (g["sp_total"] / g["raw_total"] - 1) * 100
        equip_rows.append({"sex": sex, "n_paired": int(len(g)),
                           "raw_median": round(float(g["raw_total"].median()), 1),
                           "sp_median": round(float(g["sp_total"].median()), 1),
                           "median_uplift_pct":
                               round(float(uplift.median()), 1)})
    pd.DataFrame(equip_rows).to_csv(os.path.join(OUT, "equipment.csv"), index=False)

    # ------------------------------------------------------------------
    # Headline summary
    # ------------------------------------------------------------------
    summary = {
        "n_entries_sbd": int(len(entries)),
        "n_raw_lifters": int(len(raw)),
        "n_sp_lifters": int(len(sp)),
        "overall_percentiles": overall,
        "peak_age": peaks,
        "sex_gap_total": {"first": gap_first, "last": gap_last},
        "growth_since_2010": growth,
        "equipment_uplift_paired":
            {r["sex"]: {"n": r["n_paired"], "median_pct": r["median_uplift_pct"]}
             for r in equip_rows},
        "median_total_raw": {
            "M": round(float(raw[raw["Sex"] == "M"]["TotalKg"].median()), 1),
            "F": round(float(raw[raw["Sex"] == "F"]["TotalKg"].median()), 1)},
    }
    with open(os.path.join(OUT, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2)[:2000])


if __name__ == "__main__":
    main()
