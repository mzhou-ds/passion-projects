"""Fetch MoneyPuck shot data, 2019-20 through 2024-25 seasons.

Source: MoneyPuck public shot files (https://moneypuck.com/data.htm),
hosted at peter-tanner.com/moneypuck/downloads/shots_<start-year>.zip
where shots_2019.zip is the 2019-20 season. Each file is one row per
shot attempt with score state, clock, shooter, xGoal and game result.

Downloads are cached under data/raw/ (gitignored); re-runs are free.
Only the columns the analysis needs are kept, saved as one parquet.
"""
import io
import os
import zipfile

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
OUT = os.path.join(HERE, "..", "data", "shots_slim.parquet")
SEASONS = [2019, 2020, 2021, 2022, 2023, 2024]  # start year of season

COLS = [
    "season", "game_id", "isPlayoffGame", "time", "period", "event", "goal",
    "shooterPlayerId", "shooterName", "isHomeTeam", "homeTeamCode",
    "awayTeamCode", "homeTeamGoals", "awayTeamGoals", "homeTeamWon",
    "xGoal", "playerPositionThatDidEvent", "teamCode", "homeEmptyNet",
    "awayEmptyNet",
]


def fetch_season(year: int) -> pd.DataFrame:
    os.makedirs(RAW, exist_ok=True)
    zpath = os.path.join(RAW, f"shots_{year}.zip")
    if not os.path.exists(zpath):
        url = f"https://peter-tanner.com/moneypuck/downloads/shots_{year}.zip"
        print(f"downloading {url}")
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        with open(zpath, "wb") as f:
            f.write(r.content)
    with zipfile.ZipFile(zpath) as z:
        name = z.namelist()[0]
        with z.open(name) as fh:
            df = pd.read_csv(fh, usecols=lambda c: c in COLS, low_memory=False)
    # 2024-25 file also carries MoneyPuck's own pre-shot home win
    # probability; keep it in the raw cache for the validation in 02.
    return df


def fetch_season_wp(year: int = 2024) -> pd.DataFrame:
    zpath = os.path.join(RAW, f"shots_{year}.zip")
    with zipfile.ZipFile(zpath) as z:
        name = z.namelist()[0]
        with z.open(name) as fh:
            df = pd.read_csv(
                fh,
                usecols=lambda c: c in COLS + ["homeWinProbability"],
                low_memory=False,
            )
    return df


def main() -> None:
    frames = []
    for y in SEASONS:
        d = fetch_season(y)
        print(y, len(d), "shot rows")
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df.to_parquet(OUT)
    print("wrote", OUT, len(df), "rows")


if __name__ == "__main__":
    main()
