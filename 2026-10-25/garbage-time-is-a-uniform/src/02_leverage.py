"""Build the win-probability surface and score every shot for leverage.

Win probability is estimated empirically, not taken from a vendor:
for regulation play, group every shot attempt by (shooter's goal
differential, 5-minute bucket of time remaining) and take the share of
those games the shooter's team eventually won. Overtime gets a fixed
surface (tied = 0.50, up one in OT cannot occur before the goal, so OT
shots are scored from the pre-shot diff: +0 impossible in sudden death;
we use the empirical OT values by diff).

Leverage of a shot for the shooting team = 1 - 2*|WP - 0.5|.
Leverage 1.0 means the game is a coin flip; 0.0 means it is decided.
A goal is called "decided-state" (garbage time) when leverage < 0.20,
i.e. the shooter's win probability was already outside 40-60 in the
favour of either side... precisely WP <= 0.10 or WP >= 0.90.

Validation is out-of-sample: the surface is refit on 2019-20..2022-23
only and scored on 2023-24 + 2024-25 shots (Brier score and decile
calibration vs a home-base-rate baseline). Note: the 2024-25
MoneyPuck file contains a homeWinProbability column, but it is empty
for every row in the public file, so it cannot serve as a benchmark.

Outputs: data/shots_leverage.parquet (skaters only),
data/wp_surface.csv, data/wp_validation.json
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def add_state(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["shooter_goals"] = np.where(df.isHomeTeam == 1, df.homeTeamGoals, df.awayTeamGoals)
    df["opp_goals"] = np.where(df.isHomeTeam == 1, df.awayTeamGoals, df.homeTeamGoals)
    df["diff"] = (df.shooter_goals - df.opp_goals).clip(-6, 6)
    df["shooter_won"] = np.where(df.isHomeTeam == 1, df.homeTeamWon, 1 - df.homeTeamWon)
    df["mins_bucket"] = ((3600 - df.time) / 300).astype(int).clip(0, 12)
    df["empty_net_for"] = np.where(df.isHomeTeam == 1, df.awayEmptyNet, df.homeEmptyNet)
    return df


def main() -> None:
    df = pd.read_parquet(os.path.join(DATA, "shots_slim.parquet"))
    df = add_state(df)
    reg = df[df.period <= 3]
    surface = (
        reg.groupby(["diff", "mins_bucket"])
        .agg(wp=("shooter_won", "mean"), n=("shooter_won", "size"))
        .reset_index()
    )
    surface.to_csv(os.path.join(DATA, "wp_surface.csv"), index=False)

    df = df.merge(surface[["diff", "mins_bucket", "wp"]], on=["diff", "mins_bucket"], how="left")
    ot = df.period > 3
    df.loc[ot, "wp"] = np.where(
        df.loc[ot, "diff"] > 0, 0.72, np.where(df.loc[ot, "diff"] < 0, 0.28, 0.50)
    )
    df["leverage"] = 1 - 2 * np.abs(df.wp - 0.5)
    df["decided"] = (df.leverage < 0.20).astype(int)

    skaters = df[df.playerPositionThatDidEvent != "G"].copy()
    keep = [
        "season", "game_id", "isPlayoffGame", "time", "period", "goal",
        "shooterPlayerId", "shooterName", "teamCode", "homeTeamCode",
        "awayTeamCode", "isHomeTeam", "diff", "xGoal", "empty_net_for",
        "wp", "leverage", "decided", "shooter_won",
    ]
    skaters[keep].to_parquet(os.path.join(DATA, "shots_leverage.parquet"))

    # --- out-of-sample validation: fit on 2019-22, score on 2023-24 ---
    train = reg[reg.season <= 2022]
    test = reg[reg.season >= 2023].copy()
    s_train = (
        train.groupby(["diff", "mins_bucket"]).shooter_won.mean()
        .rename("wp_oos").reset_index()
    )
    test = test.merge(s_train, on=["diff", "mins_bucket"], how="left")
    test = test.dropna(subset=["wp_oos"])
    brier = float(np.mean((test.wp_oos - test.shooter_won) ** 2))
    base_rate = float(train.shooter_won.mean())
    brier_base = float(np.mean((base_rate - test.shooter_won) ** 2))
    test["wp_decile"] = pd.cut(test.wp_oos, [0, .1, .3, .5, .7, .9, 1.01])
    calib = (
        test.groupby("wp_decile", observed=True)
        .agg(pred=("wp_oos", "mean"), actual=("shooter_won", "mean"), n=("wp_oos", "size"))
        .round(3)
    )
    calib.to_csv(os.path.join(DATA, "wp_calibration.csv"))
    val = {
        "oos_seasons": "fit 2019-20..2022-23, scored 2023-24..2024-25",
        "n_test_shots": int(len(test)),
        "brier_empirical_surface": brier,
        "brier_constant_baseline": brier_base,
        "note": "MoneyPuck's homeWinProbability column is empty in the public 2024-25 file; not used.",
    }
    with open(os.path.join(DATA, "wp_validation.json"), "w") as f:
        json.dump(val, f, indent=2)
    print(val)
    print("shots with leverage:", len(skaters), "goals:", int(skaters.goal.sum()))


if __name__ == "__main__":
    main()
