"""Fetch 2025-26 NHL regular-season shift charts + play-by-play.

Sources (both public, no key):
  - shifts: https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId=<id>
  - pbp:    https://api-web.nhle.com/v1/gamecenter/<id>/play-by-play
Games 2025020001..2025021312 (1,312 regular-season games).
Caches raw JSON under data/raw/ so the run is reproducible without re-hitting the API.
"""
import json, os, time, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW, exist_ok=True)

def get(url, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "musing-with-mike/1.0 (research)"})
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503):
                time.sleep(2 * (i + 1)); continue
            return None
        except requests.RequestException:
            time.sleep(2 * (i + 1))
    return None

def fetch_game(gid):
    out = {}
    sp = os.path.join(RAW, f"shifts_{gid}.json")
    pp = os.path.join(RAW, f"pbp_{gid}.json")
    if os.path.exists(sp):
        out["shifts"] = "cached"
    else:
        d = get(f"https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={gid}")
        if d is None:
            out["shifts"] = "FAILED"
        else:
            json.dump(d, open(sp, "w"))
            out["shifts"] = len(d.get("data", []))
    if os.path.exists(pp):
        out["pbp"] = "cached"
    else:
        d = get(f"https://api-web.nhle.com/v1/gamecenter/{gid}/play-by-play")
        if d is None:
            out["pbp"] = "FAILED"
        else:
            json.dump(d, open(pp, "w"))
            out["pbp"] = len(d.get("plays", []))
    return gid, out

if __name__ == "__main__":
    gids = list(range(2025020001, 2025021313))
    results = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(fetch_game, g): g for g in gids}
        done = 0
        for f in as_completed(futs):
            gid, r = f.result()
            results[gid] = r
            done += 1
            if done % 200 == 0:
                print(f"{done}/1312 games", flush=True)
    failed_shifts = [g for g, r in results.items() if r["shifts"] == "FAILED"]
    failed_pbp = [g for g, r in results.items() if r["pbp"] == "FAILED"]
    empty_shifts = []
    for g in gids:
        try:
            d = json.load(open(os.path.join(RAW, f"shifts_{g}.json")))
            if len(d.get("data", [])) < 100:
                empty_shifts.append(g)
        except Exception:
            pass
    print("failed shifts:", len(failed_shifts), failed_shifts[:10])
    print("failed pbp:", len(failed_pbp), failed_pbp[:10])
    print("games with <100 shift rows (empty/broken feed):", len(empty_shifts), empty_shifts[:10])
    json.dump({"failed_shifts": failed_shifts, "failed_pbp": failed_pbp,
               "empty_shifts": empty_shifts},
              open(os.path.join(RAW, "fetch_report.json"), "w"), indent=2)
