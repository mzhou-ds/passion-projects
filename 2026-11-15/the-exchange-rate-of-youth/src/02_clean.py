"""02_clean.py — build the analysis sample from the OpenPowerlifting bulk CSV.

Input : data/raw/openpowerlifting-latest.zip (revision 6b8787a8, 2026-11-14,
        4,067,855 rows; fetched by src/01_fetch.py from the GitLab Pages mirror
        of the official file).
Filters (same population as build #60, minus its training-age restrictions):
  * Event == SBD (full three-lift powerlifting), Equipment == Raw
  * Sex in {M, F}, Age 14-85, BodyweightKg 40-200, Date >= 2000-01-01
  * TotalKg > 0 and all three best lifts > 0 (a completed meet)
  * Name-collision guard (as in build #60): drop lifters whose recorded age
    ever runs backwards by more than a year across meets (same name, two people).
Output: data/clean_lifts.csv (one row per lifter-meet) + data/clean_report.json
"""
import json
import zipfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent.parent
ZIP = HERE / "data" / "raw" / "openpowerlifting-latest.zip"
OUT = HERE / "data" / "clean_lifts.csv"

KEEP = ["Name", "Sex", "Event", "Equipment", "Age", "BodyweightKg",
        "Best3SquatKg", "Best3BenchKg", "Best3DeadliftKg", "TotalKg",
        "Wilks", "Date", "Federation", "Tested"]


def main():
    with zipfile.ZipFile(ZIP) as z:
        csv_name = [n for n in z.namelist() if n.endswith(".csv")][0]
        print(f"reading {csv_name} ...")
        with z.open(csv_name) as f:
            raw = pd.read_csv(f, usecols=lambda c: c in KEEP, low_memory=False)
    n_raw = len(raw)
    print(f"raw rows: {n_raw:,}")

    d = raw.copy()
    d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
    d = d[d["Event"] == "SBD"]
    d = d[d["Equipment"] == "Raw"]
    d = d[d["Sex"].isin(["M", "F"])]
    d = d[d["Date"] >= "2000-01-01"]
    for c in ["Age", "BodyweightKg", "TotalKg",
              "Best3SquatKg", "Best3BenchKg", "Best3DeadliftKg"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d[d["Age"].between(14, 85)]
    d = d[d["BodyweightKg"].between(40, 200)]
    d = d[(d["TotalKg"] > 0) & (d["Best3SquatKg"] > 0)
          & (d["Best3BenchKg"] > 0) & (d["Best3DeadliftKg"] > 0)]
    d = d.drop_duplicates(subset=["Name", "Sex", "Date", "Federation", "TotalKg"])
    d = d.sort_values(["Name", "Date"]).reset_index(drop=True)

    # name-collision guard: age must not run backwards by > 1 year
    d["age_prev"] = d.groupby(["Name", "Sex"])["Age"].shift(1)
    bad = d[(d["age_prev"] - d["Age"]) > 1][["Name", "Sex"]].drop_duplicates()
    bad_keys = set(map(tuple, bad.values))
    n_before = len(d)
    d = d[~d.apply(lambda r: (r["Name"], r["Sex"]) in bad_keys, axis=1)]
    d = d.drop(columns=["age_prev"]).reset_index(drop=True)
    print(f"name-collision guard removed {n_before - len(d):,} rows "
          f"({len(bad_keys)} lifter identities)")

    d.to_csv(OUT, index=False)
    report = {
        "raw_rows": int(n_raw),
        "clean_rows": int(len(d)),
        "lifters": int(d["Name"].nunique()),
        "men_rows": int((d["Sex"] == "M").sum()),
        "women_rows": int((d["Sex"] == "F").sum()),
        "date_min": str(d["Date"].min().date()),
        "date_max": str(d["Date"].max().date()),
        "federations": int(d["Federation"].nunique()),
        "age_range": [float(d["Age"].min()), float(d["Age"].max())],
    }
    (HERE / "data" / "clean_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
