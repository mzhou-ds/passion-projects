"""Fetch Wikipedia pageviews for the remembrance-day articles.

Sources: Wikimedia Pageviews API (REST v1), no key required.
Articles: Remembrance Day, Veterans Day, Memorial Day, Anzac Day,
Remembrance poppy, Buddy poppy.
Windows:
  - daily, 2025-10-15 .. 2025-11-20 (the November spike)
  - daily, 2025-04-15 .. 2025-05-31 (Anzac Day + Memorial Day spikes)
  - monthly, 2025-01 .. 2025-12 (the year's attention shape)
Writes data/pageviews_daily_2025.csv and data/pageviews_monthly_2025.csv
(one row per article per date; user access only, desktop+mobile+app).
"""
import json
import time
from datetime import date

import requests

ARTICLES = [
    "Remembrance_Day",
    "Veterans_Day",
    "Memorial_Day",
    "Anzac_Day",
    "Remembrance_poppy",
    # "Buddy poppy" has no standalone article; it is a section of
    # "Remembrance poppy", so there is nothing separate to fetch.
]
HEADERS = {"User-Agent": "musing-with-mike-build/1.0 (research; contact: github.com/mzhou-ds)"}
BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user"


def fetch(article, start, end, granularity):
    url = f"{BASE}/{article}/{granularity}/{start}/{end}"
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return [
        {"article": article.replace("_", " "), "date": i["timestamp"][:8], "views": i["views"]}
        for i in r.json().get("items", [])
    ]


def main():
    rows = []
    for a in ARTICLES:
        rows += fetch(a, "20251015", "20251120", "daily")
        time.sleep(0.3)
    rows_apr = []
    for a in ["Anzac_Day", "Memorial_Day", "Remembrance_Day", "Veterans_Day"]:
        rows_apr += fetch(a, "20250415", "20250531", "daily")
        time.sleep(0.3)
    monthly = []
    for a in ARTICLES:
        monthly += fetch(a, "20250101", "20251201", "monthly")
        time.sleep(0.3)

    import csv, os

    os.makedirs("data", exist_ok=True)
    with open("data/pageviews_daily_2025.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["article", "date", "views"])
        w.writeheader()
        w.writerows(sorted(rows + rows_apr, key=lambda r: (r["article"], r["date"])))
    with open("data/pageviews_monthly_2025.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["article", "date", "views"])
        w.writeheader()
        w.writerows(sorted(monthly, key=lambda r: (r["article"], r["date"])))
    print(f"daily rows: {len(rows) + len(rows_apr)}, monthly rows: {len(monthly)}")


if __name__ == "__main__":
    main()
