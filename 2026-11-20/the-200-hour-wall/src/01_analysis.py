#!/usr/bin/env python3
"""
Build #74 — The 200-Hour Wall (relationships, 2026-11-20)

Question: how long does it actually take an adult to make a new close
friend, in years, at the rate adults really spend time with friends?

Ingredients
-----------
1. Hall (2019), "How many hours does it take to make a friend?",
   Journal of Social and Personal Relationships 36(4), 1278-1296.
   Pooled thresholds (the famous version): ~50 hours to a casual
   friend, ~90 to a friend, 200+ to a close friend. Adult-only
   thresholds (from the paper, via Greater Good's summary): 94 hours
   to a casual friend, 164 to a friend, ~264 to a close friend
   (164 + ~100 more). Students move faster: 43 / 57 / ~119.
   Two more facts from the same paper matter here: hours spent
   working together do not move closeness, only relaxed time does;
   and the students who upgraded a friendship doubled their hours
   with that person and halved time with everyone else. Concentration
   is the mechanism, not total social time.

2. American Time Use Survey diary microdata, 2003-2025 (BLS),
   as aggregated in the committed extract from the 2026-11-02 build
   ("The Friendless Day"): one row per diary day, survey-weighted
   minutes with a friend present (nonwork minutes only).
   This script recomputes the age curve from that extract when it is
   present in the repo; otherwise it reads the committed aggregate
   in data/age_friend_hours.csv, so the build reproduces standalone.

Model
-----
Years to a threshold T for a person in age band A, if a new friend
gets share s of that band's total annual friend hours:

    years = T / (annual_friend_hours[A] * s)

Shares: 1.0 = every friend minute goes to the one new person
(an impossible upper bound on speed); 0.5, 0.33, 0.2 (one of five
close friends), 0.1. The model is deliberately optimistic: ATUS
"friend present" minutes count group hangouts, where the new person
may be one of several, so true dyadic hours are lower, and the
clock here assumes no decay, no missed weeks, and no chemistry
failure. Real years are longer than these.

Outputs: data/age_friend_hours.csv, data/years_to_friend.csv,
data/cadence.csv, data/results.json (all printed too).
"""

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)          # project folder
REPO = os.path.dirname(os.path.dirname(ROOT))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

EXTRACT = os.path.join(
    REPO, "2026-11-02", "the-friendless-day", "data", "respondent_day.csv"
)
AGGREGATE = os.path.join(DATA, "age_friend_hours.csv")

AGE_ORDER = ["15-24", "25-34", "35-44", "45-54", "55-64", "65+"]
ERAS = ["2003-07", "2021-25"]

# Hall (2019) thresholds, cumulative hours from first meeting.
LADDERS = {
    "pooled": {"casual": 50, "friend": 90, "close": 200},
    "adult": {"casual": 94, "friend": 164, "close": 264},
    "student": {"casual": 43, "friend": 100, "close": 119},
}
SHARES = [1.0, 0.5, 0.33, 0.2, 0.1]
CADENCE_HRS_WK = [0.5, 1, 2, 3, 5, 8]


def weighted_mean_se(g):
    w = g["TUFINLWGT"].to_numpy(dtype=float)
    x = g["friend_min"].to_numpy(dtype=float)
    m = (w * x).sum() / w.sum()
    neff = w.sum() ** 2 / (w ** 2).sum()
    var = (w * (x - m) ** 2).sum() / w.sum()
    return m, float(np.sqrt(var / neff)), len(g)


def build_age_table():
    """Weighted friend minutes/day by age band and era."""
    if os.path.exists(EXTRACT):
        df = pd.read_csv(
            EXTRACT, usecols=["era", "ageband", "TUFINLWGT", "friend_min"]
        )
        rows = []
        for era in ERAS:
            for ab in AGE_ORDER:
                g = df[(df.era == era) & (df.ageband == ab)]
                m, se, n = weighted_mean_se(g)
                rows.append({
                    "era": era, "ageband": ab, "n": n,
                    "friend_min_day": round(m, 2),
                    "se_min_day": round(se, 2),
                    "friend_hrs_year": round(m * 365 / 60, 1),
                })
        tab = pd.DataFrame(rows)
    else:
        tab = pd.read_csv(AGGREGATE)
        print("extract not found, using committed aggregate", file=sys.stderr)
    tab.to_csv(os.path.join(DATA, "age_friend_hours.csv"), index=False)
    return tab


def years_to_threshold(annual_hrs, threshold, share):
    return threshold / (annual_hrs * share)


def main():
    tab = build_age_table()
    print(tab.to_string(index=False))

    # --- core table: years to each rung, 2021-25, by age and share ---
    cur = tab[tab.era == "2021-25"].set_index("ageband")
    rows = []
    for ab in AGE_ORDER:
        hrs = cur.loc[ab, "friend_hrs_year"]
        for ladder_name, ladder in LADDERS.items():
            if ladder_name == "student":
                continue  # student ladder only applies to the 15-24 band
            for rung, t in ladder.items():
                for s in SHARES:
                    rows.append({
                        "ageband": ab, "ladder": ladder_name, "rung": rung,
                        "threshold_hrs": t, "share": s,
                        "annual_friend_hrs": hrs,
                        "hrs_with_new_person_per_year": round(hrs * s, 1),
                        "years": round(years_to_threshold(hrs, t, s), 2),
                    })
    # student ladder for the youngest band only
    hrs_young = cur.loc["15-24", "friend_hrs_year"]
    for rung, t in LADDERS["student"].items():
        for s in SHARES:
            rows.append({
                "ageband": "15-24", "ladder": "student", "rung": rung,
                "threshold_hrs": t, "share": s,
                "annual_friend_hrs": hrs_young,
                "hrs_with_new_person_per_year": round(hrs_young * s, 1),
                "years": round(years_to_threshold(hrs_young, t, s), 2),
            })
    ytf = pd.DataFrame(rows)
    ytf.to_csv(os.path.join(DATA, "years_to_friend.csv"), index=False)

    # --- cadence table: dedicated hrs/week with the new person ---
    cad = []
    for hw in CADENCE_HRS_WK:
        annual = hw * 52
        cad.append({
            "hrs_per_week_with_new_person": hw,
            "hrs_per_year": annual,
            "years_to_casual_pooled_50h": round(50 / annual, 2),
            "years_to_friend_pooled_90h": round(90 / annual, 2),
            "years_to_close_pooled_200h": round(200 / annual, 2),
            "years_to_close_adult_264h": round(264 / annual, 2),
        })
    cad = pd.DataFrame(cad)
    cad.to_csv(os.path.join(DATA, "cadence.csv"), index=False)

    # --- era comparison: years to close friend at a 1-in-5 share ---
    era_rows = []
    for era in ERAS:
        sub = tab[tab.era == era].set_index("ageband")
        for ab in AGE_ORDER:
            hrs = sub.loc[ab, "friend_hrs_year"]
            era_rows.append({
                "era": era, "ageband": ab,
                "annual_friend_hrs": hrs,
                "years_to_close_200h_share20": round(200 / (hrs * 0.2), 2),
                "years_to_close_264h_share20": round(264 / (hrs * 0.2), 2),
            })
    era_df = pd.DataFrame(era_rows)

    # --- headline numbers ---
    def y(ab, ladder, rung, share, era="2021-25"):
        hrs = tab[(tab.era == era) & (tab.ageband == ab)].iloc[0]["friend_hrs_year"]
        return round(LADDERS[ladder][rung] / (hrs * share), 1)

    results = {
        "annual_friend_hours_2021_25": {
            ab: float(cur.loc[ab, "friend_hrs_year"]) for ab in AGE_ORDER
        },
        "annual_friend_hours_2003_07": {
            ab: float(tab[(tab.era == "2003-07") & (tab.ageband == ab)]
                      .iloc[0]["friend_hrs_year"]) for ab in AGE_ORDER
        },
        "headline": {
            "years_to_close_friend_35_44_share20_pooled200h":
                y("35-44", "pooled", "close", 0.2),
            "years_to_close_friend_35_44_share20_adult264h":
                y("35-44", "adult", "close", 0.2),
            "years_to_close_friend_35_44_share100_pooled200h":
                y("35-44", "pooled", "close", 1.0),
            "years_to_close_friend_35_44_share100_adult264h":
                y("35-44", "adult", "close", 1.0),
            "years_to_close_friend_15_24_share20_pooled200h":
                y("15-24", "pooled", "close", 0.2),
            "years_to_close_friend_15_24_share20_student119h":
                y("15-24", "student", "close", 0.2),
            "years_to_close_friend_25_34_share20_pooled200h":
                y("25-34", "pooled", "close", 0.2),
            "years_to_casual_friend_35_44_share20_pooled50h":
                y("35-44", "pooled", "casual", 0.2),
            "years_to_casual_friend_35_44_share20_adult94h":
                y("35-44", "adult", "casual", 0.2),
        },
        "era_comparison_years_to_close_200h_share20": {
            ab: {
                "2003-07": float(era_df[(era_df.era == "2003-07")
                                        & (era_df.ageband == ab)]
                                 .iloc[0]["years_to_close_200h_share20"]),
                "2021-25": float(era_df[(era_df.era == "2021-25")
                                        & (era_df.ageband == ab)]
                                 .iloc[0]["years_to_close_200h_share20"]),
            } for ab in AGE_ORDER
        },
        "trip_equivalence": {
            "three_day_trip_waking_hrs_together": 30,
            "typical_new_person_share_hrs_per_year_35_44": round(
                float(cur.loc["35-44", "friend_hrs_year"]) * 0.2, 1),
            "monthly_two_hr_dinner_hrs_per_year": 24,
            "years_of_monthly_dinners_one_trip_equals": round(30 / 24, 2),
        },
        "sensitivity_35_44_share20": {
            str(t): round(t / (float(cur.loc["35-44", "friend_hrs_year"]) * 0.2), 1)
            for t in [150, 200, 264, 300]
        },
        "notes": (
            "ATUS friend minutes are nonwork minutes with a friend present, "
            "survey-weighted, diary-day means. The model assumes every counted "
            "minute is dyadic time with the new person at the stated share, "
            "no decay, no missed weeks. Real years are longer: group hangouts "
            "split the minutes across several people, and Hall's thresholds "
            "count relaxed time only, not work/school time together."
        ),
    }
    with open(os.path.join(DATA, "results.json"), "w") as f:
        json.dump(results, f, indent=2)

    print("\n--- headline ---")
    print(json.dumps(results["headline"], indent=2))
    print("\n--- era comparison (years to close friend, 200h, 1-in-5 share) ---")
    print(era_df.pivot(index="ageband", columns="era",
                        values="years_to_close_200h_share20").to_string())
    print("\n--- cadence ---")
    print(cad.to_string(index=False))
    print("\nWrote data/age_friend_hours.csv, data/years_to_friend.csv, "
          "data/cadence.csv, data/results.json")


if __name__ == "__main__":
    main()
