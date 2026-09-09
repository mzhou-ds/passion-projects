"""Fetch every pick from the NHL drafts 2005-2018 (records.nhl.com API).

Output: data/drafts.csv with one row per pick:
  draftYear, overall, round, pickInRound, playerId, name, position, team, teamId, country

Run: python3 src/01_fetch_drafts.py   (run from the project root)
Source: https://records.nhl.com/site/api/draft  (public, no auth)
"""
import csv, json, time, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) passion-projects-draft-research"}
YEARS = range(2005, 2019)

def main():
    rows = []
    for y in YEARS:
        url = f"https://records.nhl.com/site/api/draft?cayenneExp=draftYear={y}"
        req = urllib.request.Request(url, headers=UA)
        picks = json.load(urllib.request.urlopen(req, timeout=30))["data"]
        for r in picks:
            rows.append({
                "draftYear": y,
                "overall": r["overallPickNumber"],
                "round": r["roundNumber"],
                "pickInRound": r["pickInRound"],
                "playerId": r.get("playerId"),
                "name": r.get("playerName"),
                "position": r.get("position"),
                "team": r.get("triCode"),
                "teamId": r.get("draftedByTeamId"),
                "country": r.get("countryCode"),
            })
        print(f"{y}: {len(picks)} picks", flush=True)
        time.sleep(1.0)
    with open("data/drafts.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} picks to data/drafts.csv")

if __name__ == "__main__":
    main()
