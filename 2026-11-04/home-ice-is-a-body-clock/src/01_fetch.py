"""Fetch every NHL regular-season and playoff game, 2023-24 through 2026-27
to date, from the public NHL API (api-web.nhle.com, no key required).

The club-schedule-season endpoint returns one team's full schedule. Each
game appears once per participating team, so games are deduplicated by
game id. Only FINAL games are kept (future fixtures are dropped).

Output: data/games_raw.csv — one row per game, with the fields the
feature builder needs. Raw per-team JSON is NOT committed (it would be
~25MB); this script regenerates games_raw.csv from scratch in ~2 minutes.
"""

import csv
import json
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "data" / "games_raw.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

TEAMS = ["ANA", "BOS", "BUF", "CAR", "CBJ", "CGY", "CHI", "COL", "DAL",
         "DET", "EDM", "FLA", "LAK", "MIN", "MTL", "NJD", "NSH", "NYI",
         "NYR", "OTT", "PHI", "PIT", "SEA", "SJS", "STL", "TBL", "TOR",
         "UTA", "VAN", "VGK", "WPG", "WSH", "ARI"]  # ARI = Coyotes, 2023-24 only
SEASONS = [20232024, 20242025, 20252026, 20262027]

# Arena coordinates (lat, lon) for travel-distance features.
ARENAS = {
    "ANA": (33.807, -117.876), "BOS": (42.366, -71.062), "BUF": (42.875, -78.876),
    "CAR": (35.803, -78.722), "CBJ": (39.969, -83.006), "CGY": (51.037, -114.001),
    "CHI": (41.881, -87.674), "COL": (39.901, -105.065), "DAL": (32.790, -96.810),
    "DET": (42.341, -83.055), "EDM": (53.546, -113.074), "FLA": (26.159, -80.178),
    "LAK": (34.043, -118.267), "MIN": (44.944, -93.101), "MTL": (45.496, -73.569),
    "NJD": (40.733, -74.171), "NSH": (36.159, -86.778), "NYI": (40.722, -73.723),
    "NYR": (40.751, -73.990), "OTT": (45.296, -75.927), "PHI": (39.901, -75.172),
    "PIT": (40.443, -79.989), "SEA": (47.622, -122.354), "SJS": (37.133, -121.901),
    "STL": (38.626, -90.202), "TBL": (27.942, -82.451), "TOR": (43.643, -79.379),
    "UTA": (40.768, -111.901), "VAN": (49.278, -123.108), "VGK": (36.102, -115.178),
    "WPG": (49.892, -97.143), "WSH": (38.897, -77.020), "ARI": (33.531, -112.261),
}


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "musing-with-mike/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    games = {}
    for season in SEASONS:
        for team in TEAMS:
            url = f"https://api-web.nhle.com/v1/club-schedule-season/{team}/{season}"
            try:
                data = fetch_json(url)
            except Exception as exc:  # team did not exist that season, etc.
                print(f"skip {team} {season}: {exc}")
                continue
            for g in data.get("games", []):
                # Completed games are "OFF" (regular/playoff) or "FINAL"
                # (preseason quirk); future fixtures are "FUT"/"PRE".
                if g.get("gameState") not in ("OFF", "FINAL"):
                    continue
                if g["homeTeam"].get("score") is None:
                    continue
                gid = g["id"]
                if gid in games:
                    continue
                home = g["homeTeam"]["abbrev"]
                away = g["awayTeam"]["abbrev"]
                games[gid] = {
                    "game_id": gid,
                    "season": season,
                    "game_type": g["gameType"],  # 1 preseason, 2 regular, 3 playoff
                    "date": g["gameDate"],
                    "home": home,
                    "away": away,
                    "home_score": g["homeTeam"].get("score"),
                    "away_score": g["awayTeam"].get("score"),
                    "neutral_site": int(bool(g.get("neutralSite"))),
                    # Venue UTC offset, e.g. "-07:00" -> -7.0. Used for timezone shifts.
                    "venue_utc_offset": g.get("venueUTCOffset", ""),
                }
            time.sleep(0.05)
        print(f"season {season} done, {len(games)} unique games so far")

    rows = sorted(games.values(), key=lambda r: (r["season"], r["date"], r["game_id"]))
    with open(OUT, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} games to {OUT}")


if __name__ == "__main__":
    main()
