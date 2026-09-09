"""Fetch career NHL regular-season totals for every drafted player (api-web.nhle.com).

Reads data/drafts.csv, calls /v1/player/{id}/landing for each unique playerId,
and caches the raw extracted fields in data/careers_cache.json so the run is
resumable. Writes data/careers.csv:
  playerId, name, position, gp, goals, assists, points

Throttled to ~2 requests/sec to be a polite API citizen.
Run: python3 src/02_fetch_careers.py   (run from the project root)
"""
import csv, json, os, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) passion-projects-draft-research"}
CACHE = "data/careers_cache.json"
OUT = "data/careers.csv"
WORKERS = 6  # parallel fetch threads; ~1s/req each -> ~6 req/s total

def fetch(pid):
    url = f"https://api-web.nhle.com/v1/player/{pid}/landing"
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30))
            break
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            if attempt == 2:
                return {"error": str(e)}
            time.sleep(2)
    rs = d.get("careerTotals", {}).get("regularSeason", {})
    return {
        "name": d.get("firstName", {}).get("default", "") + " " + d.get("lastName", {}).get("default", ""),
        "position": (d.get("position") or ""),
        "gp": int(rs.get("gamesPlayed", 0)),
        "goals": int(rs.get("goals", 0)),
        "assists": int(rs.get("assists", 0)),
        "points": int(rs.get("points", 0)),
    }

def main():
    with open("data/drafts.csv") as f:
        picks = list(csv.DictReader(f))
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    players = {p["playerId"]: (p["name"], p["position"]) for p in picks if p["playerId"]}
    todo = [pid for pid in players if pid not in cache]
    print(f"{len(players)} unique players, {len(todo)} to fetch ({len(cache)} cached)", flush=True)
    done = [0]
    def one(pid):
        r = fetch(pid)
        cache[pid] = r
        done[0] += 1
        if done[0] % 250 == 0:
            print(f"  {done[0]}/{len(todo)}", flush=True)
            json.dump(cache, open(CACHE, "w"))
        return r
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(one, todo))
    json.dump(cache, open(CACHE, "w"))
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["playerId", "name", "position", "gp", "goals", "assists", "points"])
        w.writeheader()
        for pid, (nm, pos) in players.items():
            c = cache.get(pid, {})
            if "error" in c:
                c = {}
            w.writerow({"playerId": pid, "name": c.get("name", nm), "position": c.get("position", pos),
                        "gp": c.get("gp", 0), "goals": c.get("goals", 0),
                        "assists": c.get("assists", 0), "points": c.get("points", 0)})
    print(f"wrote {OUT} ({len(players)} players)")

if __name__ == "__main__":
    main()
