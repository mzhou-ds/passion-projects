"""Counts + Beatport analysis for The Release Glut.

1. Discogs genre counts 2005-2026 (data/raw/discogs_counts.json):
   - raw series per genre, electronic share of the four-genre total
   - cataloguing-lag correction: pop is flat 2005-2021 (~51k/yr), so pop's
     post-2021 decline measures the lag curve; apply pop's lag factors to
     electronic (and rock) as a difference-in-differences correction.
2. Beatport Top 100 snapshot 2026-11-21 (data/raw/beatport_top100_2026-11-21.csv):
   BPM / key / length / age distributions, zombie tracks, top-10 vs rest.
Outputs: data/results_counts.json, data/beatport_summary.json
"""
import json
import os
from datetime import date

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "..", "data")
SNAP = date(2026, 11, 21)


def main():
    counts = json.load(open(os.path.join(DATA, "raw", "discogs_counts.json")))
    years = list(range(2005, 2027))
    df = pd.DataFrame({g: [counts[g][str(y)] for y in years]
                       for g in counts}, index=years)
    df.index.name = "year"
    df["four_genre_total"] = df[["electronic", "rock", "hip hop", "pop"]].sum(axis=1)
    df["electronic_share"] = df["electronic"] / df["four_genre_total"]
    df["electronic_vs_pop"] = df["electronic"] / df["pop"]

    # --- lag correction -------------------------------------------------
    # Pop is flat 2005-2021: mean 51,318. Treat that as pop's true level and
    # measure the observed/true ratio for 2022-2026 as the lag curve.
    pop_base = df.loc[2005:2021, "pop"].mean()
    lag = {}
    for y in range(2022, 2027):
        lag[y] = df.loc[y, "pop"] / pop_base
    for g in ("electronic", "rock", "hip hop"):
        df[f"{g}_lagcorr"] = df[g].astype(float)
        for y in range(2022, 2027):
            df.loc[y, f"{g}_lagcorr"] = df.loc[y, g] / lag[y]
    # rock as an alternative control: rock plateau 2014-2021 mean
    rock_base = df.loc[2014:2021, "rock"].mean()
    lag_rock = {y: df.loc[y, "rock"] / rock_base for y in range(2022, 2027)}
    df["electronic_lagcorr_rock"] = df["electronic"].astype(float)
    for y in range(2022, 2027):
        df.loc[y, "electronic_lagcorr_rock"] = df.loc[y, "electronic"] / lag_rock[y]

    # growth stats
    def growth(g, a, b):
        return df.loc[b, g] / df.loc[a, g] - 1

    res = {
        "pop_baseline_2005_2021": float(pop_base),
        "rock_baseline_2014_2021": float(rock_base),
        "lag_factors_pop_control": {str(y): round(v, 3) for y, v in lag.items()},
        "lag_factors_rock_control": {str(y): round(v, 3) for y, v in lag_rock.items()},
        "electronic_growth_2005_2020_raw": round(growth("electronic", 2005, 2020), 3),
        "rock_growth_2005_2020_raw": round(growth("rock", 2005, 2020), 3),
        "hiphop_growth_2005_2020_raw": round(growth("hip hop", 2005, 2020), 3),
        "pop_growth_2005_2020_raw": round(growth("pop", 2005, 2020), 3),
        "electronic_2020_vs_2019": round(growth("electronic", 2019, 2020), 3),
        "electronic_2025_lagcorr_pop": int(round(df.loc[2025, "electronic_lagcorr"])),
        "electronic_2025_lagcorr_rock": int(round(df.loc[2025, "electronic_lagcorr_rock"])),
        "electronic_2025_raw": int(df.loc[2025, "electronic"]),
        "electronic_peak_year_raw": int(df["electronic"].idxmax()),
        "electronic_peak_raw": int(df["electronic"].max()),
        "electronic_share_2005": round(float(df.loc[2005, "electronic_share"]), 3),
        "electronic_share_2020": round(float(df.loc[2020, "electronic_share"]), 3),
        "electronic_vs_pop_2005": round(float(df.loc[2005, "electronic_vs_pop"]), 2),
        "electronic_vs_pop_2020": round(float(df.loc[2020, "electronic_vs_pop"]), 2),
        "electronic_overtakes_rock_year": int(
            (df["electronic"] > df["rock"]).idxmax()),
    }
    df.round(1).to_csv(os.path.join(DATA, "counts_by_genre_year.csv"))
    json.dump(res, open(os.path.join(DATA, "results_counts.json"), "w"), indent=2)
    print(json.dumps(res, indent=2))

    # --- Beatport Top 100 ----------------------------------------------
    bp = pd.read_csv(os.path.join(DATA, "raw", "beatport_top100_2026-11-21.csv"),
                     parse_dates=["release_date"])
    bp["age_days"] = (pd.Timestamp(SNAP) - bp["release_date"]).dt.days
    bp["is_minor"] = bp["key"].str.contains("Min")
    bp["bpm_band"] = pd.cut(bp["bpm"], [0, 100, 122, 124, 128, 132, 136, 200],
                            labels=["<100", "100-122", "122-124", "124-128",
                                    "128-132", "132-136", "136+"])
    bs = {
        "n": int(len(bp)),
        "bpm_median": float(bp["bpm"].median()),
        "bpm_mean": round(float(bp["bpm"].mean()), 1),
        "bpm_iqr": [float(bp["bpm"].quantile(0.25)), float(bp["bpm"].quantile(0.75))],
        "bpm_in_124_136_pct": round(float(((bp["bpm"] >= 124) & (bp["bpm"] <= 136)).mean() * 100), 1),
        "bpm_in_128_132_pct": round(float(((bp["bpm"] >= 128) & (bp["bpm"] <= 132)).mean() * 100), 1),
        "minor_key_pct": round(float(bp["is_minor"].mean() * 100), 1),
        "top_keys": bp["key"].value_counts().head(5).to_dict(),
        "length_median_sec": float(bp["length_sec"].median()),
        "length_mean_min": round(float(bp["length_sec"].mean() / 60), 2),
        "length_over_6min_pct": round(float((bp["length_sec"] > 360).mean() * 100), 1),
        "age_median_days": float(bp["age_days"].median()),
        "age_mean_days": round(float(bp["age_days"].mean()), 1),
        "released_within_2wks_pct": round(float((bp["age_days"] <= 14).mean() * 100), 1),
        "released_within_4wks_pct": round(float((bp["age_days"] <= 28).mean() * 100), 1),
        "older_than_1yr": int((bp["age_days"] > 365).sum()),
        "older_than_1yr_tracks": bp.loc[bp["age_days"] > 365, ["rank", "title", "release_date", "bpm", "key"]].to_dict("records"),
        "top10_age_median_days": float(bp.loc[bp["rank"] <= 10, "age_days"].median()),
        "bottom10_age_median_days": float(bp.loc[bp["rank"] > 90, "age_days"].median()),
        "top10_bpm_median": float(bp.loc[bp["rank"] <= 10, "bpm"].median()),
        "rest_bpm_median": float(bp.loc[bp["rank"] > 10, "bpm"].median()),
    }
    # fix date serialization for zombie tracks
    for t in bs["older_than_1yr_tracks"]:
        t["release_date"] = str(t["release_date"].date())
    json.dump(bs, open(os.path.join(DATA, "beatport_summary.json"), "w"), indent=2)
    print(json.dumps(bs, indent=2, default=str))


if __name__ == "__main__":
    main()
