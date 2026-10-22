#!/usr/bin/env python3
"""Fetch source data for 'The One-Country Mosaic'.

Sources (all official, no API keys):
  US  : OHSS (DHS) Yearbook of Immigration Statistics, Lawful Permanent
        Residents workbooks FY2023 (Table 3 = LPRs by country of birth,
        FY2014-2023) and FY2024 (FY2015-2024).
  CA  : IRCC Open Data, 'Permanent Residents - Monthly IRCC Updates':
        admissions by country of citizenship (monthly, 2015-present),
        and 'Temporary Residents: Study Permit Holders - Monthly IRCC
        Updates': study permit holders by country of citizenship.

Raw files land in data/raw/ untouched. This script only downloads.
"""
import pathlib
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

FILES = {
    "us_lpr_fy2023.xlsx": (
        "https://ohss.dhs.gov/sites/default/files/2024-09/"
        "2024_0906_ohss_yearbook_lawful_permanent_residents_fy2023_0.xlsx"
    ),
    "us_lpr_fy2024.xlsx": (
        "https://ohss.dhs.gov/system/files/2026-06/"
        "2026_0604_ohss_yearbook_lawful_permanent_residents_fy2024.xlsx"
    ),
    # IRCC canonical files (Open Government Portal datasets 'Permanent
    # Residents - Monthly IRCC Updates' and 'Temporary Residents: Study
    # Permit Holders - Monthly IRCC Updates'). Live host first; the
    # Wayback Machine snapshot of the same IRCC file (2025-08-03) is
    # the fallback — that is how the copies in data/raw were obtained
    # on 2026-10-22, when ircc.canada.ca was unreachable (gateway
    # timeouts). Snapshot data runs through Mar 2025 (PR) / Dec 2024
    # (study year-end stocks).
    "ca_pr_citizenship.xlsx": (
        "https://www.ircc.canada.ca/opendata-donneesouvertes/data/"
        "EN_ODP-PR-Citz.xlsx",
        "https://web.archive.org/web/20250803100234/"
        "https://www.ircc.canada.ca/opendata-donneesouvertes/data/"
        "EN_ODP-PR-Citz.xlsx",
    ),
    "ca_study_citizenship.xlsx": (
        "https://www.ircc.canada.ca/opendata-donneesouvertes/data/"
        "EN_ODP_annual-TR-Study-IS_CITZ_year_end.xlsx",
        "https://web.archive.org/web/20250803095814/"
        "https://www.ircc.canada.ca/opendata-donneesouvertes/data/"
        "EN_ODP_annual-TR-Study-IS_CITZ_year_end.xlsx",
    ),
}

def main() -> None:
    for name, url in FILES.items():
        dest = RAW / name
        if dest.exists() and dest.stat().st_size > 10_000:
            print(f"skip (present) {name} {dest.stat().st_size} bytes")
            continue
        urls = url if isinstance(url, tuple) else (url,)
        last_err = None
        for u in urls:
            try:
                print(f"GET {u}")
                r = requests.get(u, timeout=120,
                                 headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                dest.write_bytes(r.content)
                print(f"  -> {name} {len(r.content)} bytes")
                last_err = None
                break
            except Exception as e:  # try the archived copy next
                print(f"  failed: {e}")
                last_err = e
        if last_err is not None:
            raise last_err

if __name__ == "__main__":
    main()
