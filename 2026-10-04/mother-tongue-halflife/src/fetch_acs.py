#!/usr/bin/env python3
"""US side: ACS 2023 5-year table-based summary files (www2.census.gov) —
the Census API now requires a key and Census Reporter 403s from here, so we
parse the public .dat extracts. B16001 (language) publishes sub-metro rows
only, so it is aggregated up to CBSA by GEO_ID prefix; B01003/B05006 carry
direct CBSA (summary-level 310) rows. Coverage note: B16001 has no rows for
Houston, San Diego, Sacramento, Las Vegas, or Honolulu — those metros are
excluded rather than estimated. Raw .dat files (~286 MB) are NOT committed;
downloads:
  https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/acsdt5y2023-{b01003,b16001,b05006}.dat
"""
import csv, json
from collections import defaultdict
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
RAW = Path("/tmp/acs2023")
OUT = PROJ / "data" / "acs_chinese_language.json"
NAMES = {"35620": "New York", "31080": "Los Angeles", "41860": "San Francisco-Oakland",
         "14460": "Boston", "42660": "Seattle", "16980": "Chicago", "47900": "Washington DC",
         "37980": "Philadelphia", "19100": "Dallas-Fort Worth", "12060": "Atlanta",
         "33100": "Miami", "19820": "Detroit", "45300": "Tampa"}

out = {"United States": {}}
with open(RAW / "b16001.dat", newline="") as f:
    agg = defaultdict(lambda: {"chinese": 0, "chinese_verywell": 0, "chinese_less": 0, "lang_all_5plus": 0})
    for r in csv.DictReader(f, delimiter="|"):
        g = r["GEO_ID"]
        if g == "0100000US":
            out["United States"].update({"chinese": int(r["B16001_E075"]), "chinese_verywell": int(r["B16001_E076"]),
                                         "chinese_less": int(r["B16001_E077"]), "lang_all_5plus": int(r["B16001_E001"])})
        elif g.startswith(("310", "311", "312", "314")) and g.split("US", 1)[1][:5] in NAMES:
            a = agg[g.split("US", 1)[1][:5]]
            a["chinese"] += int(r["B16001_E075"]); a["chinese_verywell"] += int(r["B16001_E076"])
            a["chinese_less"] += int(r["B16001_E077"]); a["lang_all_5plus"] += int(r["B16001_E001"])
    for code, vals in agg.items():
        out[NAMES[code]] = vals
for table, cols in {"b01003": {"pop": "B01003_E001"},
                    "b05006": {"born_china": "B05006_E050", "born_hk": "B05006_E051", "born_tw": "B05006_E052"}}.items():
    with open(RAW / f"{table}.dat", newline="") as f:
        for r in csv.DictReader(f, delimiter="|"):
            g = r["GEO_ID"]
            name = "United States" if g == "0100000US" else (
                NAMES.get(g.split("US", 1)[1][:5]) if g.startswith("310M7") else None)
            if name and name in out:
                out[name].update({k: int(r[v]) for k, v in cols.items()})
OUT.write_text(json.dumps({"2023": out}, indent=1))
print("geos:", len(out))
for n, v in out.items():
    print(n, v.get("chinese"), v.get("born_china"))
