"""Build occasion-level NHANES dietary data for build #61.

Reads DR1IFF/DR2IFF (cycles 2007-08 .. 2017-18) from the local copy kept
by build #56 (2026-10-28/nutritional-jetlag/data/raw/) and collapses food
items into eating occasions: one row per (person, clock time, occasion
name). Also keeps a slim item-level file for the food-group decomposition.

Occasion-name codes (NHANES codebook, DRx_030Z):
  breakfast: 1, 10 (Desayuno)
  lunch:     2, 12 (Comida), 11 (Almuerzo), 5 (Brunch)
  dinner:    3, 4 (Supper), 14 (Cena)
  snack:     6, 13 (Merienda), 15 (Entre comida), 16 (Botana),
             17 (Bocadillo), 18 (Tentempie)
  drink:     7, 19 (Bebida)
  other:     9, 99
  infant feeding (8): dropped
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data")
RAW = "/home/hatch/workspace/passion-projects/2026-10-28/nutritional-jetlag/data/raw"
CYCLES = {2007: "E", 2009: "F", 2011: "G", 2013: "H", 2015: "I", 2017: "J"}

BREAKFAST = {1, 10}
LUNCH = {2, 12, 11, 5}
DINNER = {3, 4, 14}
SNACK = {6, 13, 15, 16, 17, 18}
DRINK = {7, 19}

MEAL_OF = {}
for c in BREAKFAST:
    MEAL_OF[c] = "breakfast"
for c in LUNCH:
    MEAL_OF[c] = "lunch"
for c in DINNER:
    MEAL_OF[c] = "dinner"
for c in SNACK:
    MEAL_OF[c] = "snack"
for c in DRINK:
    MEAL_OF[c] = "drink"

ITEM_COLS = ["SEQN", "DR{day}DRSTZ", "DR{day}DAY", "DR{day}_020", "DR{day}_030Z",
             "DR{day}IFDCD", "DR{day}IGRMS", "DR{day}IKCAL", "DR{day}IPROT",
             "DR{day}ICARB", "DR{day}ISUGR", "DR{day}IFIBE", "DR{day}ITFAT",
             "DR{day}ISODI", "DR{day}ICAFF", "WTDRD1", "WTDR2D"]


def load_day(start, sfx, day):
    df = pd.read_sas(os.path.join(RAW, f"DR{day}IFF_{sfx}.xpt"),
                     format="xport")
    cols = [c.format(day=day) for c in ITEM_COLS]
    df = df[cols].copy()
    df = df.rename(columns={
        f"DR{day}DRSTZ": "reliable", f"DR{day}DAY": "dow",
        f"DR{day}_020": "t_sec", f"DR{day}_030Z": "occ",
        f"DR{day}IFDCD": "foodcode", f"DR{day}IGRMS": "grams",
        f"DR{day}IKCAL": "kcal", f"DR{day}IPROT": "protein",
        f"DR{day}ICARB": "carb", f"DR{day}ISUGR": "sugar",
        f"DR{day}IFIBE": "fiber", f"DR{day}ITFAT": "fat",
        f"DR{day}ISODI": "sodium", f"DR{day}ICAFF": "caffeine"})
    df["cycle"] = f"{start}-{str(start + 1)[-2:]}"
    df["day"] = day
    # SAS missing sentinels arrive as denormal-tiny floats.
    df.loc[(df["t_sec"] < 0) | (df["t_sec"] >= 86400) |
           ((df["t_sec"] > 0) & (df["t_sec"] < 60)), "t_sec"] = np.nan
    df = df.dropna(subset=["t_sec"])
    df = df[df["occ"] != 8]  # infant feeding
    df["t_h"] = df["t_sec"] / 3600.0
    for c in ["kcal", "sugar", "protein", "carb", "fat", "fiber", "sodium",
              "grams", "caffeine"]:
        df.loc[(df[c] < 0) | (df[c] > 10000), c] = np.nan
    df["meal"] = df["occ"].map(MEAL_OF).fillna("other")
    df["foodgrp1"] = (df["foodcode"].astype("Int64").astype(str).str[0])
    df["foodgrp2"] = (df["foodcode"].astype("Int64").astype(str).str[:2])
    return df


def main():
    items, demos = [], []
    for start, sfx in CYCLES.items():
        for day in (1, 2):
            d = load_day(start, sfx, day)
            items.append(d)
            print("cycle", sfx, "day", day, len(d), "items")
        demo = pd.read_sas(os.path.join(RAW, f"DEMO_{sfx}.xpt"),
                           format="xport")[["SEQN", "RIAGENDR", "RIDAGEYR",
                                            "RIDRETH1", "DMDEDUC2",
                                            "INDFMPIR"]]
        bmx = pd.read_sas(os.path.join(RAW, f"BMX_{sfx}.xpt"),
                          format="xport")[["SEQN", "BMXBMI"]]
        demo = demo.merge(bmx, on="SEQN", how="left")
        demo["cycle"] = f"{start}-{str(start + 1)[-2:]}"
        demos.append(demo)
    items = pd.concat(items, ignore_index=True)
    demo = pd.concat(demos, ignore_index=True)
    demo = demo.rename(columns={"RIAGENDR": "sex", "RIDAGEYR": "age",
                                "RIDRETH1": "race", "INDFMPIR": "pir",
                                "BMXBMI": "bmi"})
    items = items.merge(demo, on=["SEQN", "cycle"], how="left")
    items.to_parquet(os.path.join(OUT, "items.parquet"), index=False)

    # Collapse items -> occasions (person, clock time, occasion name).
    occ = (items.groupby(["SEQN", "cycle", "day", "t_h", "occ", "meal",
                          "reliable", "dow", "WTDRD1", "WTDR2D", "sex",
                          "age", "race", "pir", "bmi"], as_index=False,
                         observed=True)
           .agg(kcal=("kcal", "sum"), sugar=("sugar", "sum"),
                protein=("protein", "sum"), carb=("carb", "sum"),
                fat=("fat", "sum"), fiber=("fiber", "sum"),
                sodium=("sodium", "sum"), grams=("grams", "sum"),
                caffeine=("caffeine", "sum"), n_items=("kcal", "size")))
    # Person-day totals for the plausibility filter.
    day_tot = (items.groupby(["SEQN", "cycle", "day"], as_index=False)
               .agg(day_kcal=("kcal", "sum")))
    occ = occ.merge(day_tot, on=["SEQN", "cycle", "day"], how="left")
    occ = occ[occ["kcal"] > 0].copy()
    occ["sugar_share"] = occ["sugar"] * 4.0 / occ["kcal"]  # share of kcal from sugar
    occ["sugar_per_100kcal"] = occ["sugar"] / occ["kcal"] * 100.0
    occ["prot_share"] = occ["protein"] * 4.0 / occ["kcal"]
    occ["fiber_per_100kcal"] = occ["fiber"] / occ["kcal"] * 100.0
    occ["age_band"] = pd.cut(occ["age"], [0, 11, 19, 29, 44, 59, 79],
                             labels=["2-11", "12-19", "20-29", "30-44",
                                     "45-59", "60-79"])
    occ.to_parquet(os.path.join(OUT, "occasions.parquet"), index=False)
    print("occasions:", len(occ))
    print(occ["meal"].value_counts().to_dict())


if __name__ == "__main__":
    main()
