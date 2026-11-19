#!/usr/bin/env python3
"""Second StatCan pass (table 98-10-0617-01): mother-tongue component split by
age group for Canada, national level only. Tests whether the Cantonese tilt of
the 2nd generation is composition (older 2nd-gen are Cantonese, younger are
Mandarin) or retention (Cantonese survives better at every age).
"""
import csv
import io
import zipfile
from collections import defaultdict

ZIP = "data/statcan_98100617.zip"
AGE_GROUPS = ("0 to 14 years", "15 to 24 years", "25 to 34 years",
              "35 to 44 years", "45 to 54 years", "55 to 64 years",
              "65 to 74 years", "75 years and over")
CHINESE_CHILDREN = ("Hakka", "Mandarin", "Min Dong",
                    "Min Nan (Chaochow, Teochow, Fukien, Taiwanese)",
                    "Wu (Shanghainese)", "Yue (Cantonese)",
                    "Chinese, n.o.s.", "Chinese languages, n.i.e.")


def main():
    zf = zipfile.ZipFile(ZIP)
    data_name = [n for n in zf.namelist() if n.endswith(".csv") and "Meta" not in n][0]
    split = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    with zf.open(data_name) as raw:
        header = next(csv.reader(io.StringIO(raw.readline().decode("utf-8"))))
        i_know = header.index("Knowledge of official languages (5)")
        i_gen = header.index("Generation status (4)")
        i_age = header.index("Age (12)")
        i_gender = header.index("Gender (3)")
        i_mt = header.index("Mother tongue (241)")
        c_total = next(i for i, h in enumerate(header)
                       if h.endswith("[1]") and "All languages spoken at home" in h)
        for line in raw:
            if b"2021,Canada," not in line:
                continue
            row = next(csv.reader(io.StringIO(line.decode("utf-8", errors="replace"))))
            if row[i_know] != "Total - Knowledge of official languages":
                continue
            if row[i_gender] != "Total - Gender":
                continue
            gen = row[i_gen]
            if gen not in ("First generation", "Second generation",
                           "Third generation or more"):
                continue
            age = row[i_age]
            if age not in AGE_GROUPS:
                continue
            mt = row[i_mt]
            if mt in CHINESE_CHILDREN:
                split[gen][age][mt] += float(row[c_total] or 0)
    with open("data/ca_mt_split_age.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["generation", "age", "mother_tongue", "count"])
        for gen in split:
            for age in split[gen]:
                for mt in split[gen][age]:
                    w.writerow([gen, age, mt, int(split[gen][age][mt])])
    print("wrote data/ca_mt_split_age.csv")


if __name__ == "__main__":
    main()
