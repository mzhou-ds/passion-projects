#!/usr/bin/env python3
"""Parse OHSS Yearbook Table 3 (LPRs by country of birth) into a tidy CSV.

The FY2024 workbook covers FY2015-2024, the FY2023 workbook FY2014-2023.
We take FY2014 from the older book and FY2015-2024 from the newer one
(the two agree on overlapping years up to OHSS rounding).

Output: data/us_lpr_by_birth_country.csv  (country, year, persons)
Values are OHSS-published cells, rounded by OHSS to the nearest 10.
"""
import csv
import pathlib

import openpyxl

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

SKIP = {"Total", "All other countries1", "Unknown"}


def parse_table3(path: pathlib.Path) -> dict:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Table 3"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    hdr = next(i for i, r in enumerate(rows)
               if r[0] and "Region and country" in str(r[0]))
    years = [int(c) for c in rows[hdr][1:] if c]
    start = next(i for i, r in enumerate(rows)
                 if r[0] and str(r[0]).strip() == "COUNTRY")
    out = {}  # (country, year) -> persons
    total_by_year = {}
    for r in rows[start + 1:]:
        if not r[0]:
            continue
        name = str(r[0]).strip()
        if name.startswith("1 Includes") or name.startswith("Notes"):
            break
        vals = r[1:1 + len(years)]
        if name == "Total":
            for y, v in zip(years, vals):
                if isinstance(v, (int, float)):
                    total_by_year[y] = int(v)
            continue
        if name in SKIP:
            continue
        for y, v in zip(years, vals):
            if isinstance(v, (int, float)):
                out[(name, y)] = out.get((name, y), 0) + int(v)
    return out, total_by_year


def main() -> None:
    old, _ = parse_table3(RAW / "us_lpr_fy2023.xlsx")
    new, totals = parse_table3(RAW / "us_lpr_fy2024.xlsx")
    merged = {}
    for (c, y), v in old.items():
        if y == 2014:
            merged[(c, y)] = v
    merged.update(new)
    # FY2014 total from the FY2023 book's Total row (parse separately)
    _, totals_old = parse_table3(RAW / "us_lpr_fy2023.xlsx")
    totals = {**totals_old, **totals}

    out_path = ROOT / "data" / "us_lpr_by_birth_country.csv"
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["country", "year", "persons", "total_all_countries",
                    "share"])
        for (c, y) in sorted(merged, key=lambda t: (t[1], t[0])):
            tot = totals.get(y)
            share = merged[(c, y)] / tot if tot else None
            w.writerow([c, y, merged[(c, y)], tot,
                        f"{share:.6f}" if share else ""])
    print(f"wrote {out_path} rows={len(merged)} "
          f"years={min(y for _, y in merged)}-{max(y for _, y in merged)}")
    for y in sorted(totals):
        print(f"  FY{y} total {totals[y]:,}")


if __name__ == "__main__":
    main()
