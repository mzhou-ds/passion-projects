"""Prep: load the OpenPowerlifting bulk CSV, filter to raw full-power sanctioned
meets, and build per-lifter careers.

Inputs : data/openpowerlifting-2026-10-31/openpowerlifting-2026-10-31-4a1c65a7.csv
Outputs: data/meets_clean.parquet   (one row per meet result, filtered scope)
         data/careers.parquet      (one row per lifter)
         data/panel_stats.json
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
CSV = os.path.join(
    DATA,
    "openpowerlifting-2026-10-31",
    "openpowerlifting-2026-10-31-4a1c65a7.csv",
)

COLS = ["Name", "Sex", "Event", "Equipment", "Age", "TotalKg", "Dots",
        "BodyweightKg", "Federation", "Date", "Sanctioned"]
ZIP_URL = ("https://openpowerlifting.gitlab.io/opl-csv/files/"
           "openpowerlifting-latest.zip")
ZIP_PATH = os.path.join(DATA, "openpowerlifting-latest.zip")

DATA_END = pd.Timestamp("2026-10-31")
FIRST_MEET_MIN = pd.Timestamp("2010-01-01")
COMPLETED_CUTOFF = pd.Timestamp("2024-10-31")  # no meet in last 2y of data


def ensure_csv():
    """Download the bulk zip (GitLab Pages mirror of the official file) if the
    extracted CSV is not already under data/. The zip is ~171 MB and the CSV
    ~830 MB, so neither is committed to git; only the derived parquet files are."""
    if os.path.exists(CSV):
        return
    import urllib.request
    import zipfile
    print(f"downloading {ZIP_URL} ...")
    urllib.request.urlretrieve(ZIP_URL, ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH) as z:
        z.extractall(DATA)
    print("downloaded and extracted.")


def main():
    ensure_csv()
    df = pd.read_csv(CSV, usecols=COLS, low_memory=False)
    n_raw = len(df)
    print(f"raw rows: {n_raw:,}")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df[df["Date"].notna() & (df["Date"] <= DATA_END)]
    df = df[(df["Event"] == "SBD") & (df["Equipment"] == "Raw")
            & (df["Sanctioned"] == "Yes")]
    df = df[df["TotalKg"].notna() & (df["TotalKg"] > 0)
            & df["Dots"].notna() & (df["Dots"] > 0)
            & df["Age"].notna() & (df["Age"] >= 14) & (df["Age"] <= 85)]
    df = df[df["Name"].notna() & (df["Name"].str.strip() != "")]
    df = df.drop_duplicates(subset=["Name", "Sex", "Date", "TotalKg", "Federation"])
    print(f"after scope filters: {len(df):,}")

    df = df.sort_values(["Name", "Sex", "Date", "TotalKg"])
    g = df.groupby(["Name", "Sex"], sort=False)

    first = g["Date"].min().rename("first_date")
    last = g["Date"].max().rename("last_date")
    n_meets = g.size().rename("n_meets")
    # best-total meet: max Dots (ties -> earliest date)
    idx_best = g["Dots"].idxmax()
    best = df.loc[idx_best, ["Name", "Sex", "Date", "Age", "TotalKg", "Dots",
                             "BodyweightKg", "Federation"]].copy()
    best = best.rename(columns={"Date": "best_date", "Age": "age_best",
                                "TotalKg": "best_total", "Dots": "best_dots",
                                "BodyweightKg": "bw_at_best"})
    best = best.set_index(["Name", "Sex"])
    first_age = df.sort_values(["Name", "Sex", "Date"]).groupby(["Name", "Sex"])["Age"].first().rename("age_first")

    careers = pd.concat([first, last, n_meets, first_age, best], axis=1).reset_index()
    careers["span_years"] = (careers["last_date"] - careers["first_date"]).dt.days / 365.25
    careers["train_age_best"] = (careers["best_date"] - careers["first_date"]).dt.days / 365.25
    careers["completed"] = careers["last_date"] <= COMPLETED_CUTOFF
    # left-censoring guard: first meet must be in the well-covered era
    careers = careers[careers["first_date"] >= FIRST_MEET_MIN]
    # collision guard: age must not run backwards by >1y across a lifter's meets
    df_sorted = df.sort_values(["Name", "Sex", "Date"])
    age_drop = (df_sorted.groupby(["Name", "Sex"])["Age"]
                .apply(lambda s: (s.diff() < -1.0).any()))
    bad = set(age_drop[age_drop].index)
    careers = careers[~careers.set_index(["Name", "Sex"]).index.isin(bad)]
    careers = careers[careers["span_years"] <= 40]
    careers = careers[careers["train_age_best"] >= 0]

    # meets file with training year attached (for trajectory curves)
    first_map = careers.set_index(["Name", "Sex"])["first_date"]
    meets = df[df.set_index(["Name", "Sex"]).index.isin(
        careers.set_index(["Name", "Sex"]).index)].copy()
    meets["first_date"] = meets.set_index(["Name", "Sex"]).index.map(first_map)
    meets["train_year"] = ((meets["Date"] - meets["first_date"]).dt.days / 365.25).clip(lower=0)
    meets["age_first_cohort"] = pd.cut(
        meets.set_index(["Name", "Sex"]).index.map(
            careers.set_index(["Name", "Sex"])["age_first"]),
        bins=[0, 25, 35, 45, 200], labels=["<25", "25-34", "35-44", "45+"])

    meets.to_parquet(os.path.join(DATA, "meets_clean.parquet"), index=False)
    careers.to_parquet(os.path.join(DATA, "careers.parquet"), index=False)

    stats = {
        "raw_rows": int(n_raw),
        "scoped_rows": int(len(df)),
        "lifters": int(len(careers)),
        "lifters_by_sex": {k: int(v) for k, v in careers["Sex"].value_counts().items()},
        "meets_in_scope": int(len(meets)),
        "completed_careers": int(careers["completed"].sum()),
        "completed_3plus": int(((careers["completed"]) & (careers["n_meets"] >= 3)).sum()),
        "one_meet_lifters": int((careers["n_meets"] == 1).sum()),
        "date_range": [str(df["Date"].min().date()), str(df["Date"].max().date())],
    }
    with open(os.path.join(DATA, "panel_stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
