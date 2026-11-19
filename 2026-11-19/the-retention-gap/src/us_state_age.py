#!/usr/bin/env python3
"""Second PUMS pass: age composition of the native-born Chinese-ancestry
population by state, to test whether the New York vs California retention gap
is a cohort-composition effect (NY's native-born skew younger, i.e. children
of recent immigrants) rather than a place effect.

Also computes, for the native-born, retention by age group within the top
states (CA, NY, TX, WA) to see if the age gradient is the same everywhere.
"""
import csv
import zipfile
from collections import defaultdict

import pandas as pd

ZIP = "data/pums_2022_1yr.zip"
CHINESE_LANG = {1970, 2000, 2030, 2050}
STATE_NAMES = {6: "California", 36: "New York", 48: "Texas", 53: "Washington",
               25: "Massachusetts", 34: "New Jersey", 17: "Illinois",
               12: "Florida", 39: "Ohio", 42: "Pennsylvania"}


def age_group(a):
    if a < 5:
        return "0-4"
    if a < 18:
        return "5-17"
    if a < 35:
        return "18-34"
    if a < 65:
        return "35-64"
    return "65+"


def main():
    zf = zipfile.ZipFile(ZIP)
    comp = defaultdict(float)       # (state, age_group) -> pop, native-born Chinese ancestry
    ret_sa = defaultdict(float)     # (state, age_group, pop|speakers) native-born
    for fname in ["psam_pusa.csv", "psam_pusb.csv"]:
        with zf.open(fname) as fh:
            for chunk in pd.read_csv(fh, usecols=["LANP", "NATIVITY", "ANC1P", "ANC2P",
                                                  "PWGTP", "AGEP", "ST"],
                                     chunksize=300_000,
                                     dtype={"LANP": "Int64", "ANC1P": "Int64",
                                            "ANC2P": "Int64"}):
                chi = chunk[(chunk["ANC1P"] == 706) | (chunk["ANC2P"] == 706)]
                nat = chi[chi["NATIVITY"] == 1]
                speaks = nat["LANP"].isin(CHINESE_LANG)
                w = nat["PWGTP"].astype(float)
                ag = nat["AGEP"].map(age_group)
                for (st, a), idx in nat.groupby([nat["ST"], ag]).groups.items():
                    sname = STATE_NAMES.get(int(st), "Other states")
                    comp[(sname, a)] += float(w.loc[idx].sum())
                    ret_sa[(sname, a, "pop")] += float(w.loc[idx].sum())
                    ret_sa[(sname, a, "speakers")] += float(w.loc[idx][speaks.loc[idx]].sum())
    with open("data/us_state_age.csv", "w", newline="") as f:
        wtr = csv.writer(f)
        wtr.writerow(["state", "age_group", "native_born_pop", "share_of_state_native_born",
                      "retention"])
        states = sorted({k[0] for k in comp})
        for st in states:
            tot = sum(comp[(st, a)] for a in ("0-4", "5-17", "18-34", "35-64", "65+"))
            for a in ("0-4", "5-17", "18-34", "35-64", "65+"):
                pop = ret_sa[(st, a, "pop")]
                spk = ret_sa[(st, a, "speakers")]
                wtr.writerow([st, a, int(pop), round(pop / tot, 4) if tot else "",
                              round(spk / pop, 4) if pop and a != "0-4" else ""])
    print("wrote data/us_state_age.csv")
    df = pd.read_csv("data/us_state_age.csv")
    piv = df.pivot(index="state", columns="age_group", values="share_of_state_native_born")
    print(piv.round(3).to_string())
    print()
    print(df.pivot(index="state", columns="age_group", values="retention").round(3).to_string())


if __name__ == "__main__":
    main()
