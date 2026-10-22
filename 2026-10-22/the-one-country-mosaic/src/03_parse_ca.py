#!/usr/bin/env python3
"""Parse IRCC open-data workbooks into tidy annual CSVs.

PR file ('PR - CITZ' sheet): 3-row header (year / quarter / month),
one column per month plus quarter- and year-total columns, values
rounded to the nearest 5, '--' = suppressed (0-5). We keep only true
month columns and sum them into calendar years.

Study file ('TR - SP CITZ' sheet): one column per year, values are
study permit holders present on Dec 31 of that year.

Outputs:
  data/ca_pr_by_citizenship.csv     (country, year, persons, months_used)
  data/ca_study_by_citizenship.csv  (country, year, persons)
"""
import csv
import pathlib

import openpyxl

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"])}


def num(v):
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        if s in ("--", ""):
            return 0  # IRCC suppression: true value is 0-5
        try:
            return int(float(s))
        except ValueError:
            return 0
    return 0


def parse_pr(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["PR - CITZ"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    year_row, month_row = rows[2], rows[4]
    col_year, cur = {}, None
    for ci in range(len(year_row)):
        y = year_row[ci]
        if isinstance(y, str) and y.strip().isdigit():
            y = int(y.strip())
        if isinstance(y, (int, float)) and 1990 < y < 2100:
            cur = int(y)
        m = month_row[ci]
        if cur and isinstance(m, str) and m.strip().lower()[:3] in MONTHS:
            col_year[ci] = (cur, MONTHS[m.strip().lower()[:3]])
    annual, months_used = {}, {}
    totals = {}
    for r in rows[5:]:
        if not r or not r[0]:
            continue
        country = str(r[0]).strip()
        if not country:
            continue
        for ci, (y, m) in col_year.items():
            v = num(r[ci]) if ci < len(r) else 0
            if country.lower() == "total":
                totals[y] = totals.get(y, 0) + v
                months_used[y] = months_used.get(y, 0) + (1 if v or True else 0)
            else:
                annual[(country, y)] = annual.get((country, y), 0) + v
    return annual, totals


def parse_study(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["TR - SP CITZ"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    hdr = rows[2]
    years = {}
    for ci, v in enumerate(hdr):
        if isinstance(v, str) and v.strip().isdigit():
            v = int(v.strip())
        if isinstance(v, (int, float)) and 1990 < v < 2100:
            years[ci] = int(v)
    out = {}
    for r in rows[3:]:
        if not r or not r[0]:
            continue
        country = str(r[0]).strip()
        if not country or country.lower().startswith("total"):
            continue
        for ci, y in years.items():
            v = num(r[ci]) if ci < len(r) else 0
            if v:
                out[(country, y)] = v
    return out


def dump(annual, out_name, extra=None):
    out_path = ROOT / "data" / out_name
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["country", "year", "persons"])
        for (c, y) in sorted(annual, key=lambda t: (t[1], t[0])):
            w.writerow([c, y, annual[(c, y)]])
    yrs = sorted({y for _, y in annual})
    print(f"wrote {out_path} rows={len(annual)} years={yrs[0]}-{yrs[-1]}")
    for y in yrs:
        tot = sum(v for (_, yy), v in annual.items() if yy == y)
        print(f"  {y} total {tot:,}")


def main():
    annual, totals = parse_pr(RAW / "ca_pr_citizenship.xlsx")
    dump(annual, "ca_pr_by_citizenship.csv")
    print("file's own Total row (summed months):",
          {y: f"{totals[y]:,}" for y in sorted(totals)})
    dump(parse_study(RAW / "ca_study_citizenship.xlsx"),
         "ca_study_by_citizenship.csv")


if __name__ == "__main__":
    main()
