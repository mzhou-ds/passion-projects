"""Part 4: Is a garbage-time profile a trait or a uniform?

Three tests on player-seasons with 12+ goals:
1. Persistence: corr(player's decided-goal share this season,
   his share next season), split by players who stayed vs switched teams.
2. The switcher test: for the 131 player-seasons followed by a team
   change, corr(next share) with (a) his own old share, (b) his OLD
   team's mean share, (c) his NEW team's mean share.
3. Team level: does deleting decided goals hurt prediction? Correlate
   raw goal differential and leverage-weighted goal differential with
   next season's points percentage (win share from game results).

Outputs: data/switcher_panel.csv, data/persistence_stats.json,
data/team_panel.csv
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def corr(a, b) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def main() -> None:
    ps = pd.read_csv(os.path.join(DATA, "player_seasons.csv"))
    ps = ps[ps.goals >= 12].copy()
    team_mean = (
        ps.groupby(["season", "teamCode"]).decided_share.mean()
        .rename("team_decided_share").reset_index()
    )
    ps = ps.merge(team_mean, on=["season", "teamCode"])
    ps = ps.sort_values(["shooterPlayerId", "season"])
    for c in ["decided_share", "teamCode", "team_decided_share", "season"]:
        ps["next_" + c] = ps.groupby("shooterPlayerId")[c].shift(-1)
    panel = ps[ps.next_season == ps.season + 1].copy()
    panel["switched"] = panel.teamCode != panel.next_teamCode
    panel.to_csv(os.path.join(DATA, "switcher_panel.csv"), index=False)

    stay = panel[~panel.switched]
    switch = panel[panel.switched]
    stats = {
        "n_panel": int(len(panel)),
        "n_stay": int(len(stay)),
        "n_switch": int(len(switch)),
        "corr_own_share_next_stay": corr(stay.decided_share, stay.next_decided_share),
        "corr_own_share_next_switch": corr(switch.decided_share, switch.next_decided_share),
        "corr_own_share_next_all": corr(panel.decided_share, panel.next_decided_share),
        "corr_new_team_share_next_switch": corr(
            switch.next_team_decided_share, switch.next_decided_share
        ),
        "corr_old_team_share_next_switch": corr(
            switch.team_decided_share, switch.next_decided_share
        ),
        "corr_team_share_same_season": corr(ps.decided_share, ps.team_decided_share),
    }

    # --- team level: raw vs leverage-weighted goal differential ---
    df = pd.read_parquet(os.path.join(DATA, "shots_leverage.parquet"))
    reg = df[df.isPlayoffGame == 0].copy()
    reg["lev_goal"] = reg.goal * reg.leverage
    reg["def_team"] = np.where(
        reg.teamCode == reg.homeTeamCode, reg.awayTeamCode, reg.homeTeamCode
    )
    gf = reg.groupby(["season", "teamCode"]).agg(
        gf=("goal", "sum"), lev_gf=("lev_goal", "sum")
    ).reset_index()
    ga = reg[reg.goal == 1].groupby(["season", "def_team"]).agg(
        ga=("goal", "sum"), lev_ga=("lev_goal", "sum")
    ).reset_index().rename(columns={"def_team": "teamCode"})
    tg = gf.merge(ga, on=["season", "teamCode"])
    tg["goal_diff"] = tg.gf - tg.ga
    tg["lev_goal_diff"] = tg.lev_gf - tg.lev_ga
    games = reg.drop_duplicates(["season", "game_id", "teamCode"])
    pts = games.groupby(["season", "teamCode"]).agg(
        gp=("game_id", "count"), wins=("shooter_won", "sum")
    ).reset_index()
    pts["win_share"] = pts.wins / pts.gp
    tg = tg.merge(pts, on=["season", "teamCode"])
    tg = tg.sort_values(["teamCode", "season"])
    for c in ["win_share", "season"]:
        tg["next_" + c] = tg.groupby("teamCode")[c].shift(-1)
    tp = tg[tg.next_season == tg.season + 1]
    tg.to_csv(os.path.join(DATA, "team_panel.csv"), index=False)
    stats.update({
        "team_panel_n": int(len(tp)),
        "corr_raw_gd_next_win_share": corr(tp.goal_diff, tp.next_win_share),
        "corr_lev_gd_next_win_share": corr(tp.lev_goal_diff, tp.next_win_share),
        "corr_win_share_next_win_share": corr(tp.win_share, tp.next_win_share),
        "corr_raw_gd_same_win_share": corr(tp.goal_diff, tp.win_share),
        "corr_lev_gd_same_win_share": corr(tp.lev_goal_diff, tp.win_share),
    })
    with open(os.path.join(DATA, "persistence_stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))
    print("\nBig-name switchers:")
    big = switch.sort_values("goals", ascending=False).head(10)
    print(big[["season", "shooterName", "teamCode", "next_teamCode", "goals",
               "decided_share", "next_decided_share", "team_decided_share",
               "next_team_decided_share"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
