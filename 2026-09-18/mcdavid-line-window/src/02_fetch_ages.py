"""Part 2a: fetch birthdates for the skater pool via the NHL API (playerId = NHL id).

Polite: fresh connection per request, ~3 req/s, resumable output.
"""
import json, time, urllib.request
import pandas as pd

pool = pd.read_csv("data/processed/skater_pool.csv")
OUT = "data/processed/skater_birthdates.csv"

try:
    done = pd.read_csv(OUT)
    have = set(done["playerId"])
except FileNotFoundError:
    done, have = pd.DataFrame(columns=["playerId", "birthDate"]), set()

todo = [p for p in pool["playerId"].unique() if p not in have]
print(f"pool={len(pool)} have={len(have)} todo={len(todo)}")

def fetch(pid):
    req = urllib.request.Request(
        f"https://api-web.nhle.com/v1/player/{int(pid)}/landing",
        headers={"User-Agent": "Mozilla/5.0 (research project)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r).get("birthDate")

rows = done.to_dict("records")
for i, pid in enumerate(todo):
    try:
        bd = fetch(pid)
        rows.append({"playerId": pid, "birthDate": bd})
    except Exception as e:
        print("fail", pid, type(e).__name__)
    if (i + 1) % 100 == 0:
        pd.DataFrame(rows).to_csv(OUT, index=False)
        print(f"  {i+1}/{len(todo)}")
    time.sleep(0.35)

pd.DataFrame(rows).to_csv(OUT, index=False)
print("wrote", OUT, len(rows))
