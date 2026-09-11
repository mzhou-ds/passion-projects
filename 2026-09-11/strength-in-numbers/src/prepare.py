"""Prepare the analysis tables for the Strength in Numbers project.

Reads the OpenPowerlifting IPF-affiliate bulk CSV, filters to full-powerlifting
(SBD) results with a valid total, and builds per-lifter best-total tables
(separately for Raw and Single-ply) so repeat competitors are not double-counted
in the strength standards.

Outputs:
  output/entries_sbd.csv      — all SBD entries with TotalKg > 0 (lean columns)
  output/lifter_bests_raw.csv — one row per lifter: best Raw SBD total
  output/lifter_bests_sp.csv  — one row per lifter: best Single-ply SBD total
"""
import os
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data", "openipf-2026-09-05",
                    "openipf-2026-09-05-b8b9bf6e.csv")
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)

COLS = ["Name", "Sex", "Event", "Equipment", "Age", "BodyweightKg",
        "Best3SquatKg", "Best3BenchKg", "Best3DeadliftKg",
        "TotalKg", "Goodlift", "Dots", "Tested", "Date", "Federation"]


def main():
    print("Loading CSV ...")
    df = pd.read_csv(DATA, usecols=COLS, low_memory=False)
    print(f"  {len(df):,} rows")

    # Full powerlifting only, valid total, known sex.
    sbd = df[(df["Event"] == "SBD") & (df["TotalKg"] > 0)
             & (df["Sex"].isin(["M", "F"]))].copy()
    sbd["Date"] = pd.to_datetime(sbd["Date"], errors="coerce")
    sbd["Year"] = sbd["Date"].dt.year
    print(f"  {len(sbd):,} SBD entries with a total "
          f"({sbd['Name'].nunique():,} unique names)")

    keep = ["Name", "Sex", "Equipment", "Age", "BodyweightKg",
            "Best3SquatKg", "Best3BenchKg", "Best3DeadliftKg",
            "TotalKg", "Goodlift", "Dots", "Tested", "Year", "Federation"]
    sbd[keep].to_csv(os.path.join(OUT, "entries_sbd.csv"), index=False)

    # Per-lifter bests: the row with the max total for each (Name, Sex).
    for equip, fname in [("Raw", "lifter_bests_raw.csv"),
                         ("Single-ply", "lifter_bests_sp.csv")]:
        sub = sbd[sbd["Equipment"] == equip]
        idx = sub.groupby(["Name", "Sex"])["TotalKg"].idxmax()
        bests = sub.loc[idx, keep].reset_index(drop=True)
        bests.to_csv(os.path.join(OUT, fname), index=False)
        print(f"  {fname}: {len(bests):,} lifters, "
              f"median total {bests['TotalKg'].median():.1f} kg")

    print("Done.")


if __name__ == "__main__":
    main()
