"""Fetch 12 NHL seasons of regular-season game results + final standings.

Source: NHL public API (api-web.nhle.com), no key required.
- Final standings per season: GET /v1/standings/{last regular-season date}
  (gives team -> division/conference mapping and official points for validation)
- Every game: GET /v1/club-schedule-season/{team}/{seasonId}, gameType==2,
  deduplicated by game id. gameOutcome.lastPeriodType is REG / OT / SO,
  which is what makes the loser-point accounting possible.

Seasons: 2013-14 .. 2024-25. 2019-20 was truncated by COVID (standings as of
the 2020-03-11 pause); 2020-21 used one-off realigned divisions. Both are
flagged in the output and excluded from the playoff-field simulation in
02_standings_lab.py, but kept for league-wide trend and OT-model work.
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://api-web.nhle.com/v1"
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# seasonId -> date of (effectively) the final regular-season standings snapshot
SEASONS = {
    20132014: "2014-04-13",
    20142015: "2015-04-11",
    20152016: "2016-04-10",
    20162017: "2017-04-09",
    20172018: "2018-04-08",
    20182019: "2019-04-06",
    20192020: "2020-03-11",   # COVID pause; regular season never resumed
    20202021: "2021-05-19",   # realigned one-off divisions
    20212022: "2022-05-01",
    20222023: "2023-04-14",
    20232024: "2024-04-18",
    20242025: "2025-04-17",
}


def get(url, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def season_label(sid):
    return f"{str(sid)[:4]}-{str(sid)[6:]}"


def main():
    standings_rows, games = [], {}
    for sid, final_date in SEASONS.items():
        st = get(f"{BASE}/standings/{final_date}")["standings"]
        teams = []
        for row in st:
            teams.append(row["teamAbbrev"]["default"])
            standings_rows.append({
                "season": sid, "season_label": season_label(sid),
                "team": row["teamAbbrev"]["default"],
                "division": row["divisionName"],
                # 2020-21's realigned divisions had no conferences
                "conference": row.get("conferenceName") or row["divisionName"],
                "official_points": row["points"],
                "official_wins": row["wins"],
                "official_losses": row["losses"],
                "official_ot_losses": row["otLosses"],
                "official_goal_diff": row["goalDifferential"],
            })
        (RAW / f"standings_{sid}.json").write_text(json.dumps(st))
        for team in teams:
            sched = get(f"{BASE}/club-schedule-season/{team}/{sid}")
            for g in sched["games"]:
                if g["gameType"] != 2 or g["gameState"] not in ("OFF", "FINAL"):
                    continue
                if g["id"] in games:
                    continue
                home, away = g["homeTeam"], g["awayTeam"]
                games[g["id"]] = {
                    "game_id": g["id"], "season": sid,
                    "season_label": season_label(sid),
                    "date": g["gameDate"],
                    "home": home["abbrev"], "away": away["abbrev"],
                    "home_goals": home["score"], "away_goals": away["score"],
                    "last_period": g["gameOutcome"]["lastPeriodType"],
                    "neutral_site": bool(g.get("neutralSite", False)),
                }
            time.sleep(0.05)
        n = sum(1 for g in games.values() if g["season"] == sid)
        print(f"{season_label(sid)}: {len(teams)} teams, {n} games")

    games_df = pd.DataFrame(games.values()).sort_values(["date", "game_id"])
    games_df["winner"] = games_df.apply(
        lambda r: r["home"] if r["home_goals"] > r["away_goals"] else r["away"], axis=1)
    games_df["loser"] = games_df.apply(
        lambda r: r["away"] if r["home_goals"] > r["away_goals"] else r["home"], axis=1)
    games_df["went_ot"] = (games_df["last_period"] != "REG").astype(int)
    games_df["went_so"] = (games_df["last_period"] == "SO").astype(int)
    games_df["home_win"] = (games_df["winner"] == games_df["home"]).astype(int)
    games_df.to_csv(ROOT / "data" / "games.csv", index=False)
    pd.DataFrame(standings_rows).to_csv(ROOT / "data" / "standings_final.csv", index=False)
    print(f"\nTotal games: {len(games_df)}")


if __name__ == "__main__":
    main()
