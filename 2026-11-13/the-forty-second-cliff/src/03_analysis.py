"""Core analysis: the shift-length cliff.

1. Fit a simple logistic xG model on 5v5 shot attempts (distance, angle,
   shot type, rebound), held out by game, so shots are quality-weighted.
2. Rate curves: xG for/against, goals, attempts per 60 by mean shift age.
3. Assumption-free check: share of conceded xG vs share of 5v5 time by bucket.
4. Penalty rate by shift age. 5. The change tax. 6. Team fatigue tax.
7. Player-level: shift length by star/position; Oilers spotlight.
"""
import json, os
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
BUCKET_LABELS = ["0-10", "10-20", "20-30", "30-40", "40-50", "50-60",
                 "60-70", "70-80", "80-90", "90+"]

import glob as _glob
_id2abbr = {}
for _f in _glob.glob(os.path.join(DATA, "raw", "shifts_*.json")):
    for _s in json.load(open(_f))["data"][:50]:
        _id2abbr[_s["teamId"]] = _s["teamAbbrev"]
    if len(_id2abbr) >= 32:
        break

shots = pd.read_csv(os.path.join(DATA, "shots_5v5.csv"))
exp = pd.read_csv(os.path.join(DATA, "exposure_5v5.csv"))
pens = pd.read_csv(os.path.join(DATA, "penalties_5v5.csv"))
players = pd.read_csv(os.path.join(DATA, "player_shifts.csv"))
positions = pd.read_csv(os.path.join(DATA, "player_positions.csv"))

# ---------- 1. xG model ----------
shots = shots.dropna(subset=["dist", "angle"]).copy()
X = pd.get_dummies(shots[["dist", "angle", "rebound", "shot_type"]],
                   columns=["shot_type"], drop_first=True).astype(float)
y = shots["is_goal"].astype(int)
games = shots["game_id"].values
cut = np.quantile(games, 0.8)
tr, te = games <= cut, games > cut
model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, C=1.0))
model.fit(X[tr], y[tr])
auc = roc_auc_score(y[te], model.predict_proba(X[te])[:, 1])
shots["xg"] = model.predict_proba(X)[:, 1]
print(f"xG model AUC (held-out games): {auc:.3f} | base goal rate: {y.mean():.4f}")

# ---------- 2. rate curves ----------
# exposure: team 5v5 seconds by bucket. A team defends ~half its 5v5 time
# (league possession is 50/50 by construction), so defending exposure is
# 0.5 * team time in the bucket. The 0.5 is constant across buckets, so the
# SHAPE of the curve does not depend on it; only the level does.
time_by_bucket = exp.groupby("bucket")["seconds"].sum()  # team-seconds
n_games = shots["game_id"].nunique()
def rate_table(bucket_col, value_col, label):
    g = shots.groupby(bucket_col).agg(xg=(value_col, "sum"), goals=("is_goal", "sum"),
                                      n=("is_goal", "size"))
    g["team_hours"] = time_by_bucket / 3600
    g["def_hours"] = g["team_hours"] * 0.5
    g["xg_per60"] = g["xg"] / g["def_hours"]
    g["g_per60"] = g["goals"] / g["def_hours"]
    g["att_per60"] = g["n"] / g["def_hours"]
    g["bucket_label"] = [BUCKET_LABELS[i] for i in g.index]
    return g.reset_index()

def_curve = rate_table("def_bucket", "xg", "against")
att_curve = rate_table("att_bucket", "xg", "for")
def_curve.to_csv(os.path.join(DATA, "curve_defense.csv"), index=False)
att_curve.to_csv(os.path.join(DATA, "curve_offense.csv"), index=False)

# ---------- 3. assumption-free: xG share vs time share ----------
tot_xg_against = shots["xg"].sum()
share = pd.DataFrame({
    "bucket": BUCKET_LABELS,
    "time_share": (time_by_bucket / time_by_bucket.sum()).values,
    "xg_against_share": (shots.groupby("def_bucket")["xg"].sum()
                         / tot_xg_against).reindex(range(10)).fillna(0).values,
    "goal_share": (shots.groupby("def_bucket")["is_goal"].sum()
                   / shots["is_goal"].sum()).reindex(range(10)).fillna(0).values,
})
share["xg_overrep"] = share["xg_against_share"] / share["time_share"]
share.to_csv(os.path.join(DATA, "share_vs_time.csv"), index=False)

# ---------- 4. penalty rate by shift age (exposure = full team time) ----------
pen_g = pens.groupby("bucket").size().reindex(range(10)).fillna(0)
pen_rate = pd.DataFrame({
    "bucket": BUCKET_LABELS,
    "penalties": pen_g.values,
    "team_hours": (time_by_bucket / 3600).reindex(range(10)).fillna(0).values,
})
pen_rate["pen_per60"] = pen_rate["penalties"] / pen_rate["team_hours"]
pen_rate.to_csv(os.path.join(DATA, "penalty_rate.csv"), index=False)

# ---------- 5. change tax ----------
chg = shots[shots["def_n_fresh"] >= 2]
chg_exp_sec = exp.loc[exp["change_state"] == 1, "seconds"].sum()
tot_exp_sec = exp["seconds"].sum()
chg_rate = len(chg[chg["is_goal"]]) / (chg_exp_sec / 3600 * 0.5)   # goals/60 defending
base_rate = shots["is_goal"].sum() / (tot_exp_sec / 3600 * 0.5)
change_tax = {"change_goals": int(chg["is_goal"].sum()),
              "change_xg": float(chg["xg"].sum()),
              "change_team_hours": float(chg_exp_sec / 3600),
              "change_share_of_time": float(chg_exp_sec / tot_exp_sec),
              "change_goals_per60": float(chg_rate),
              "overall_goals_per60": float(base_rate),
              "change_ratio": float(chg_rate / base_rate)}

# ---------- 6. team fatigue tax ----------
# league-average xGA/60 per bucket (defending) as the reference curve
league_rate = def_curve.set_index("def_bucket")["xg_per60"]
exp["team_abbr"] = exp["team"].map(_id2abbr)
shots["def_abbr"] = shots["def_team"].map(_id2abbr)
shots["att_abbr"] = shots["att_team"].map(_id2abbr)
team_exp = exp.groupby(["team_abbr", "bucket"])["seconds"].sum().unstack(fill_value=0)
team_xga = shots.groupby("def_abbr")["xg"].sum()
team_games = shots.groupby("def_abbr")["game_id"].nunique()
rows = []
for team in team_exp.index:
    hours_by_bucket = team_exp.loc[team] / 3600 * 0.5  # defending hours
    expected_xga = float((hours_by_bucket * league_rate).sum())
    observed_xga = float(team_xga.get(team, 0))
    gp = int(team_games.get(team, 82))
    rows.append({"team": team, "games": gp,
                 "observed_xga": observed_xga, "expected_xga": expected_xga,
                 "excess_xga_per82": (observed_xga - expected_xga) / gp * 82,
                 "pct_time_over60": float(team_exp.loc[team, 6:].sum()
                                          / team_exp.loc[team].sum())})
team_tax = pd.DataFrame(rows).sort_values("excess_xga_per82", ascending=False)
team_tax.to_csv(os.path.join(DATA, "team_fatigue_tax.csv"), index=False)

# team mean shift length
team_shift = (players.groupby("team")["duration"].agg(["mean", "count"])
              .rename(columns={"mean": "mean_shift_sec", "count": "n_shifts"})
              .sort_values("mean_shift_sec", ascending=False))
team_shift.to_csv(os.path.join(DATA, "team_shift_length.csv"))

# ---------- 7. players ----------
pos = positions.set_index("player_id")["position"]
players["position"] = players["player_id"].map(pos)
pagg = (players.groupby(["player_id", "first", "last", "team", "position"])
        ["duration"].agg(["mean", "count", "median"]).reset_index()
        .rename(columns={"mean": "mean_shift", "count": "n_shifts",
                         "median": "median_shift"}))
stars = pagg[pagg["n_shifts"] >= 500].sort_values("mean_shift", ascending=False)
stars.to_csv(os.path.join(DATA, "player_shift_length.csv"), index=False)
pos_summary = pagg[pagg["n_shifts"] >= 200].groupby("position")["mean_shift"].agg(["mean", "count"])
print(pos_summary)

# cliff detection: biggest jump in xGA/60 between adjacent buckets
rates = def_curve["xg_per60"].values
jumps = np.diff(rates)
cliff_i = int(np.argmax(jumps))
early = def_curve.loc[def_curve["def_bucket"] <= 3, "xg_per60"].mean()
late = def_curve.loc[def_curve["def_bucket"] >= 6, "xg_per60"].mean()
att_early = att_curve.loc[att_curve["att_bucket"] <= 3, "xg_per60"].mean()
att_late = att_curve.loc[att_curve["att_bucket"] >= 6, "xg_per60"].mean()

# ---------- 8. fatigue vs siege: joint-bucket decomposition ----------
# Slice B (both teams old, att_bucket >= 4): long continuous play, nobody
# changed. No siege-selection: the attackers are as tired as the defenders.
# Slice A (attackers fresh, att_bucket <= 2; defenders old): the classic
# siege, fresh legs cycling in against a trapped line. If the cliff survives
# in slice B, fatigue is doing real work on top of selection.
def joint_curve(att_lo, att_hi):
    sub = shots[(shots["att_bucket"] >= att_lo) & (shots["att_bucket"] <= att_hi)]
    ex = exp[(exp["opp_bucket"] >= att_lo) & (exp["opp_bucket"] <= att_hi)]
    g = sub.groupby("def_bucket").agg(xg=("xg", "sum"), goals=("is_goal", "sum"),
                                      n=("is_goal", "size"))
    hours = (ex.groupby("bucket")["seconds"].sum() / 3600 * 0.5).reindex(range(10)).fillna(0)
    out = pd.DataFrame({"bucket": BUCKET_LABELS, "xg_per60": (g["xg"] / hours).reindex(range(10)).fillna(0).values,
                        "g_per60": (g["goals"] / hours).reindex(range(10)).fillna(0).values,
                        "att_per60": (g["n"] / hours).reindex(range(10)).fillna(0).values,
                        "hours": hours.values, "n": g["n"].reindex(range(10)).fillna(0).values})
    return out

both_old = joint_curve(4, 9)    # attackers 40s+ too
fresh_att = joint_curve(0, 2)   # attackers 0-30s (siege slice)
both_old.to_csv(os.path.join(DATA, "curve_both_old.csv"), index=False)
fresh_att.to_csv(os.path.join(DATA, "curve_fresh_attackers.csv"), index=False)
def _ratio(df):
    e = df.loc[df["bucket"].isin(["10-20", "20-30"]), "xg_per60"].mean()
    l = df.loc[df["bucket"].isin(["60-70", "70-80", "80-90", "90+"]), "xg_per60"].mean()
    return round(float(l / e), 2) if e else None
decomp = {"both_old_ratio_60plus_vs_10_30": _ratio(both_old),
          "fresh_att_ratio_60plus_vs_10_30": _ratio(fresh_att),
          "both_old_60plus_xg_per60": round(float(both_old.loc[both_old["bucket"].isin(
              ["60-70", "70-80", "80-90", "90+"]), "xg_per60"].mean()), 2),
          "both_old_10_30_xg_per60": round(float(both_old.loc[both_old["bucket"].isin(
              ["10-20", "20-30"]), "xg_per60"].mean()), 2),
          "fresh_att_60plus_xg_per60": round(float(fresh_att.loc[fresh_att["bucket"].isin(
              ["60-70", "70-80", "80-90", "90+"]), "xg_per60"].mean()), 2)}

# ---------- 9. change analysis by number of fresh defenders ----------
fresh_exp = exp.groupby("n_fresh")["seconds"].sum() / 3600 * 0.5  # defending hours
fresh_shots = shots.groupby("def_n_fresh").agg(xg=("xg", "sum"), goals=("is_goal", "sum"),
                                               n=("is_goal", "size"))
fresh_tab = pd.DataFrame({
    "n_fresh_defenders": fresh_shots.index,
    "defending_hours": fresh_exp.reindex(fresh_shots.index).values,
    "xg_per60": (fresh_shots["xg"] / fresh_exp).values,
    "g_per60": (fresh_shots["goals"] / fresh_exp).values,
    "att_per60": (fresh_shots["n"] / fresh_exp).values,
    "goals": fresh_shots["goals"].values})
fresh_tab.to_csv(os.path.join(DATA, "fresh_count.csv"), index=False)

findings = {
    "season": "2025-26", "games": int(n_games),
    "shots_5v5": int(len(shots)), "goals_5v5": int(shots["is_goal"].sum()),
    "xg_auc": round(float(auc), 3),
    "five_v_five_team_hours": round(float(exp["seconds"].sum() / 3600), 1),
    "def_curve": def_curve.to_dict("records"),
    "att_curve": att_curve.to_dict("records"),
    "share_vs_time": share.to_dict("records"),
    "penalty_rate": pen_rate.to_dict("records"),
    "change_tax": change_tax,
    "cliff": {"biggest_jump_between": f"{BUCKET_LABELS[cliff_i]} -> {BUCKET_LABELS[cliff_i+1]}",
              "jump_xg_per60": round(float(jumps[cliff_i]), 3),
              "xg_per60_0_40s": round(float(early), 3),
              "xg_per60_60s_plus": round(float(late), 3),
              "def_ratio_late_vs_early": round(float(late / early), 2),
              "att_xg_per60_0_40s": round(float(att_early), 3),
              "att_xg_per60_60s_plus": round(float(att_late), 3),
              "att_ratio_late_vs_early": round(float(att_late / att_early), 2)},
    "team_tax_top5": team_tax.head(5).to_dict("records"),
    "team_tax_bottom5": team_tax.tail(5).to_dict("records"),
    "team_tax_oilers": team_tax[team_tax["team"] == "EDM"].to_dict("records"),
    "team_shift_top5": team_shift.head(5).reset_index().to_dict("records"),
    "team_shift_bottom5": team_shift.tail(5).reset_index().to_dict("records"),
    "team_shift_oilers": team_shift.loc[["EDM"]].reset_index().to_dict("records") if "EDM" in team_shift.index else [],
    "longest_shift_stars": stars.head(10).to_dict("records"),
    "oilers_stars": stars[stars["team"] == "EDM"].head(8).to_dict("records"),
    "decomposition": decomp,
    "fresh_count": fresh_tab.to_dict("records"),
    "mcdavid": stars[stars["last"] == "McDavid"].to_dict("records"),
    "draisaitl": stars[stars["last"] == "Draisaitl"].to_dict("records"),
}
json.dump(findings, open(os.path.join(DATA, "findings.json"), "w"), indent=2)
print(json.dumps({k: findings[k] for k in
                  ["xg_auc", "shots_5v5", "goals_5v5", "cliff", "change_tax"]}, indent=2))
print("Oilers tax:", findings["team_tax_oilers"])
print("Oilers shift:", findings["team_shift_oilers"])
