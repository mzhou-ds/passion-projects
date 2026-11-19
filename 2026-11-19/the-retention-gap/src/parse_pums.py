#!/usr/bin/env python3
"""Parse ACS 2022 1-year PUMS person files (csv_pus.zip) for Chinese-ancestry
heritage-language retention in the United States.

Variables (verified against the PUMS variables dictionary):
  LANP      language spoken at home: 1970 Chinese, 2000 Mandarin,
            2030 Min Nan Chinese, 2050 Cantonese (blank/N/A under age 5)
  NATIVITY  1 Native, 2 Foreign born
  ANC1P/2P  first/second ancestry: 706 Chinese
  PWGTP     person weight
  AGEP      age
  ST        state FIPS (06 CA, 36 NY, 48 TX, 53 WA, 25 MA, 34 NJ, 17 IL, ...)
  RAC1P     race: 6 Asian alone

Reads the two person files in chunks with only the needed columns, so it runs
in <1 GB RAM. Outputs weighted counts (PUMS is a sample: use PWGTP).

Outputs:
  data/us_retention.csv      -- nativity x (pop, chinese speakers at home, share)
  data/us_age.csv            -- nativity x age group
  data/us_state.csv          -- nativity x state (top states + rest)
  data/us_lanp_check.csv     -- LANP distribution among Chinese-ancestry persons
"""
import csv
import zipfile
from collections import defaultdict

import pandas as pd

ZIP = "data/pums_2022_1yr.zip"
CHINESE_LANG = {1970, 2000, 2030, 2050}
USECOLS = ["LANP", "NATIVITY", "ANC1P", "ANC2P", "PWGTP", "AGEP", "ST", "RAC1P"]

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
    print("zip members:", zf.namelist())
    files = [n for n in zf.namelist() if n.endswith(".csv")]
    print("person files:", files)

    # accumulators: weighted sums
    ret = defaultdict(float)        # (nativity, "pop"|"speakers")
    ret_age = defaultdict(float)    # (nativity, age_group, "pop"|"speakers")
    ret_state = defaultdict(float)  # (nativity, state, "pop"|"speakers")
    lanp_dist = defaultdict(float)  # LANP code among Chinese-ancestry persons
    asian_proxy = defaultdict(float)  # (nativity, "pop"|"nonenglish") for Asian alone
    n_rows = 0

    for fname in files:
        with zf.open(fname) as fh:
            for chunk in pd.read_csv(fh, usecols=USECOLS, chunksize=200_000,
                                     dtype={"LANP": "Int64", "ANC1P": "Int64",
                                            "ANC2P": "Int64"}):
                n_rows += len(chunk)
                # Chinese ancestry: either ancestry entry is 706
                is_chinese = (chunk["ANC1P"] == 706) | (chunk["ANC2P"] == 706)
                sub = chunk[is_chinese]
                speaks = sub["LANP"].isin(CHINESE_LANG)
                w = sub["PWGTP"].astype(float)
                for nat, grp in sub.groupby("NATIVITY"):
                    key = "Native" if nat == 1 else "Foreign-born"
                    ret[(key, "pop")] += float(w[grp.index].sum())
                    ret[(key, "speakers")] += float(w[grp.index][speaks[grp.index]].sum())
                    for (ag), idx in grp.groupby(grp["AGEP"].map(age_group)).groups.items():
                        ret_age[(key, ag, "pop")] += float(w.loc[idx].sum())
                        ret_age[(key, ag, "speakers")] += float(
                            w.loc[idx][speaks.loc[idx]].sum())
                    for st, idx in grp.groupby("ST").groups.items():
                        sname = STATE_NAMES.get(int(st), "Other states")
                        ret_state[(key, sname, "pop")] += float(w.loc[idx].sum())
                        ret_state[(key, sname, "speakers")] += float(
                            w.loc[idx][speaks.loc[idx]].sum())
                for code, idx in sub.groupby("LANP", dropna=False).groups.items():
                    lanp_dist[("" if pd.isna(code) else int(code))] += float(w.loc[idx].sum())
                # Asian-alone proxy (B16005D-style cross-check)
                asian = chunk[chunk["RAC1P"] == 6]
                noneng = asian["LANP"].notna() & (asian["LANP"] != 0) & (asian["LANP"] != 0)
                # LANP codes: 0 means English only? In PUMS, LANP is blank for
                # English-only speakers; non-blank = speaks another language.
                noneng = asian["LANP"].notna()
                wa = asian["PWGTP"].astype(float)
                for nat, grp in asian.groupby("NATIVITY"):
                    key = "Native" if nat == 1 else "Foreign-born"
                    asian_proxy[(key, "pop")] += float(wa[grp.index].sum())
                    asian_proxy[(key, "nonenglish")] += float(
                        wa[grp.index][noneng[grp.index]].sum())
                if n_rows % 1_000_000 < 200_000:
                    print(f"  ...{n_rows/1e6:.1f}M rows", flush=True)

    print(f"scanned {n_rows} person records")

    with open("data/us_retention.csv", "w", newline="") as f:
        wtr = csv.writer(f)
        wtr.writerow(["nativity", "population", "chinese_speakers_at_home", "share"])
        for nat in ("Native", "Foreign-born"):
            pop = ret[(nat, "pop")]
            spk = ret[(nat, "speakers")]
            wtr.writerow([nat, int(pop), int(spk), round(spk / pop, 6) if pop else ""])
    with open("data/us_age.csv", "w", newline="") as f:
        wtr = csv.writer(f)
        wtr.writerow(["nativity", "age_group", "population", "chinese_speakers_at_home", "share"])
        for nat in ("Native", "Foreign-born"):
            for ag in ("0-4", "5-17", "18-34", "35-64", "65+"):
                pop = ret_age[(nat, ag, "pop")]
                spk = ret_age[(nat, ag, "speakers")]
                wtr.writerow([nat, ag, int(pop), int(spk),
                              round(spk / pop, 6) if pop else ""])
    with open("data/us_state.csv", "w", newline="") as f:
        wtr = csv.writer(f)
        wtr.writerow(["nativity", "state", "population", "chinese_speakers_at_home", "share"])
        states = sorted({k[1] for k in ret_state})
        for nat in ("Native", "Foreign-born"):
            for st in states:
                pop = ret_state[(nat, st, "pop")]
                spk = ret_state[(nat, st, "speakers")]
                wtr.writerow([nat, st, int(pop), int(spk),
                              round(spk / pop, 6) if pop else ""])
    with open("data/us_lanp_check.csv", "w", newline="") as f:
        wtr = csv.writer(f)
        wtr.writerow(["lanp_code", "weighted_persons"])
        for code in sorted(lanp_dist, key=lambda c: (c == "", c)):
            wtr.writerow([code, int(lanp_dist[code])])
    print("Asian-alone proxy (B16005D-style):")
    for nat in ("Native", "Foreign-born"):
        pop = asian_proxy[(nat, "pop")]
        ne = asian_proxy[(nat, "nonenglish")]
        print(f"  {nat}: {int(pop):,} pop, {int(ne):,} speak non-English "
              f"({ne/pop:.3f})")
    print("wrote data/us_retention.csv, data/us_age.csv, data/us_state.csv, "
          "data/us_lanp_check.csv")


if __name__ == "__main__":
    main()
