"""Fetch Hacker News front-page stories (top 500) + monthly AI-discourse time series.

Part 2 of tech-pulse-2026. Uses the public Firebase HN API (no auth) and the
free Algolia HN search API. Saves raw JSON snapshots under ../data/.
"""
import json, time, datetime as dt
import requests

DATA = "/home/hatch/workspace/passion-projects/2026-09-14/tech-pulse-2026/data"
HN = "https://hacker-news.firebaseio.com/v0"

def get(url, params=None, timeout=20):
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=timeout)  # fresh connection per call
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print("retry", url, e)
            time.sleep(2)
    return None

# --- 1. Current front page: topstories (up to 500 ids) ---
ids = get(f"{HN}/topstories.json") or []
print("topstories ids:", len(ids))
ids = ids[:500]

stories = []
for i, sid in enumerate(ids):
    item = get(f"{HN}/item/{sid}.json")
    if item and item.get("type") == "story":
        stories.append({k: item.get(k) for k in
                        ("id", "title", "url", "score", "descendants", "time", "by", "type")})
    if (i + 1) % 100 == 0:
        print(f"  fetched {i+1}/{len(ids)}")
    time.sleep(0.05)

with open(f"{DATA}/hn_top500.json", "w") as f:
    json.dump({"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(), "stories": stories}, f)
print("saved hn_top500.json with", len(stories), "stories")

# --- 2. Monthly AI-discourse share via Algolia HN search (2021-01 .. 2026-08) ---
ALG = "http://hn.algolia.com/api/v1/search"
months = []
y, m = 2021, 1
while (y, m) <= (2026, 8):
    months.append((y, m))
    m += 1
    if m == 13:
        m, y = 1, y + 1

rows = []
for (y, m) in months:
    lo = dt.datetime(y, m, 1, tzinfo=dt.timezone.utc).timestamp()
    hi = (dt.datetime(y + (m == 12), (m % 12) + 1, 1, tzinfo=dt.timezone.utc)).timestamp()
    nf = f"created_at_i>{int(lo)},created_at_i<{int(hi)}"
    total = get(ALG, {"tags": "story", "numericFilters": nf, "hitsPerPage": 0}) or {}
    ai = get(ALG, {"query": "AI OR LLM OR GPT OR Claude OR ChatGPT OR \"machine learning\" OR diffusion",
                   "tags": "story", "numericFilters": nf, "hitsPerPage": 0}) or {}
    rows.append({"year": y, "month": m,
                 "stories_total": total.get("nbHits", 0),
                 "stories_ai": ai.get("nbHits", 0)})
    print(y, m, total.get("nbHits"), ai.get("nbHits"))
    time.sleep(0.4)

with open(f"{DATA}/hn_ai_monthly.json", "w") as f:
    json.dump(rows, f)
print("saved hn_ai_monthly.json")
