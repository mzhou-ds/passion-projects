"""01b_series.py — reconstruct playoff series winners from the NHL schedule API.

Resumable: per-season game lists are cached to
data/processed/series_games_cache_{season}.csv so a rerun never refetches.

Output: data/processed/playoff_series.csv (2019-20 bubble excluded)
"""
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

# 2019 (2019-20 season) excluded: the Aug-Oct 2020 bubble had play-in series
# and round-robin games — a non-standard format. All other seasons are
# best-of-7 throughout.
SEASONS = [s for s in range(2015, 2026) if s != 2019]
# NOTE: no requests.Session here — keep-alive connections hang through the
# egress proxy (same lesson as AGENTS.md/MusicBrainz). Fresh get per call.
UA = {"User-Agent": "musing-with-mike research (non-commercial)"}


def get(url, retries=3):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, timeout=20, headers=UA)
            r.raise_for_status()
            time.sleep(0.3)
            return r
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last


def fetch_week(args):
    s, d = args
    r = get(f"https://api-web.nhle.com/v1/schedule/{d.isoformat()}").json()
    games, seen = [], set()
    for day in r.get("gameWeek", []):
        for gm in day.get("games", []):
            if gm.get("gameType") == 3 and gm.get("season") == int(f"{s}{s+1}"):
                h, a = gm["homeTeam"], gm["awayTeam"]
                if "score" in h and "score" in a and gm["id"] not in seen:
                    seen.add(gm["id"])
                    games.append(dict(gid=gm["id"], ha=h["abbrev"], aa=a["abbrev"],
                                      hs=h["score"], aw=a["score"]))
    return games


def fetch_season_games(s):
    cache = PROC / f"series_games_cache_{s}.csv"
    if cache.exists():
        df = pd.read_csv(cache)
        return df.drop(columns=[c for c in ["gid"] if c in df.columns])
    start, end = date(s + 1, 4, 1), date(s + 1, 7, 15)
    weeks = []
    d = start
    while d <= end:
        weeks.append(d)
        d += timedelta(days=7)
    games, failed = [], []
    for w in weeks:
        try:
            games.extend(fetch_week((s, w)))
        except Exception as e:
            failed.append(w)
            print(f"  week {w} failed ({type(e).__name__}), will retry", flush=True)
    for w in failed:  # one retry pass for failed weeks
        time.sleep(3)
        try:
            games.extend(fetch_week((s, w)))
        except Exception as e:
            raise RuntimeError(f"season {s} week {w} failed twice: {e}")
    df = pd.DataFrame(games)
    if df.empty:
        raise RuntimeError(f"season {s}: no playoff games found")
    df = df.drop_duplicates(subset="gid").drop(columns="gid")
    assert 60 <= len(df) <= 120, f"season {s}: implausible game count {len(df)}"
    df.to_csv(cache, index=False)
    return df


def main():
    rows = []
    for s in SEASONS:
        df = fetch_season_games(s)
        df["pair"] = df.apply(lambda r: tuple(sorted([r["ha"], r["aa"]])), axis=1)
        for pair, gdf in df.groupby("pair"):
            w1 = (((gdf["ha"] == pair[0]) & (gdf["hs"] > gdf["aw"])) |
                  ((gdf["aa"] == pair[0]) & (gdf["aw"] > gdf["hs"]))).sum()
            w2 = len(gdf) - w1
            # sanity: a real series ends 4-x (best of 7)
            assert max(w1, w2) == 4 and len(gdf) <= 7, \
                f"odd series {s} {pair}: {w1}-{w2}"
            rows.append(dict(season=s, team1=pair[0], team2=pair[1],
                             winner=pair[0] if w1 > w2 else pair[1],
                             games=len(gdf)))
        print(f"season {s}: {df['pair'].nunique()} series, {len(df)} games", flush=True)

    ser = pd.DataFrame(rows)
    team = pd.read_csv(PROC / "team_season.csv").set_index(["season", "team"])
    for i in (1, 2):
        ser = ser.join(
            team[["team_GSAx", "xGFpct"]].rename(
                columns={"team_GSAx": f"gsax{i}", "xGFpct": f"xgfpct{i}"}),
            on=["season", f"team{i}"])
    assert ser[[f"gsax{i}" for i in (1, 2)]].notna().all().all()
    ser["winner_gsax"] = ser.apply(
        lambda r: r["gsax1"] if r["winner"] == r["team1"] else r["gsax2"], axis=1)
    ser["loser_gsax"] = ser.apply(
        lambda r: r["gsax2"] if r["winner"] == r["team1"] else r["gsax1"], axis=1)
    ser["better_goalie_won"] = ser["winner_gsax"] > ser["loser_gsax"]
    ser["winner_xgf"] = ser.apply(
        lambda r: r["xgfpct1"] if r["winner"] == r["team1"] else r["xgfpct2"], axis=1)
    ser["loser_xgf"] = ser.apply(
        lambda r: r["xgfpct2"] if r["winner"] == r["team1"] else r["xgfpct1"], axis=1)
    ser["better_skaters_won"] = ser["winner_xgf"] > ser["loser_xgf"]
    ser.to_csv(PROC / "playoff_series.csv", index=False)
    print(f"playoff_series: {len(ser)} rows")

    # playoff team GSAx per season (for the "hot goalie" check)
    frames = []
    for s in SEASONS:
        df = pd.read_csv(RAW / f"mp_{s}_playoffs_goalies.csv")
        df = df[df["situation"] == "all"].copy()
        df["season"] = s
        frames.append(df)
    po = pd.concat(frames, ignore_index=True)
    po["team"] = po["team"].replace({"L.A": "LAK", "N.J": "NJD",
                                     "S.J": "SJS", "T.B": "TBL"})
    po["GSAx"] = po["flurryAdjustedxGoals"] - po["goals"]
    pg = (po.groupby(["season", "team"], as_index=False)
            .agg(po_GSAx=("GSAx", "sum"), po_gp=("games_played", "sum")))
    pg.to_csv(PROC / "playoff_team_gsax.csv", index=False)
    print(f"playoff_team_gsax: {len(pg)} rows")
    print("done")


if __name__ == "__main__":
    main()
