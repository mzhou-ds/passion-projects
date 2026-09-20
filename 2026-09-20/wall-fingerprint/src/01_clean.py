"""01_clean.py — load Berlin 2016-2019 + Boston 2016, parse times, derive pacing features.

Outputs:
  output/berlin_clean.parquet  — one row per finisher, per-5k segment paces + relatives
  output/boston_clean.parquet  — same for Boston 2016 (+ age)
"""
import re
import numpy as np
import pandas as pd

SEG_BOUNDS = [5, 10, 15, 20, 21.0975, 25, 30, 35, 40, 42.195]  # km


def to_sec(s):
    """Parse H:MM:SS or M:SS (or '-') -> seconds."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return np.nan
    s = str(s).strip()
    if s in ("", "-", "--:--:--"):
        return np.nan
    parts = s.split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        return np.nan
    if len(parts) == 3:
        h, m, sec = parts
    elif len(parts) == 2:
        h, m, sec = 0, parts[0], parts[1]
    else:
        return np.nan
    return h * 3600 + m * 60 + sec


def segment_paces(row, split_cols):
    """From cumulative split seconds -> per-segment pace (sec/km) for each 5k
    segment plus final 2.195k. Returns list aligned to SEG_BOUNDS."""
    prev_t, prev_d = 0.0, 0.0
    paces = []
    cum = [row[c] for c in split_cols] + [row["time_full_s"]]
    for d, t in zip(SEG_BOUNDS, cum):
        if np.isnan(t) or t <= prev_t:
            paces.append(np.nan)
        else:
            paces.append((t - prev_t) / (d - prev_d))
        prev_t, prev_d = t, d
    return paces


def clean_berlin():
    frames = []
    for year in (2016, 2017, 2018, 2019):
        df = pd.read_csv(f"data/berlin-{year}.csv")
        df["year"] = year
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    print(f"berlin raw rows: {len(df)}")

    splits = ["split_5k", "split_10k", "split_15k", "split_20k",
              "time_half", "split_25k", "split_30k", "split_35k", "split_40k"]
    for c in splits:
        df[c + "_s"] = df[c].map(to_sec)
    df["time_full_s"] = df["time_full"].map(to_sec)

    # drop DNF-ish / nonsense: no finish time, sub-2h or >8h
    df = df[df["time_full_s"].between(2 * 3600, 8 * 3600)]
    df = df.dropna(subset=["time_full_s"] + [c + "_s" for c in splits] + ["time_full_s"])
    df = df[df["gender"].isin(["M", "W", "F"])]
    df["gender"] = df["gender"].map({"M": "M", "W": "F", "F": "F"})

    seg_cols = [f"seg{i}" for i in range(len(SEG_BOUNDS))]
    paces = df.apply(lambda r: segment_paces(
        {c + "_s": r[c + "_s"] for c in splits} | {"time_full_s": r["time_full_s"]},
        [c + "_s" for c in splits]), axis=1, result_type="expand")
    paces.columns = seg_cols
    df = df.reset_index(drop=True)
    paces = paces.reset_index(drop=True)
    df = pd.concat([df, paces], axis=1)
    # drop rows with any invalid segment
    df = df.dropna(subset=seg_cols)
    df["avg_pace"] = df["time_full_s"] / 42.195
    for i, c in enumerate(seg_cols):
        df[f"rel{i}"] = df[c] / df["avg_pace"]  # 1.0 = even; >1 = slower than avg

    keep = ["year", "gender", "nationality", "time_full_s", "avg_pace"] + \
           seg_cols + [f"rel{i}" for i in range(len(seg_cols))]
    df = df[keep]
    df.to_pickle("output/berlin_clean.pkl")
    print(f"berlin clean rows: {len(df)} "
          f"({(df.gender=='M').sum()} M, {(df.gender=='F').sum()} F)")


def clean_boston():
    df = pd.read_csv("data/boston-2016.csv")
    print(f"boston raw rows: {len(df)}")
    splits = ["5K", "10K", "15K", "20K", "Half", "25K", "30K", "35K", "40K"]
    for c in splits:
        df[c + "_s"] = df[c].map(to_sec)
    df["time_full_s"] = df["Official Time"].map(to_sec)
    df = df[df["time_full_s"].between(2 * 3600, 8 * 3600)]
    df = df.dropna(subset=[c + "_s" for c in splits] + ["time_full_s", "Age"])
    df["gender"] = df["M/F"].map({"M": "M", "F": "F"})
    df = df[df["gender"].isin(["M", "F"])]

    seg_cols = [f"seg{i}" for i in range(len(SEG_BOUNDS))]
    paces = df.apply(lambda r: segment_paces(
        {c + "_s": r[c + "_s"] for c in splits} | {"time_full_s": r["time_full_s"]},
        [c + "_s" for c in splits]), axis=1, result_type="expand")
    paces.columns = seg_cols
    df = df.reset_index(drop=True)
    paces = paces.reset_index(drop=True)
    df = pd.concat([df, paces], axis=1)
    df = df.dropna(subset=seg_cols)
    df["avg_pace"] = df["time_full_s"] / 42.195
    for i, c in enumerate(seg_cols):
        df[f"rel{i}"] = df[c] / df["avg_pace"]

    keep = ["Age", "gender", "City", "State", "Country", "time_full_s", "avg_pace"] + \
           seg_cols + [f"rel{i}" for i in range(len(seg_cols))]
    df = df[keep]
    df.to_pickle("output/boston_clean.pkl")
    print(f"boston clean rows: {len(df)} "
          f"({(df.gender=='M').sum()} M, {(df.gender=='F').sum()} F)")


if __name__ == "__main__":
    clean_berlin()
    clean_boston()
