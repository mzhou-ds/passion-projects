"""The standings lab: re-rank 12 NHL seasons under three points systems.

Systems
  nhl   : 2 for any win, 1 for an OT/SO loss, 0 for a regulation loss (actual)
  wl    : 2 for any win, 0 for any loss  (the loser point deleted)
  iihf  : 3 regulation win, 2 OT/SO win, 1 OT/SO loss, 0 regulation loss

For every team-season we rebuild the record split by how games ended
(regulation / OT / shootout) from data/games.csv, validate the NHL-system
points against the official final standings, then apply the league's actual
playoff format (top 3 per division + 2 wild cards per conference) under each
system and count who gets in and who gets bounced.

Also: "hope" snapshots. On Feb 1 / Mar 1 / Apr 1 of each season we rebuild the
standings to that date under each system and count how many teams sit within
0.030 points-percentage of the playoff cutline -- the manufactured-closeness
metric. A system that keeps more fanbases "in it" longer is a retention
product, whether or not it ranks teams better.

Excluded from the playoff-field simulation: 2019-20 (COVID-truncated, 24-team
playoffs) and 2020-21 (one-off divisions, divisional playoffs). Both stay in
the league-wide trend table.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_FIELD = {20192020, 20202021}
SNAPSHOTS = ["02-01", "03-01", "04-01"]


def team_records(games):
    """Per team-season record split by ending type."""
    rows = {}
    for _, g in games.iterrows():
        for team, gf, ga, is_winner in (
            (g["home"], g["home_goals"], g["away_goals"], g["winner"] == g["home"]),
            (g["away"], g["away_goals"], g["home_goals"], g["winner"] == g["away"]),
        ):
            r = rows.setdefault((g["season"], team), dict(
                season=g["season"], season_label=g["season_label"], team=team,
                gp=0, reg_w=0, ot_w=0, so_w=0, reg_l=0, ot_l=0, so_l=0, gf=0, ga=0))
            r["gp"] += 1
            r["gf"] += gf
            r["ga"] += ga
            kind = {"REG": "reg", "OT": "ot", "SO": "so"}[g["last_period"]]
            r[f"{kind}_{'w' if is_winner else 'l'}"] += 1
    df = pd.DataFrame(rows.values())
    df["wins"] = df.reg_w + df.ot_w + df.so_w
    df["row"] = df.reg_w + df.ot_w  # regulation + OT wins (official tiebreaker)
    df["ot_losses"] = df.ot_l + df.so_l
    df["goal_diff"] = df.gf - df.ga
    return df


def add_points(df):
    df["pts_nhl"] = 2 * df.wins + df.ot_losses
    df["pts_wl"] = 2 * df.wins
    df["pts_iihf"] = 3 * df.reg_w + 2 * (df.ot_w + df.so_w) + df.ot_losses
    # max attainable points per game differs by system; points% normalizes
    df["pct_nhl"] = df.pts_nhl / (2 * df.gp)
    df["pct_wl"] = df.pts_wl / (2 * df.gp)
    df["pct_iihf"] = df.pts_iihf / (3 * df.gp)
    return df


def playoff_field(table, system):
    """table: team records with division/conference for one season.
    Returns set of playoff teams under the given system ('nhl'|'wl'|'iihf')."""
    pts = f"pts_{system}"
    t = table.sort_values(
        [pts, "reg_w", "row", "goal_diff", "gf"],
        ascending=False).copy()
    t["div_rank"] = t.groupby("division")[pts].rank(method="first", ascending=False)
    in_field = set(t[t.div_rank <= 3].team)
    for conf, grp in t.groupby("conference"):
        rest = grp[~grp.team.isin(in_field)].sort_values(
            [pts, "reg_w", "row", "goal_diff", "gf"], ascending=False)
        in_field.update(rest.head(2).team)
    return in_field


def hope_snapshot(games, season, mmdd, meta):
    """Teams within 0.030 points% of the cutline, per system, at a date."""
    yr = int(str(season)[:4]) if int(mmdd[:2]) >= 10 else int(str(season)[:4]) + 1
    cutoff = f"{yr}-{mmdd}"
    sub = games[(games.season == season) & (games.date < cutoff)]
    if sub.empty:
        return None
    rec = add_points(team_records(sub)).merge(meta, on=["season", "team"])
    out = {"season": season, "season_label": rec.season_label.iloc[0], "date": mmdd}
    for system in ("nhl", "wl", "iihf"):
        field = playoff_field(rec, system)
        pct = f"pct_{system}"
        pts = f"pts_{system}"
        # raw-points window as broadcasters count it ("six points back");
        # IIHF hands out 3 points a game, so its window scales to 9
        window = 9 if system == "iihf" else 6
        in_hunt = 0
        in_hunt_raw = 0
        for conf, grp in rec.groupby("conference"):
            cut = grp[grp.team.isin(field)][pct].min()
            in_hunt += int(((cut - grp[pct]) <= 0.030).sum())
            cut_raw = grp[grp.team.isin(field)][pts].min()
            in_hunt_raw += int(((cut_raw - grp[pts]) <= window).sum())
        out[f"hope_{system}"] = in_hunt
        out[f"hope_raw_{system}"] = in_hunt_raw
        out[f"n_teams"] = len(rec)
    return out


def main():
    games = pd.read_csv(ROOT / "data" / "games.csv")
    meta = pd.read_csv(ROOT / "data" / "standings_final.csv")[
        ["season", "team", "division", "conference", "official_points"]]
    rec = add_points(team_records(games)).merge(meta, on=["season", "team"])

    # --- validation: rebuilt NHL points vs official standings ---------------
    bad = rec[rec.pts_nhl != rec.official_points]
    validation = {
        "team_seasons_checked": int(len(rec)),
        "mismatches": int(len(bad)),
        "mismatch_detail": bad[["season_label", "team", "pts_nhl", "official_points"]]
        .to_dict("records"),
    }
    print(f"validation: {len(rec)} team-seasons, {len(bad)} point mismatches")

    # --- league-wide trends --------------------------------------------------
    trends = games.groupby(["season", "season_label"]).agg(
        games=("game_id", "count"), ot_rate=("went_ot", "mean"),
        so_rate=("went_so", "mean"), home_win=("home_win", "mean"),
        goals_per_game=("home_goals", lambda s: 0)).reset_index()
    goals = games.assign(total=games.home_goals + games.away_goals).groupby("season").total.mean()
    trends["goals_per_game"] = trends.season.map(goals)
    trends["three_point_rate"] = trends.ot_rate  # every OT/SO game awards 3 total points
    trends["spread_pct_nhl"] = rec.groupby("season").pct_nhl.std().values
    trends["spread_pct_wl"] = rec.groupby("season").pct_wl.std().values
    trends["spread_pct_iihf"] = rec.groupby("season").pct_iihf.std().values
    trends.to_csv(ROOT / "data" / "season_trends.csv", index=False)

    # --- playoff-field simulation -------------------------------------------
    flips, field_rows = [], []
    for season, grp in rec.groupby("season"):
        if season in EXCLUDE_FIELD:
            continue
        actual = playoff_field(grp, "nhl")
        for system in ("wl", "iihf"):
            alt = playoff_field(grp, system)
            if alt != actual:
                flips.append({
                    "season": season, "season_label": grp.season_label.iloc[0],
                    "system": system,
                    "in": sorted(alt - actual), "out": sorted(actual - alt)})
        for system in ("nhl", "wl", "iihf"):
            f = playoff_field(grp, system)
            for _, r in grp.iterrows():
                field_rows.append({
                    "season": season, "season_label": r.season_label,
                    "team": r.team, "system": system,
                    "playoffs": r.team in f,
                    "points": int(r[f"pts_{system}"]), "pct": round(r[f"pct_{system}"], 4)})
    pd.DataFrame(field_rows).to_csv(ROOT / "data" / "playoff_fields.csv", index=False)

    # --- hope snapshots -------------------------------------------------------
    hope = [hope_snapshot(games, s, d, meta)
            for s in sorted(games.season.unique()) if s not in {20202021}
            for d in SNAPSHOTS]
    hope_df = pd.DataFrame([h for h in hope if h])
    hope_df.to_csv(ROOT / "data" / "hope_snapshots.csv", index=False)

    # --- Oilers lens ------------------------------------------------------------
    edm = rec[rec.team == "EDM"].copy()
    edm_rows = []
    fields = pd.DataFrame(field_rows)
    for _, r in edm.iterrows():
        row = {"season_label": r.season_label, "gp": int(r.gp), "wins": int(r.wins),
               "ot_losses": int(r.ot_losses), "loser_points": int(r.ot_losses),
               "pts_nhl": int(r.pts_nhl), "pct_nhl": round(r.pct_nhl, 3),
               "pct_wl": round(r.pct_wl, 3), "pct_iihf": round(r.pct_iihf, 3)}
        f = fields[fields.season == r.season]
        for system in ("nhl", "wl", "iihf"):
            sub = f[f.system == system]
            if len(sub):
                row[f"playoffs_{system}"] = bool(
                    sub[sub.team == "EDM"].playoffs.iloc[0])
        edm_rows.append(row)
    pd.DataFrame(edm_rows).to_csv(ROOT / "data" / "oilers.csv", index=False)

    # --- loser-point merchants --------------------------------------------------
    rec["lp_share"] = rec.ot_losses / rec.pts_nhl
    merchants_season = rec.nlargest(5, "ot_losses")[
        ["season_label", "team", "wins", "reg_w", "ot_losses", "pts_nhl", "lp_share"]]
    merchants_all = (rec.groupby("team").agg(
        otl=("ot_losses", "sum"), pts=("pts_nhl", "sum")).reset_index())
    merchants_all["lp_share"] = merchants_all.otl / merchants_all.pts
    merchants_all = merchants_all.nlargest(5, "otl")
    fields_df = pd.DataFrame(field_rows)
    nhl_fields = fields_df[fields_df.system == "nhl"]
    po = nhl_fields[nhl_fields.playoffs].merge(
        rec[["season", "team", "ot_losses", "wins", "reg_w"]],
        on=["season", "team"])
    po_merchants = po.nlargest(5, "ot_losses")[
        ["season_label", "team", "wins", "reg_w", "ot_losses"]]
    merchants = {
        "top_team_seasons": merchants_season.assign(
            lp_share=merchants_season.lp_share.round(3)).to_dict("records"),
        "top_teams_12yr": merchants_all.assign(
            lp_share=merchants_all.lp_share.round(3)).to_dict("records"),
        "top_playoff_teams": po_merchants.to_dict("records"),
    }

    findings = {
        "validation": validation,
        "merchants": merchants,
        "hope_raw_mar1_means": {
            s: round(float(hope_df[hope_df.date == "03-01"][f"hope_raw_{s}"].mean()), 2)
            for s in ("nhl", "wl", "iihf")},
        "flips": flips,
        "n_field_flips_wl": sum(1 for f in flips if f["system"] == "wl"),
        "n_field_flips_iihf": sum(1 for f in flips if f["system"] == "iihf"),
        "seasons_simulated": int(rec[~rec.season.isin(EXCLUDE_FIELD)].season.nunique()),
        "hope_mar1_means": {
            s: round(float(hope_df[hope_df.date == "03-01"][f"hope_{s}"].mean()), 2)
            for s in ("nhl", "wl", "iihf")},
        "hope_mar1_total_teams": int(hope_df[hope_df.date == "03-01"].n_teams.iloc[-1]),
        "ot_rate_first_season": round(float(trends.ot_rate.iloc[0]), 4),
        "ot_rate_last_season": round(float(trends.ot_rate.iloc[-1]), 4),
        "ot_rate_all": round(float(games.went_ot.mean()), 4),
        "total_games": int(len(games)),
        "total_loser_points": int(rec.ot_losses.sum()),
        "spread_ratio_nhl_vs_wl": round(float(
            trends.spread_pct_nhl.mean() / trends.spread_pct_wl.mean()), 3),
        "spread_ratio_nhl_vs_iihf": round(float(
            trends.spread_pct_nhl.mean() / trends.spread_pct_iihf.mean()), 3),
    }
    (ROOT / "data" / "findings_standings.json").write_text(json.dumps(findings, indent=1))
    print(json.dumps(findings, indent=1))
    rec.to_csv(ROOT / "data" / "team_seasons.csv", index=False)


if __name__ == "__main__":
    main()
