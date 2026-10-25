"""Part 1-3: How much scoring happens after games are decided?

- Share of shots / goals by leverage bucket, regular season and playoffs
- Conversion and xG per shot by bucket, with and without empty-net shots
  (tests the lazy version of the story: 'garbage time is just softer')
- The empty-net audit: share of all goals, their mean leverage
- Player-season leverage profiles and the star table

Outputs: data/bucket_stats.csv, data/playoff_bucket_stats.csv,
data/player_seasons.csv, data/star_profiles.csv, data/headline_stats.json
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
BUCKETS = [0, 0.2, 0.4, 0.6, 0.8, 1.01]
LABELS = ["0.0-0.2 decided", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0 coin-flip"]


def bucket_stats(df: pd.DataFrame) -> pd.DataFrame:
    d = df.assign(bucket=pd.cut(df.leverage, BUCKETS, labels=LABELS))
    out = (
        d.groupby("bucket", observed=True)
        .agg(
            shots=("goal", "size"),
            goals=("goal", "sum"),
            conversion=("goal", "mean"),
            xg_per_shot=("xGoal", "mean"),
            empty_net_share=("empty_net_for", "mean"),
        )
        .reset_index()
    )
    out["shot_share"] = out.shots / out.shots.sum()
    out["goal_share"] = out.goals / out.goals.sum()
    return out


def main() -> None:
    df = pd.read_parquet(os.path.join(DATA, "shots_leverage.parquet"))
    reg = df[df.isPlayoffGame == 0]
    po = df[df.isPlayoffGame == 1]

    bs = bucket_stats(reg)
    bs.to_csv(os.path.join(DATA, "bucket_stats.csv"), index=False)
    bucket_stats(po).to_csv(os.path.join(DATA, "playoff_bucket_stats.csv"), index=False)

    no_en = bucket_stats(reg[reg.empty_net_for == 0])
    no_en.to_csv(os.path.join(DATA, "bucket_stats_no_empty_net.csv"), index=False)

    goals = reg[reg.goal == 1]
    en_goals = goals[goals.empty_net_for == 1]
    headline = {
        "regular_season_goals": int(len(goals)),
        "decided_share_of_goals": float(goals.decided.mean()),
        "decided_share_of_shots": float(reg.decided.mean()),
        "decided_share_of_goals_no_empty_net": float(
            goals[goals.empty_net_for == 0].decided.mean()
        ),
        "playoff_decided_share_of_goals": float(po[po.goal == 1].decided.mean()),
        "empty_net_goals": int(len(en_goals)),
        "empty_net_share_of_all_goals": float(len(en_goals) / len(goals)),
        "empty_net_mean_leverage": float(en_goals.leverage.mean()),
        "empty_net_share_of_decided_goals": float(
            en_goals.decided.sum() / goals.decided.sum()
        ),
        "mean_leverage_all_goals": float(goals.leverage.mean()),
        "conversion_decided": float(
            bs.loc[bs.bucket == LABELS[0], "conversion"].iloc[0]
        ),
        "conversion_coinflip": float(
            bs.loc[bs.bucket == LABELS[-1], "conversion"].iloc[0]
        ),
        "conversion_decided_no_en": float(
            no_en.loc[no_en.bucket == LABELS[0], "conversion"].iloc[0]
        ),
        "conversion_coinflip_no_en": float(
            no_en.loc[no_en.bucket == LABELS[-1], "conversion"].iloc[0]
        ),
    }

    # player-season profiles (primary team = team of most attempts)
    g = goals.copy()
    g["clutch_goal"] = (g.leverage > 0.8).astype(int)
    ps = (
        g.groupby(["season", "shooterPlayerId", "shooterName"])
        .agg(
            goals=("goal", "sum"),
            decided_goals=("decided", "sum"),
            clutch_goals=("clutch_goal", "sum"),
            leverage_goals=("leverage", "sum"),
            empty_net_goals=("empty_net_for", "sum"),
            xg=("xGoal", "sum"),
        )
        .reset_index()
    )
    att = (
        reg.groupby(["season", "shooterPlayerId"])
        .agg(attempts=("goal", "size"), attempt_xg=("xGoal", "sum"))
        .reset_index()
    )
    prim = (
        reg.groupby(["season", "shooterPlayerId", "teamCode"])
        .size()
        .rename("n_att")
        .reset_index()
        .sort_values("n_att")
        .groupby(["season", "shooterPlayerId"])
        .tail(1)[["season", "shooterPlayerId", "teamCode"]]
    )
    ps = ps.merge(att, on=["season", "shooterPlayerId"]).merge(
        prim, on=["season", "shooterPlayerId"]
    )
    ps["decided_share"] = ps.decided_goals / ps.goals
    ps["clutch_share"] = ps.clutch_goals / ps.goals
    ps["leverage_per_goal"] = ps.leverage_goals / ps.goals
    ps.to_csv(os.path.join(DATA, "player_seasons.csv"), index=False)

    stars = (
        ps.groupby(["shooterPlayerId", "shooterName"])
        .agg(
            goals=("goals", "sum"),
            decided_goals=("decided_goals", "sum"),
            leverage_goals=("leverage_goals", "sum"),
            empty_net_goals=("empty_net_goals", "sum"),
            seasons=("season", "nunique"),
        )
        .reset_index()
    )
    stars = stars[stars.goals >= 150]
    stars["decided_share"] = stars.decided_goals / stars.goals
    stars["leverage_per_goal"] = stars.leverage_goals / stars.goals
    stars = stars.sort_values("leverage_per_goal")
    stars.to_csv(os.path.join(DATA, "star_profiles.csv"), index=False)
    headline["ovechkin"] = stars[stars.shooterName == "Alex Ovechkin"].iloc[0].to_dict()
    for k, v in list(headline["ovechkin"].items()):
        headline["ovechkin"][k] = float(v) if isinstance(v, (np.floating, np.integer)) else v

    with open(os.path.join(DATA, "headline_stats.json"), "w") as f:
        json.dump(headline, f, indent=2, default=str)
    print(json.dumps(headline, indent=2, default=str))
    print("\nStar profiles (150+ goals, 2019-20..2024-25):")
    print(stars.to_string(index=False))


if __name__ == "__main__":
    main()
