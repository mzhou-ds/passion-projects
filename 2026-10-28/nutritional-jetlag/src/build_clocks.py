"""Build per-person, per-day eating clocks from NHANES Individual Foods files.

For each recall day we collapse food items into eating occasions (same clock
time) and compute the day's eating clock:
  first_h   - clock time (hours) of the first calorie-bearing occasion
  last_h    - clock time of the last calorie-bearing occasion
  mid_h     - calorie-weighted midpoint: sum(time*kcal)/sum(kcal)
  window_h  - last - first
  kcal      - total kcal
  after20   - share of kcal at/after 20:00
  after22   - share of kcal at/after 22:00
  snack_pm_kcal - kcal after 20:00 at occasions the respondent called a snack
  dinner_kcal / dinner_h - kcal and calorie-weighted time of dinner-named occasions
  n_occ     - number of distinct occasion times with kcal > 0

Occasion-name codes (NHANES codebook, DRx_030Z):
  breakfast: 1, 10 (Desayuno), 5/11 brunch & Almuerzo grouped with midday below
  lunch:     2, 12 (Comida), 11 (Almuerzo), 5 (Brunch)
  dinner:    3, 4 (Supper), 14 (Cena)
  snack:     6, 13 (Merienda), 15 (Entre comida), 16 (Botana),
             17 (Bocadillo), 18 (Tentempie)
  drink:     7, 19 (Bebida)
  infant feeding (8) rows are dropped before clock construction.

Population for the pair file: age 20-79, both recalls reliable
(DRxDRSTZ == 1), each day 500-6000 kcal, at least 2 calorie occasions/day.
Two-day weight: WTDR2D (the two-day dietary sample weight).
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data")
CYCLES = {2007: "E", 2009: "F", 2011: "G", 2013: "H", 2015: "I", 2017: "J"}

SNACK = {6, 13, 15, 16, 17, 18}
DINNER = {3, 4, 14}
BREAKFAST = {1, 10}


def day_clock(path, day):
    """Aggregate one Individual Foods file to one row per person-day."""
    tcol, ocol, kcal_col = f"DR{day}_020", f"DR{day}_030Z", f"DR{day}IKCAL"
    wtcol = "WTDR2D" if day == 2 else "WTDRD1"
    cols = ["SEQN", wtcol, f"DR{day}DRSTZ", f"DR{day}DAY",
            tcol, ocol, kcal_col]
    df = pd.read_sas(path, format="xport")[cols]
    df = df.rename(columns={tcol: "t_sec", ocol: "occ", kcal_col: "kcal",
                            f"DR{day}DRSTZ": "reliable", f"DR{day}DAY": "dow",
                            wtcol: "wtd"})
    # SAS missing-value sentinels arrive as denormal-tiny floats.
    df.loc[(df["t_sec"] < 0) | (df["t_sec"] >= 86400) |
           ((df["t_sec"] > 0) & (df["t_sec"] < 60)), "t_sec"] = np.nan
    df.loc[(df["kcal"] < 0.1) | (df["kcal"] > 5000), "kcal"] = 0.0
    df = df.dropna(subset=["t_sec"])
    df = df[df["occ"] != 8]  # infant feeding
    df["t_h"] = df["t_sec"] / 3600.0
    head = df.groupby("SEQN").agg(reliable=("reliable", "first"),
                                  dow=("dow", "first"),
                                  wtd=("wtd", "first")).reset_index()
    # collapse items -> occasions (person, clock time)
    occ = (df.groupby(["SEQN", "t_h"], as_index=False)
             .agg(kcal=("kcal", "sum"),
                  is_snack=("occ", lambda s: int(any(v in SNACK for v in s))),
                  is_dinner=("occ", lambda s: int(any(v in DINNER for v in s))),
                  is_breakfast=("occ", lambda s: int(any(v in BREAKFAST for v in s)))))
    occ = occ[occ["kcal"] > 0]
    g = occ.groupby("SEQN")
    out = pd.DataFrame({
        "first_h": g["t_h"].min(),
        "last_h": g["t_h"].max(),
        "kcal": g["kcal"].sum(),
        "n_occ": g.size(),
    })
    out["mid_h"] = occ.assign(tk=occ["t_h"] * occ["kcal"]).groupby("SEQN")["tk"].sum() / out["kcal"]
    out["window_h"] = out["last_h"] - out["first_h"]
    pm = occ[occ["t_h"] >= 20]
    out["after20"] = pm.groupby("SEQN")["kcal"].sum().reindex(out.index).fillna(0) / out["kcal"]
    late = occ[occ["t_h"] >= 22]
    out["after22"] = late.groupby("SEQN")["kcal"].sum().reindex(out.index).fillna(0) / out["kcal"]
    sn = pm[pm["is_snack"] == 1]
    out["snack_pm_kcal"] = sn.groupby("SEQN")["kcal"].sum().reindex(out.index).fillna(0)
    dn = occ[occ["is_dinner"] == 1]
    out["dinner_kcal"] = dn.groupby("SEQN")["kcal"].sum().reindex(out.index).fillna(0)
    out["dinner_h"] = (dn.assign(tk=dn["t_h"] * dn["kcal"]).groupby("SEQN")["tk"].sum()
                       / out["dinner_kcal"].replace(0, np.nan))
    bf = occ[(occ["is_breakfast"] == 1) & (occ["t_h"] < 11)]
    out["has_breakfast"] = bf.groupby("SEQN")["kcal"].sum().reindex(out.index).fillna(0).gt(0).astype(int)
    out = out.reset_index().merge(head, on="SEQN", how="left")
    out["day"] = day
    return out


def main():
    days, demos = [], []
    for start, sfx in CYCLES.items():
        for day in (1, 2):
            d = day_clock(os.path.join(RAW, "raw", f"DR{day}IFF_{sfx}.xpt"), day)
            d["cycle"] = f"{start}-{str(start + 1)[-2:]}"
            days.append(d)
            print("cycle", sfx, "day", day, len(d), "person-days")
        demo = pd.read_sas(os.path.join(RAW, "raw", f"DEMO_{sfx}.xpt"),
                           format="xport")[["SEQN", "RIAGENDR", "RIDAGEYR", "RIDRETH1",
                                             "DMDEDUC2", "DMDMARTL", "INDFMPIR"]]
        bmx = pd.read_sas(os.path.join(RAW, "raw", f"BMX_{sfx}.xpt"),
                          format="xport")[["SEQN", "BMXBMI"]]
        demo = demo.merge(bmx, on="SEQN", how="left")
        demo["cycle"] = f"{start}-{str(start + 1)[-2:]}"
        demos.append(demo)
    pdays = pd.concat(days, ignore_index=True)
    demo = pd.concat(demos, ignore_index=True)
    pdays.to_parquet(os.path.join(RAW, "person_days.parquet"), index=False)

    d1 = pdays[pdays["day"] == 1].drop(columns=["day"]).add_suffix("_1").rename(columns={"SEQN_1": "SEQN", "cycle_1": "cycle"})
    d2 = pdays[pdays["day"] == 2].drop(columns=["day", "cycle"]).add_suffix("_2").rename(columns={"SEQN_2": "SEQN"})
    pairs = d1.merge(d2, on="SEQN", how="inner").merge(demo, on=["SEQN", "cycle"], how="left")
    pairs["WTDR2D"] = pairs["wtd_2"]  # two-day weight, carried on the day-2 file
    ok = (
        (pairs["reliable_1"] == 1) & (pairs["reliable_2"] == 1)
        & pairs["kcal_1"].between(500, 6000) & pairs["kcal_2"].between(500, 6000)
        & (pairs["n_occ_1"] >= 2) & (pairs["n_occ_2"] >= 2)
        & pairs["RIDAGEYR"].between(20, 79)
        & (pairs["WTDR2D"] > 0)
    )
    pairs = pairs[ok].copy()
    # dow codes: 1 = Sunday ... 7 = Saturday
    for s in ("1", "2"):
        pairs[f"weekend_{s}"] = pairs[f"dow_{s}"].isin([1, 7]).astype(int)
    pairs["pair_type"] = np.select(
        [pairs["weekend_1"] + pairs["weekend_2"] == 0,
         pairs["weekend_1"] + pairs["weekend_2"] == 2],
        ["both_weekday", "both_weekend"], default="mixed")
    pairs["age_band"] = pd.cut(pairs["RIDAGEYR"], [19, 29, 39, 49, 59, 69, 80],
                               labels=["20s", "30s", "40s", "50s", "60s", "70s"])
    pairs.to_parquet(os.path.join(RAW, "person_pairs.parquet"), index=False)
    print("pairs kept:", len(pairs))


if __name__ == "__main__":
    main()
