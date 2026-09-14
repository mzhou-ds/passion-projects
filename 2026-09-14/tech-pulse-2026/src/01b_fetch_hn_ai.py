"""Fetch monthly HN story counts for AI-related keywords (2021-01..2026-08).

Uses one simple query per keyword per month (Algolia's free search API does not
support OR across quoted phrases, so each keyword is queried separately and
series are reported independently). Saves data/hn_ai_monthly.json.
"""
import json, time, datetime as dt
import requests

DATA = "/home/hatch/workspace/passion-projects/2026-09-14/tech-pulse-2026/data"
KEYWORDS = ["AI", "LLM", "ChatGPT", "machine learning"]

def get(url, params, timeout=20):
    for _ in range(3):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except Exception:
            time.sleep(2)
    return {}

months, y, m = [], 2021, 1
while (y, m) <= (2026, 8):
    months.append((y, m))
    m += 1
    if m == 13:
        m, y = 1, y + 1

rows = []
for (y, m) in months:
    lo = int(dt.datetime(y, m, 1, tzinfo=dt.timezone.utc).timestamp())
    hi = int(dt.datetime(y + (m == 12), (m % 12) + 1, 1, tzinfo=dt.timezone.utc).timestamp())
    nf = f"created_at_i>{lo},created_at_i<{hi}"
    row = {"year": y, "month": m}
    tot = get("https://hn.algolia.com/api/v1/search",
              {"tags": "story", "numericFilters": nf, "hitsPerPage": 0})
    row["stories_total"] = tot.get("nbHits", 0)
    for kw in KEYWORDS:
        r = get("https://hn.algolia.com/api/v1/search",
                {"query": kw, "tags": "story", "numericFilters": nf, "hitsPerPage": 0})
        row[f"kw_{kw.replace(' ', '_')}"] = r.get("nbHits", 0)
        time.sleep(0.25)
    rows.append(row)
    print(y, m, row["stories_total"], {k: row[k] for k in row if k.startswith("kw_")})
    time.sleep(0.25)

with open(f"{DATA}/hn_ai_monthly.json", "w") as f:
    json.dump(rows, f)
print("saved", len(rows), "months")
