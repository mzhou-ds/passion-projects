#!/usr/bin/env python3
"""
Collect festival attendance figures from Wikipedia.

Fetches the raw wikitext of the Tomorrowland and Ultra Music Festival
Wikipedia pages via the MediaWiki API and parses their year-by-year
attendance tables.

Output: data/festival_attendance.csv
  columns: festival, year, attendance, notes

Sources:
  https://en.wikipedia.org/wiki/Tomorrowland_(festival)
  https://en.wikipedia.org/wiki/Ultra_Music_Festival
Retrieved 2026-09-08. Figures are as reported on Wikipedia (some marked
"citation needed" there); see README for caveats.
"""
import csv
import json
import re
from pathlib import Path

import requests

UA = "passion-projects-edm/1.0 (https://github.com/mzhou-ds/passion-projects; research project)"
API = "https://en.wikipedia.org/w/api.php"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def wikitext(page: str) -> str:
    r = requests.get(
        API,
        params={"action": "parse", "page": page, "prop": "wikitext", "format": "json"},
        headers={"User-Agent": UA},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["parse"]["wikitext"]["*"]


def clean(cell: str) -> str:
    cell = re.sub(r"<ref.*?(?:/>|</ref\s*>)", "", cell, flags=re.S)
    cell = re.sub(r"\{\{[^\}]*\}\}", "", cell)  # templates
    cell = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", cell)
    cell = re.sub(r"\[\[([^\]]*)\]\]", r"\1", cell)
    cell = re.sub(r"''+", "", cell)
    cell = re.sub(r"<[^>]+>", "", cell)
    return cell.strip()


def parse_number(s: str):
    s = s.replace(",", "").replace("~", "").strip()
    m = re.search(r"(\d[\d\s]*)", s)
    if not m:
        return None
    try:
        return int(m.group(1).replace(" ", ""))
    except ValueError:
        return None


def tomorrowland() -> list[dict]:
    wt = wikitext("Tomorrowland (festival)")
    # the editions table: header row has !Year !Dates !Attendance
    m = re.search(r"\{\|[^|]*?class=\"wikitable\".*?!\s*Year\s*\n!\s*Dates\s*\n!\s*Attendance(.*?)\n\|\}", wt, re.S)
    assert m, "Tomorrowland editions table not found"
    rows = []
    for chunk in m.group(1).split("|-")[1:]:
        cells = [clean(c) for c in chunk.strip().split("\n|")]
        cells = [c.lstrip("|").strip() for c in cells]
        if len(cells) < 3 or not re.match(r"^\d{4}", cells[0]):
            continue
        year = int(re.match(r"^(\d{4})", cells[0]).group(1))
        att = parse_number(cells[2])
        if att is None:
            continue
        rows.append({"festival": "Tomorrowland", "year": year, "attendance": att, "notes": cells[2][:80]})
    return rows


def ultra() -> list[dict]:
    wt = wikitext("Ultra Music Festival")
    i = wt.find("==Attendances==")
    seg = wt[i : i + 12000]
    m = re.search(r"\{\|.*?\n\|\}", seg, re.S)
    assert m, "Ultra attendance table not found"
    t = m.group(0)
    rows = []
    for chunk in t.split("|-")[1:]:
        m2 = re.search(
            r'\|\s*align="center"\s*\|\s*(\d{4}).*?\|\|\s*align="center"\s*\|\s*([^|<]+)',
            chunk,
            re.S,
        )
        if not m2:
            continue
        att = parse_number(clean(m2.group(2)))
        if att is None:
            continue
        rows.append(
            {"festival": "Ultra Music Festival", "year": int(m2.group(1)), "attendance": att, "notes": ""}
        )
    return rows


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rows = tomorrowland() + ultra()
    rows.sort(key=lambda r: (r["festival"], r["year"]))
    with open(DATA_DIR / "festival_attendance.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["festival", "year", "attendance", "notes"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows ->", DATA_DIR / "festival_attendance.csv")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
