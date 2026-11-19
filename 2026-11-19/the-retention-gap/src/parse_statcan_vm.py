#!/usr/bin/env python3
"""Parse StatCan table 98-10-0324-01 (2021 Census, 25% sample):
Visible minority and population group by generation status.

Gives the denominator for the Canadian retention measure: the Chinese visible
minority population by generation status (and age), for Canada + six CMAs.

Structure: long dimensions Generation status (4), Age (15C), Statistics (3),
Population group (87); Visible minority (15) is WIDE, column [4] = Chinese.
Keep rows: GEO in set, Age in {Total, 8 coarse groups}, Statistics = Count,
Population group = Total - Population group; read the Chinese[4] column.

Output: data/ca_vm.csv -- geo x generation x age: chinese_visible_minority
"""
import csv
import io
import zipfile
from collections import defaultdict

ZIP = "data/statcan_98100324.zip"

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


def main():
    zf = zipfile.ZipFile(ZIP)
    data_name = [n for n in zf.namelist() if n.endswith(".csv") and "Meta" not in n][0]
    vm = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

    with zf.open(data_name) as raw:
        header = next(csv.reader(io.StringIO(raw.readline().decode("utf-8"))))
        i_gen = header.index("Generation status (4)")
        i_age = header.index("Age (15C)")
        i_stat = header.index("Statistics (3)")
        i_pg = header.index("Population group (87)")
        c_chinese = None
        for i, h in enumerate(header):
            if h.endswith("[4]") and "Visible minority" in h and "Chinese" in h:
                c_chinese = i
        print("chinese column:", c_chinese, header[c_chinese])
        n_scanned = 0
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
            if row[i_stat] != "Count":
                continue
            if row[i_pg] != "Total - Population group":
                continue
            gen = row[i_gen]
            if gen not in GENERATIONS:
                continue
            age = row[i_age]
            if age != "Total - Age" and age not in AGE_GROUPS:
                continue
            vm[geo_label][gen][age] += float(row[c_chinese] or 0)
    print(f"scanned {n_scanned} lines")
    with open("data/ca_vm.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["geography", "generation", "age", "chinese_visible_minority"])
        for geo in sorted(vm):
            for gen in sorted(vm[geo]):
                for age in sorted(vm[geo][gen]):
                    w.writerow([geo, gen, age, int(vm[geo][gen][age])])
    print("wrote data/ca_vm.csv")


if __name__ == "__main__":
    main()
