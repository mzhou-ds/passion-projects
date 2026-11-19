#!/usr/bin/env python3
"""Parse StatCan table 98-10-0617-01 (2021 Census, 25% sample):
All languages spoken at home by mother tongue, knowledge of official languages
and generation status.

The full-table CSV is 5.3 GB in WIDE format: the "All languages spoken at home
(11)" dimension is one value column per member, not a long dimension. Verified
from the header row:
  ...,"All languages spoken at home (11):Total - All languages spoken at home[1]",
  Symbol,"All languages spoken at home (11):English[2]",Symbol,...,[11]
The mutually exclusive home-language categories are [2] English, [3] French,
[4] Non-official language, [7] English and French, [8] English and non-official,
[9] French and non-official, [10] English, French and non-official,
[11] Multiple non-official. ([5] Indigenous / [6] Non-Indigenous are sub-splits
of [4]; verified the eight sum to [1] exactly on the first data row.)

Mother tongue: the "Chinese languages" aggregate row already sums its eight
children (Mandarin, Yue (Cantonese), Hakka, Min Dong, Min Nan, Wu, Chinese
n.o.s., Chinese languages n.i.e.), so the headline numerator uses the aggregate
only; the children are kept for a Mandarin-vs-Cantonese split.

Speed: byte-level pre-filter keeps only lines whose GEO is Canada or one of
the six CMAs before csv-parsing, so the 5.3 GB scan runs in ~1-2 minutes.

Outputs (data/):
  ca_retention.csv -- geo x generation: total pop, Chinese mother tongue, share
  ca_homeuse.csv   -- geo x generation, conditional on Chinese mother tongue:
                     total, speaks any non-official language at home, share
  ca_mt_split.csv  -- geo x generation x Chinese mother-tongue component
  ca_age.csv       -- geo x generation x age group: total, Chinese MT, share
"""
import csv
import io
import zipfile
from collections import defaultdict

ZIP = "data/statcan_98100617.zip"

GEO_KEYS = [
    (b"2021,Canada,", "Canada"),
    (b"Toronto (CMA)", "Toronto"),
    (b"Vancouver (CMA)", "Vancouver"),
    (b"Montr\xc3\xa9al (CMA)", "Montreal"),
    (b"Calgary (CMA)", "Calgary"),
    (b"Edmonton (CMA)", "Edmonton"),
    (b"Ottawa - Gatineau (CMA)", "Ottawa-Gatineau"),
]

GENERATIONS = ("Total - Generation status", "First generation",
               "Second generation", "Third generation or more")
AGE_GROUPS = ("0 to 14 years", "15 to 24 years", "25 to 34 years",
              "35 to 44 years", "45 to 54 years", "55 to 64 years",
              "65 to 74 years", "75 years and over")
CHINESE_CHILDREN = ("Hakka", "Mandarin", "Min Dong",
                    "Min Nan (Chaochow, Teochow, Fukien, Taiwanese)",
                    "Wu (Shanghainese)", "Yue (Cantonese)",
                    "Chinese, n.o.s.", "Chinese languages, n.i.e.")


def home_col(header, n):
    for i, h in enumerate(header):
        if h.endswith(f"[{n}]") and "All languages spoken at home" in h:
            return i
    raise KeyError(f"home column [{n}] not found")


def main():
    zf = zipfile.ZipFile(ZIP)
    data_name = [n for n in zf.namelist() if n.endswith(".csv") and "Meta" not in n][0]

    retention = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    homeuse = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    mt_split = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    age_ret = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float))))

    with zf.open(data_name) as raw:
        header_line = raw.readline()
        header = next(csv.reader(io.StringIO(header_line.decode("utf-8"))))
        i_geo = header.index("GEO")
        i_know = header.index("Knowledge of official languages (5)")
        i_gen = header.index("Generation status (4)")
        i_age = header.index("Age (12)")
        i_gender = header.index("Gender (3)")
        i_mt = header.index("Mother tongue (241)")
        c_total = home_col(header, 1)
        c_nonoff = home_col(header, 4)
        c_eng_nonoff = home_col(header, 8)
        c_fr_nonoff = home_col(header, 9)
        c_eng_fr_nonoff = home_col(header, 10)
        c_multi_nonoff = home_col(header, 11)
        print("home columns:", c_total, c_nonoff, c_eng_nonoff, c_fr_nonoff,
              c_eng_fr_nonoff, c_multi_nonoff)

        n_scanned = 0
        n_kept = 0
        for line in raw:
            n_scanned += 1
            geo_label = None
            for key, label in GEO_KEYS:
                if key in line:
                    geo_label = label
                    break
            if geo_label is None:
                continue
            row = next(csv.reader(io.StringIO(line.decode("utf-8", errors="replace"))))
            if row[i_know] != "Total - Knowledge of official languages":
                continue
            if row[i_gender] != "Total - Gender":
                continue
            gen = row[i_gen]
            if gen not in GENERATIONS:
                continue
            mt = row[i_mt]
            age = row[i_age]
            total_home = float(row[c_total] or 0)
            any_nonoff = sum(float(row[c] or 0) for c in
                             (c_nonoff, c_eng_nonoff, c_fr_nonoff,
                              c_eng_fr_nonoff, c_multi_nonoff))
            n_kept += 1
            if age == "Total - Age":
                if mt == "Total - Mother tongue":
                    retention[geo_label][gen]["total"] += total_home
                elif mt == "Chinese languages":
                    retention[geo_label][gen]["chinese"] += total_home
                    homeuse[geo_label][gen]["total"] += total_home
                    homeuse[geo_label][gen]["any_nonoff"] += any_nonoff
                elif mt in CHINESE_CHILDREN:
                    mt_split[geo_label][gen][mt] += total_home
            if age in AGE_GROUPS:
                if mt == "Total - Mother tongue":
                    age_ret[geo_label][gen][age]["total"] += total_home
                elif mt == "Chinese languages":
                    age_ret[geo_label][gen][age]["chinese"] += total_home
            if n_scanned % 5_000_000 == 0:
                print(f"  ...{n_scanned/1e6:.0f}M lines scanned, {n_kept} kept", flush=True)

    print(f"scanned {n_scanned} lines, kept {n_kept} rows")

    with open("data/ca_retention.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["geography", "generation", "population_total", "chinese_mt",
                    "chinese_mt_share"])
        for geo in sorted(retention):
            for gen in sorted(retention[geo]):
                tot = retention[geo][gen]["total"]
                chi = retention[geo][gen]["chinese"]
                w.writerow([geo, gen, int(tot), int(chi),
                            round(chi / tot, 6) if tot else ""])
    with open("data/ca_homeuse.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["geography", "generation", "chinese_mt_total",
                    "speaks_non_official_at_home", "share"])
        for geo in sorted(homeuse):
            for gen in sorted(homeuse[geo]):
                tot = homeuse[geo][gen]["total"]
                no = homeuse[geo][gen]["any_nonoff"]
                w.writerow([geo, gen, int(tot), int(no),
                            round(no / tot, 6) if tot else ""])
    with open("data/ca_mt_split.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["geography", "generation", "mother_tongue", "count"])
        for geo in sorted(mt_split):
            for gen in sorted(mt_split[geo]):
                for mt in sorted(mt_split[geo][gen]):
                    w.writerow([geo, gen, mt, int(mt_split[geo][gen][mt])])
    with open("data/ca_age.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["geography", "generation", "age", "population_total",
                    "chinese_mt", "chinese_mt_share"])
        for geo in sorted(age_ret):
            for gen in sorted(age_ret[geo]):
                for age in sorted(age_ret[geo][gen]):
                    tot = age_ret[geo][gen][age]["total"]
                    chi = age_ret[geo][gen][age]["chinese"]
                    w.writerow([geo, gen, age, int(tot), int(chi),
                                round(chi / tot, 6) if tot else ""])
    print("wrote data/ca_retention.csv, data/ca_homeuse.csv, "
          "data/ca_mt_split.csv, data/ca_age.csv")


if __name__ == "__main__":
    main()
