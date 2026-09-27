"""01_prepare.py — build analysis-ready panels.

Inputs : data/raw/mp_*_goalies.csv, mp_*_playoffs_goalies.csv, mp_*_teams.csv
         (MoneyPuck season summaries), NHL API (schedule + team summary stats)
Outputs: data/processed/goalie_season.csv   — one row per goalie-season
         data/processed/team_season.csv     — team GSAx, xGF%, points, goal diff
         data/processed/playoff_series.csv — every playoff series 2015-2025
                                             (2020 bubble excluded), winner,
                                             each team's regular-season GSAx
                                             and xGF%

Conventions
  * MoneyPuck labels seasons by starting year: 2025 == 2025-26 season.
  * GSAx = flurryAdjustedxGoals - goals  (MoneyPuck's preferred xGA for goalies,
    situation='all').
  * icetime in the goalie files is in seconds.
"""
import json
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

SEASONS = list(range(2015, 2026))
# NOTE: no requests.Session — keep-alive connections hang through the egress
# proxy (see AGENTS.md). Fresh requests.get per call.
UA = {"User-Agent": "musing-with-mike research (non-commercial)"}


def get(url, retries=6, **kw):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, timeout=30, headers=UA, **kw)
            r.raise_for_status()
            time.sleep(0.25)
            return r
        except Exception as e:  # transient proxy hiccups — back off and retry
            last = e
            time.sleep(2 ** i + 1)
    raise last


# ---------------------------------------------------------------- goalies
def load_goalies(kind="regular"):
    frames = []
    for s in SEASONS:
        fn = f"mp_{s}_{'playoffs_' if kind == 'playoffs' else ''}goalies.csv"
        df = pd.read_csv(RAW / fn)
        df = df[df["situation"] == "all"].copy()
        df["season"] = s
        frames.append(df)
    g = pd.concat(frames, ignore_index=True)
    # sanity: no TOT rows that would double-count
    assert not (g["team"] == "TOT").any(), "TOT rows present — aggregation would double count"
    g["GSAx"] = g["flurryAdjustedxGoals"] - g["goals"]
    g["GSAx_raw"] = g["xGoals"] - g["goals"]
    g["minutes"] = g["icetime"] / 60.0
    g["GSAx60"] = g["GSAx"] / g["icetime"] * 3600.0
    g["svpct"] = 1 - g["goals"] / g["ongoal"].replace(0, np.nan)
    g["team"] = g["team"].replace({"L.A": "LAK", "N.J": "NJD",
                                   "S.J": "SJS", "T.B": "TBL"})
    return g


def main():
    reg = load_goalies("regular")
    po = load_goalies("playoffs")

    # goalie-season panel (aggregate multi-team goalies across teams)
    gs = (
        reg.groupby(["season", "playerId"], as_index=False)
        .agg(
            name=("name", "first"),
            teams=("team", lambda x: "+".join(sorted(set(x)))),
            gp=("games_played", "sum"),
            minutes=("minutes", "sum"),
            GSAx=("GSAx", "sum"),
            GSAx_raw=("GSAx_raw", "sum"),
            shots=("ongoal", "sum"),
            goals=("goals", "sum"),
        )
    )
    gs["GSAx60"] = gs["GSAx"] / (gs["minutes"] * 60) * 60  # per 60 min
    gs["GSAx60"] = gs["GSAx"] / gs["minutes"] * 60
    gs["svpct"] = 1 - gs["goals"] / gs["shots"].replace(0, np.nan)
    gs.to_csv(PROC / "goalie_season.csv", index=False)
    print(f"goalie_season: {len(gs)} rows")

    # team-season panel: team GSAx + xGF% from MoneyPuck
    team_frames = []
    for s in SEASONS:
        t = pd.read_csv(RAW / f"mp_{s}_teams.csv")
        t = t[t["situation"] == "all"].copy()
        t["season"] = s
        # pre-2021 files use dotted abbreviations (L.A, N.J, S.J, T.B)
        t["team"] = t["team"].replace({"L.A": "LAK", "N.J": "NJD",
                                       "S.J": "SJS", "T.B": "TBL"})
        team_frames.append(t[["season", "team", "xGoalsPercentage"]])
    tm = pd.concat(team_frames, ignore_index=True)

    tg = (
        reg.groupby(["season", "team"], as_index=False)
        .agg(team_GSAx=("GSAx", "sum"), team_minutes=("minutes", "sum"))
    )
    team = tm.merge(tg, on=["season", "team"], how="left")
    team = team.rename(columns={"xGoalsPercentage": "xGFpct"})

    # team points / goal differential from NHL stats API (regular season)
    pts_cache = PROC / "team_points_cache.csv"
    if pts_cache.exists():
        pts = pd.read_csv(pts_cache)
        print("team points: loaded from cache")
    else:
        rows = []
        for s in SEASONS:
            season_id = f"{s}{s+1}"
            url = (
                "https://api.nhle.com/stats/rest/en/team/summary?isAggregate=false"
                f"&isGame=false&start=0&limit=100&cayenneExp=seasonId%3D{season_id}%20and%20gameTypeId%3D2"
            )
            d = get(url).json()
            for r in d["data"]:
                rows.append(
                    dict(
                        season=s,
                        team_name=r["teamFullName"],
                        points=r["points"],
                        GF=r["goalsFor"],
                        GA=r["goalsAgainst"],
                        gp=r["gamesPlayed"],
                    )
                )
        pts = pd.DataFrame(rows)
        pts.to_csv(pts_cache, index=False)

    # map NHL full names -> MoneyPuck abbreviations
    name_to_abbrev = {
        "Anaheim Ducks": "ANA", "Arizona Coyotes": "ARI", "Boston Bruins": "BOS",
        "Buffalo Sabres": "BUF", "Calgary Flames": "CGY", "Carolina Hurricanes": "CAR",
        "Chicago Blackhawks": "CHI", "Colorado Avalanche": "COL", "Columbus Blue Jackets": "CBJ",
        "Dallas Stars": "DAL", "Detroit Red Wings": "DET", "Edmonton Oilers": "EDM",
        "Florida Panthers": "FLA", "Los Angeles Kings": "LAK", "Minnesota Wild": "MIN",
        "Montréal Canadiens": "MTL", "Nashville Predators": "NSH", "New Jersey Devils": "NJD",
        "New York Islanders": "NYI", "New York Rangers": "NYR", "Ottawa Senators": "OTT",
        "Philadelphia Flyers": "PHI", "Pittsburgh Penguins": "PIT", "San Jose Sharks": "SJS",
        "Seattle Kraken": "SEA", "St. Louis Blues": "STL", "Tampa Bay Lightning": "TBL",
        "Toronto Maple Leafs": "TOR", "Utah Hockey Club": "UTA", "Utah Mammoth": "UTA",
        "Vancouver Canucks": "VAN", "Vegas Golden Knights": "VGK", "Washington Capitals": "WSH",
        "Winnipeg Jets": "WPG",
    }
    pts["team"] = pts["team_name"].map(name_to_abbrev)
    missing = pts[pts["team"].isna()]["team_name"].unique()
    assert len(missing) == 0, f"unmapped teams: {missing}"
    pts["goal_diff"] = pts["GF"] - pts["GA"]
    team = team.merge(pts[["season", "team", "points", "GF", "GA", "goal_diff"]],
                      on=["season", "team"], how="left")
    assert team["points"].notna().all()
    team.to_csv(PROC / "team_season.csv", index=False)
    print(f"team_season: {len(team)} rows")
    print("done  (playoff series built separately by 01b_series.py)")


if __name__ == "__main__":
    main()
