"""
02_kinship_model.py - the cousin arithmetic.

The model is deliberately simple period arithmetic, stated in full so
anyone can argue with it:

For a focal child born in year Y in a country with period total
fertility rate TFR(t):

  parents' generation gap  G = 29 years (roughly the mean age at
                             childbearing across the window in all
                             three countries; sensitivity in the README)
  aunts + uncles  AU(Y) = 2 * max(TFR(Y-G) - 1, 0)
      Each parent's sibling count is set by the fertility of the
      grandparents' era, centred on the year the parents were born.
  cousins         C(Y)  = AU(Y) * TFR(Y)
      Aunts and uncles are roughly the parents' age, so their fertility
      is proxied by the period TFR around the focal child's birth.
  siblings        S(Y)  = max(TFR(Y) - 1, 0)   (expected, completed)
  reunion kin     R(Y)  = 2 parents + 4 grandparents + S + AU + C
      (a headcount of living-at-birth kin within two generations up
       and one across; mortality is NOT modelled, so read R as the
       size of the tree, not the size of the room in any given year)

The compounding is the point: C is a *product* of two fertility terms
from two different generations, so a proportional fall in TFR hits
cousins roughly twice (in percentage terms), and the aunts/uncles leg
lags the fertility fall by one generation. Cousins peak a generation
after fertility peaks.

Projection years (2024-2055) hold TFR at its 2023 level for each
country. That is a scenario, not a forecast, and is labelled as such
in every output (column `projected`).

Outputs: data/kinship_by_year.csv, data/scenarios.csv, data/model.json
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
GEN = 29
COUNTRIES = ["United States", "Canada", "China"]


def load_tfr():
    f = pd.read_csv(os.path.join(DATA, "fertility_un_owid.csv"))
    out = {}
    for c in COUNTRIES + ["World"]:
        s = f[f.Entity == c].set_index("Year")["Fertility rate"].sort_index()
        out[c] = s
    return out


def tfr_at(series, year, last_year=2023):
    """Period TFR at `year`, holding the 2023 value flat beyond the data."""
    if year <= last_year:
        return float(series.loc[year])
    return float(series.loc[last_year])


def kin_for_year(series, year):
    au = 2 * max(tfr_at(series, year - GEN) - 1, 0)
    tfr = tfr_at(series, year)
    cousins = au * tfr
    sibs = max(tfr - 1, 0)
    reunion = 2 + 4 + sibs + au + cousins
    return {
        "year": year,
        "tfr": round(tfr, 3),
        "tfr_parents_birth_year": round(tfr_at(series, year - GEN), 3),
        "aunts_uncles": round(au, 2),
        "expected_siblings": round(sibs, 2),
        "expected_cousins": round(cousins, 2),
        "reunion_kin": round(reunion, 1),
        "projected": year > 2023,
    }


def main():
    tfr = load_tfr()
    rows = []
    for c in COUNTRIES:
        for y in range(1979, 2056):
            r = kin_for_year(tfr[c], y)
            r["country"] = c
            rows.append(r)
    kin = pd.DataFrame(rows)
    kin.to_csv(os.path.join(DATA, "kinship_by_year.csv"), index=False)

    def pick(country, year):
        r = kin[(kin.country == country) & (kin.year == year)].iloc[0]
        out = {}
        for k, v in r.items():
            if k == "country":
                continue
            if k == "projected":
                out[k] = bool(v)
            elif k == "year":
                out[k] = int(v)
            else:
                out[k] = float(v)
        return out

    us = tfr["United States"]
    peak_row = kin[(kin.country == "United States") & (~kin.projected)].loc[
        lambda d: d.expected_cousins.idxmax()]
    summary = {
        "us_tfr_2023": round(float(us.loc[2023]), 3),
        "ca_tfr_2023": round(float(tfr["Canada"].loc[2023]), 3),
        "cn_tfr_2023": round(float(tfr["China"].loc[2023]), 3),
        "us_cousin_peak": {"year": int(peak_row.year),
                           "cousins": float(peak_row.expected_cousins),
                           "aunts_uncles": float(peak_row.aunts_uncles)},
        "us_1980": pick("United States", 1980),
        "us_1990": pick("United States", 1990),
        "us_2000": pick("United States", 2000),
        "us_2010": pick("United States", 2010),
        "us_2023": pick("United States", 2023),
        "us_2055_proj": pick("United States", 2055),
        "ca_1990": pick("Canada", 1990),
        "ca_2023": pick("Canada", 2023),
        "cn_1990": pick("China", 1990),
        "cn_2023": pick("China", 2023),
    }
    # Scenario table for the site calculator presets. The last row is an
    # arithmetic scenario, NOT a measurement: two parents who are each
    # only children have, by construction, no siblings, so their child
    # has no first cousins through them whatever the local TFR is.
    scenarios = pd.DataFrame([
        {"scenario": "US baby, 1990 (cousin peak)", "aunts_uncles": summary["us_1990"]["aunts_uncles"],
         "kids_per_aunt_uncle": summary["us_1990"]["tfr"], "siblings": summary["us_1990"]["expected_siblings"]},
        {"scenario": "US baby, 2023", "aunts_uncles": summary["us_2023"]["aunts_uncles"],
         "kids_per_aunt_uncle": summary["us_2023"]["tfr"], "siblings": summary["us_2023"]["expected_siblings"]},
        {"scenario": "Canadian baby, 2023", "aunts_uncles": summary["ca_2023"]["aunts_uncles"],
         "kids_per_aunt_uncle": summary["ca_2023"]["tfr"], "siblings": summary["ca_2023"]["expected_siblings"]},
        {"scenario": "China baby, 2023", "aunts_uncles": summary["cn_2023"]["aunts_uncles"],
         "kids_per_aunt_uncle": summary["cn_2023"]["tfr"], "siblings": summary["cn_2023"]["expected_siblings"]},
        {"scenario": "US baby, 2055 (TFR flat at 2023)", "aunts_uncles": summary["us_2055_proj"]["aunts_uncles"],
         "kids_per_aunt_uncle": summary["us_2055_proj"]["tfr"], "siblings": summary["us_2055_proj"]["expected_siblings"]},
        {"scenario": "Child of two only-child parents (one-child-era scenario)",
         "aunts_uncles": 0.0, "kids_per_aunt_uncle": summary["us_2023"]["tfr"], "siblings": summary["us_2023"]["expected_siblings"]},
    ])
    scenarios["expected_cousins"] = (scenarios.aunts_uncles * scenarios.kids_per_aunt_uncle).round(2)
    scenarios.to_csv(os.path.join(DATA, "scenarios.csv"), index=False)

    with open(os.path.join(DATA, "model.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
    print(scenarios.to_string(index=False))


if __name__ == "__main__":
    main()
