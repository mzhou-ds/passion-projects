#!/usr/bin/env python3
"""
Analysis for 'The Empty-Net Era' (build #76).

Reads data/game_features.csv + data/player_goals.csv (produced by 01_fetch.py)
and computes:
  1. Season aggregates: goals per game, ENG per game, ENG share, non-ENG GPG.
  2. Decomposition of the scoring boom into ENG vs non-ENG growth.
  3. Goalie-pull timing trend (first endgame pull, trailing by 1 / by 2).
  4. 6v5 scoring rates vs power-play scoring rates (goals per 60).
  5. Break-even pull time: when pulling the goalie beats staying 5v5,
     from empirical scoring rates (Poisson first-goal model).
  6. XGBoost + SHAP: what predicts whether a game produces an empty-net goal?
  7. Player level: ENG padding in the goal-scoring race; Oilers focus.

Outputs: findings.txt, analysis_results.json, data/season_summary.csv
"""
import json
import math
import os
import re

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..")

SEASON_LABEL = {
    2015: "2015-16", 2016: "2016-17", 2017: "2017-18", 2018: "2018-19",
    2019: "2019-20", 2020: "2020-21", 2021: "2021-22", 2022: "2022-23",
    2023: "2023-24", 2024: "2024-25", 2025: "2025-26", 2026: "2026-27",
}

g = pd.read_csv(os.path.join(DATA, "game_features.csv"))
players = pd.read_csv(os.path.join(DATA, "player_goals.csv"))
players = players[players["player_name"].notna() & (players["player_name"] != "")]
players["player_name"] = players["player_name"].astype(str)


def clean_name(s):
    # Defensive: older runs stored roster names as locale-dict strings
    # ("{'default': 'Auston'} {'default': 'Matthews'}").
    if "{'default'" in s:
        parts = re.findall(r"'default': '([^']+)'", s)
        return " ".join(parts[:2]) if parts else s
    return s


players["player_name"] = players["player_name"].apply(clean_name)

# ---------------------------------------------------------------- validation
g["official_total"] = g["home_score"] + g["away_score"]
bad = g[g["goals_total"] != g["official_total"]]
print(f"games: {len(g)}  score mismatches: {len(bad)}")
assert len(bad) == 0, bad[["game_id", "goals_total", "official_total"]].head()

# External validation: team ENG totals for 2023-24, from StatMuse / Daily Faceoff
# (WPG 24, TBL 23, FLA 21, SJS 4, EDM 12; league average 13.8 per team).
_d23 = g[g["season"] == 2023]
_home = _d23.groupby("home_abbrev")["eng_by_home"].sum()
_away = _d23.groupby("away_abbrev")["eng_by_away"].sum()
_team_eng_2324 = _home.add(_away, fill_value=0).astype(int).to_dict()
_expected = {"WPG": 24, "TBL": 23, "FLA": 21, "SJS": 4, "EDM": 12}
_valid = {t: (_team_eng_2324.get(t), e) for t, e in _expected.items()}
print("team ENG validation 2023-24 (measured, expected):", _valid)
assert all(_team_eng_2324.get(t) == e for t, e in _expected.items()), _valid
assert abs(sum(_team_eng_2324.values()) / 32 - 13.8) < 0.5, sum(_team_eng_2324.values())

# Game-level pull outcomes: the fetch records first-interval outcomes, but a
# coach often pulls, resets, and pulls again. Score the whole game: sum GF/GA
# over ALL endgame intervals and ask whether the net erased the first deficit.
def game_pull_outcomes(row):
    raw = row.get("pull_intervals_json", "")
    try:
        ivs = json.loads(raw) if isinstance(raw, str) and raw else []
    except Exception:
        return pd.Series([None, None, None])
    eg = [iv for iv in ivs if iv[3] < 0 and iv[0] <= 360]  # [start_rem, dur, team, diff, gf, ga]
    if not eg:
        return pd.Series([None, None, None])
    d0 = eg[0][3]
    net = sum(iv[4] - iv[5] for iv in eg)
    tie = 1 if net >= -d0 else 0
    enga = 1 if any(iv[5] > 0 for iv in eg) else 0
    return pd.Series([d0, tie, enga])

_out = g.apply(game_pull_outcomes, axis=1)
_out.columns = ["eg_first_diff", "game_pull_tie", "game_pull_eng"]
g = pd.concat([g, _out], axis=1)

# Full seasons vs partial (2026-27 in progress; 2019-20 and 2020-21 shortened).
full = g[~g["season"].isin([2019, 2020, 2026])]

# ---------------------------------------------------------------- 1. season aggregates
rows = []
for s, d in g.groupby("season"):
    n = len(d)
    goals = d["goals_total"].sum()
    eng = d["eng_total"].sum()
    pp_t = d["pp_time_sec"].sum()
    pp_g = d["pp_goals"].sum()
    sv_t = d["sixv5_time_eg"].sum()
    sv_gf = d["sixv5_gf_eg"].sum()
    sv_ga = d["sixv5_ga_eg"].sum()
    pulls = d[d["first_eg_pull_time_rem"].notna()]
    pulls1 = pulls[pulls["eg_first_diff"] == -1]
    pulls2 = pulls[pulls["eg_first_diff"] == -2]
    rows.append({
        "season": s, "label": SEASON_LABEL[s], "games": n,
        "gpg": goals / n,
        "eng_per_game": eng / n,
        "eng_share_pct": 100 * eng / goals,
        "non_eng_gpg": (goals - eng) / n,
        "eng_total": int(eng), "goals_total": int(goals),
        "pp_time_per_game_min": pp_t / n / 60,
        # goals per 60 minutes = goals * 3600 / seconds
        "pp_gf_per_60": 3600 * pp_g / pp_t if pp_t else np.nan,
        "sixv5_time_per_game_sec": sv_t / n,
        "sixv5_gf_per_60": 3600 * sv_gf / sv_t if sv_t else np.nan,
        "sixv5_ga_per_60": 3600 * sv_ga / sv_t if sv_t else np.nan,
        "games_with_eg_pull": len(pulls),
        "eg_pull_rate_pct": 100 * len(pulls) / n,
        "first_pull_mean_rem_sec": pulls["first_eg_pull_time_rem"].mean(),
        "first_pull_median_rem_sec": pulls["first_eg_pull_time_rem"].median(),
        "first_pull_mean_rem_down1_sec": pulls1["first_eg_pull_time_rem"].mean(),
        "first_pull_median_rem_down1_sec": pulls1["first_eg_pull_time_rem"].median(),
        "first_pull_mean_rem_down2_sec": pulls2["first_eg_pull_time_rem"].mean(),
        "first_pull_median_rem_down2_sec": pulls2["first_eg_pull_time_rem"].median(),
        "pull_tie_rate_down1_pct": 100 * pulls1["game_pull_tie"].mean() if len(pulls1) else np.nan,
        "pull_tie_rate_down2_pct": 100 * pulls2["game_pull_tie"].mean() if len(pulls2) else np.nan,
        "pull_eng_against_down1_pct": 100 * pulls1["game_pull_eng"].mean() if len(pulls1) else np.nan,
    })
S = pd.DataFrame(rows).sort_values("season")
S.to_csv(os.path.join(DATA, "season_summary.csv"), index=False)

# ---------------------------------------------------------------- 2. decomposition
base = S[S["season"] == 2015].iloc[0]
last_full = S[S["season"] == 2025].iloc[0]   # 2025-26: last completed season
peak = S[S["season"] != 2026].sort_values("gpg", ascending=False).iloc[0]
decomp = {
    "gpg_2015_16": round(base["gpg"], 3),
    "peak_label": peak["label"],
    "gpg_peak": round(peak["gpg"], 3),
    "gpg_last_full": round(last_full["gpg"], 3),
    "last_full_label": last_full["label"],
    "gpg_growth_2015_to_last": round(last_full["gpg"] - base["gpg"], 3),
    "eng_growth_2015_to_last": round(last_full["eng_per_game"] - base["eng_per_game"], 3),
    "eng_share_of_growth_2015_to_last_pct": round(
        100 * (last_full["eng_per_game"] - base["eng_per_game"]) / (last_full["gpg"] - base["gpg"]), 1),
    "eng_per_game_2015_16": round(base["eng_per_game"], 3),
    "eng_per_game_peak": round(peak["eng_per_game"], 3),
    "eng_per_game_last_full": round(last_full["eng_per_game"], 3),
    "eng_share_2015_16_pct": round(base["eng_share_pct"], 2),
    "eng_share_peak_pct": round(peak["eng_share_pct"], 2),
    "eng_share_last_full_pct": round(last_full["eng_share_pct"], 2),
    "non_eng_gpg_2015_16": round(base["non_eng_gpg"], 3),
    "non_eng_gpg_peak": round(peak["non_eng_gpg"], 3),
    "non_eng_gpg_last_full": round(last_full["non_eng_gpg"], 3),
    "eng_growth_multiple": round(last_full["eng_per_game"] / base["eng_per_game"], 2),
}

# ---------------------------------------------------------------- 3. pull timing trend
pull_trend = {
    "first_pull_median_down1_2015": float(S[S["season"] == 2015]["first_pull_median_rem_down1_sec"].iloc[0]),
    "first_pull_median_down1_last": float(S[S["season"] == 2025]["first_pull_median_rem_down1_sec"].iloc[0]),
    "first_pull_mean_down1_2015": float(S[S["season"] == 2015]["first_pull_mean_rem_down1_sec"].iloc[0]),
    "first_pull_mean_down1_last": float(S[S["season"] == 2025]["first_pull_mean_rem_down1_sec"].iloc[0]),
    "first_pull_median_down2_2015": float(S[S["season"] == 2015]["first_pull_median_rem_down2_sec"].iloc[0]),
    "first_pull_median_down2_last": float(S[S["season"] == 2025]["first_pull_median_rem_down2_sec"].iloc[0]),
    "eg_pull_rate_2015_pct": float(S[S["season"] == 2015]["eg_pull_rate_pct"].iloc[0]),
    "eg_pull_rate_last_pct": float(S[S["season"] == 2025]["eg_pull_rate_pct"].iloc[0]),
}

# pull time distribution: share of down-1 pulls earlier than 2:00 / 3:00 remaining
d1 = g[(g["eg_first_diff"] == -1) & g["first_eg_pull_time_rem"].notna()]
early = {}
for s in [2015, 2019, 2025]:
    d = d1[d1["season"] == s]["first_eg_pull_time_rem"]
    early[str(s)] = {
        "n": int(len(d)),
        "pct_before_120s": round(100 * (d >= 120).mean(), 1),
        "pct_before_180s": round(100 * (d >= 180).mean(), 1),
        "median_sec": float(d.median()),
    }
pull_trend["down1_early_pull_share"] = early

# ---------------------------------------------------------------- 4. 6v5 vs PP rates (pooled, full seasons only)
fp = full
pp_t, pp_g = fp["pp_time_sec"].sum(), fp["pp_goals"].sum()
sv_t = fp["sixv5_time_eg"].sum()
sv_gf, sv_ga = fp["sixv5_gf_eg"].sum(), fp["sixv5_ga_eg"].sum()
rates = {
    "pp_gf_per_60_pooled": round(3600 * pp_g / pp_t, 2),
    "sixv5_gf_per_60_pooled": round(3600 * sv_gf / sv_t, 2),
    "sixv5_eng_per_60_pooled": round(3600 * sv_ga / sv_t, 2),
    "sixv5_total_goals_per_60": round(3600 * (sv_gf + sv_ga) / sv_t, 2),
    "pp_goals": int(pp_g), "pp_hours": round(pp_t / 3600, 1),
    "sixv5_hours": round(sv_t / 3600, 1),
    "sixv5_gf": int(sv_gf), "sixv5_ga_eng": int(sv_ga),
    # per-pull outcomes, pooled full seasons, down 1 / down 2 (game-level: all
    # endgame intervals in the game, not just the first pull)
    "down1_pulls": int(len(fp[(fp["eg_first_diff"] == -1)])),
    "down1_tie_rate_pct": round(100 * fp[fp["eg_first_diff"] == -1]["game_pull_tie"].mean(), 1),
    "down1_eng_against_rate_pct": round(100 * fp[fp["eg_first_diff"] == -1]["game_pull_eng"].mean(), 1),
    "down2_pulls": int(len(fp[(fp["eg_first_diff"] == -2)])),
    "down2_tie_rate_pct": round(100 * fp[fp["eg_first_diff"] == -2]["game_pull_tie"].mean(), 1),
    "down2_eng_against_rate_pct": round(100 * fp[fp["eg_first_diff"] == -2]["game_pull_eng"].mean(), 1),
}

# ---------------------------------------------------------------- 5. break-even pull time
# Empirical per-minute rates (pooled full seasons):
#   lam_f = 6v5 goals-for per minute, lam_a = ENG-against per minute (during 6v5)
#   lam_5 = trailing team's 5v5 goals-for per minute. Approx: league 5v5 GF rate
#   per team = (total regulation goals - PP goals - 6v5 goals) / total 5v5
#   team-minutes. 5v5 team-minutes per game ~ 2 teams x (60 - PP min - 6v5 min
#   - ~4 min of 4v4/3v3 allowance).
reg_goals = fp["goals_reg"].sum()
fivev5_goals = reg_goals - pp_g - sv_gf - sv_ga
pp_team_min = pp_t / 60          # one team on PP at a time -> team-minutes
sv_team_min = sv_t / 60          # one team 6v5 at a time
team_min_5v5 = 2 * 60 * len(fp) - pp_team_min - sv_team_min - 4 * len(fp)
lam_5 = fivev5_goals / team_min_5v5
lam_f = sv_gf / (sv_t / 60)   # goals per minute of 6v5 time
lam_a = sv_ga / (sv_t / 60)   # ENGs per minute of 6v5 time

def p_tie_pull(t_min):
    # P(first goal in the 6v5 is a GF, before time expires)
    return (lam_f / (lam_f + lam_a)) * (1 - math.exp(-(lam_f + lam_a) * t_min))

def p_tie_stay(t_min):
    return 1 - math.exp(-lam_5 * t_min)

ts = np.arange(0.25, 15.01, 0.25)
# Pull beats stay for small t (higher scoring rate) but its tie chance saturates
# at lam_f/(lam_f+lam_a), while staying 5v5 keeps climbing. The crossover is
# where staying overtakes pulling: pull wins while fewer than this many minutes
# remain.
crossover = None
for t in ts:
    if p_tie_stay(t) > p_tie_pull(t):
        crossover = float(t)
        break
be_model = {
    "lam_5v5_gf_per_min": round(lam_5, 4),
    "lam_6v5_gf_per_min": round(lam_f, 4),
    "lam_6v5_eng_per_min": round(lam_a, 4),
    "lam_5v5_gf_per_60": round(lam_5 * 60, 2),
    "crossover_pull_minutes": crossover,
    "p_tie_pull_at_2min": round(p_tie_pull(2.0), 3),
    "p_tie_stay_at_2min": round(p_tie_stay(2.0), 3),
    "p_tie_pull_at_5min": round(p_tie_pull(5.0), 3),
    "p_tie_stay_at_5min": round(p_tie_stay(5.0), 3),
    "p_tie_pull_at_crossover": round(p_tie_pull(crossover), 3) if crossover else None,
    "p_tie_stay_at_crossover": round(p_tie_stay(crossover), 3) if crossover else None,
}
# pull outcome by time remaining bucket (down 1, full seasons, game-level outcomes)
d1f = fp[(fp["eg_first_diff"] == -1) & fp["first_eg_pull_time_rem"].notna()].copy()
d1f["bucket"] = pd.cut(d1f["first_eg_pull_time_rem"],
                       [-1, 60, 120, 180, 240, 360, 1200],
                       labels=["<1:00", "1:00-2:00", "2:00-3:00", "3:00-4:00", "4:00-6:00", ">6:00"])
bucket = (d1f.groupby("bucket", observed=True)
          .agg(n=("game_pull_tie", "size"),
               tie_rate=("game_pull_tie", "mean"),
               eng_rate=("game_pull_eng", "mean"))
          .reset_index())
bucket["tie_rate"] = (100 * bucket["tie_rate"]).round(1)
bucket["eng_rate"] = (100 * bucket["eng_rate"]).round(1)
be_model["outcome_by_pull_time_bucket"] = bucket.to_dict("records")

# ---------------------------------------------------------------- 6. XGBoost: predict ENG in a game
# Team quality proxy: season points% computed from the game data itself.
pts = {}
for s, d in g.groupby("season"):
    p = {}
    for _, r in d.iterrows():
        for ab, sc, opp in ((r["home_abbrev"], r["home_score"], r["away_score"]),
                            (r["away_abbrev"], r["away_score"], r["home_score"])):
            w, l, otl = p.get(ab, (0, 0, 0))
            if sc > opp:
                w += 1
            elif r["goals_ot"] > 0 or r["goals_so"] > 0:
                otl += 1
            else:
                l += 1
            p[ab] = (w, l, otl)
    for ab, (w, l, otl) in p.items():
        pts[(s, ab)] = (2 * w + otl) / max(2 * (w + l + otl), 1)

m = g.copy()
m["trail_abbrev"] = np.where(m["score_diff_end3"] > 0, m["away_abbrev"],
                             np.where(m["score_diff_end3"] < 0, m["home_abbrev"], ""))
m["lead_abbrev"] = np.where(m["score_diff_end3"] > 0, m["home_abbrev"],
                            np.where(m["score_diff_end3"] < 0, m["away_abbrev"], ""))
m["trail_is_home"] = (m["score_diff_end3"] < 0).astype(int)
m["abs_diff_end3"] = m["score_diff_end3"].abs()
m["trail_pts_pct"] = [pts.get((s, a), 0.5) for s, a in zip(m["season"], m["trail_abbrev"])]
m["lead_pts_pct"] = [pts.get((s, a), 0.5) for s, a in zip(m["season"], m["lead_abbrev"])]
m["target_eng"] = (m["eng_total"] > 0).astype(int)
sub = m[(m["score_diff_end3"].notna()) & (m["score_diff_end3"] != 0)].copy()
# Game-state features only: season is left out on purpose (the split is by season,
# and the question is what about the game itself predicts an ENG, not the trend).
X = sub[["abs_diff_end3", "trail_is_home", "trail_pts_pct", "lead_pts_pct"]].copy()
X["pts_gap"] = sub["trail_pts_pct"] - sub["lead_pts_pct"]
y = sub["target_eng"]
tr = sub["season"] <= 2022
te = sub["season"] >= 2023
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier
import shap

clf = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05,
                    subsample=0.9, colsample_bytree=0.9, random_state=7,
                    eval_metric="logloss")
clf.fit(X[tr], y[tr])
pred = clf.predict_proba(X[te])[:, 1]
auc = roc_auc_score(y[te], pred)
explainer = shap.TreeExplainer(clf)
sv = explainer.shap_values(X[te])
mean_abs = np.abs(sv).mean(axis=0)
shap_rank = sorted(zip(X.columns, mean_abs.round(4)), key=lambda t: -t[1])
ml = {
    "n_train": int(tr.sum()), "n_test": int(te.sum()),
    "base_rate_test_pct": round(100 * y[te].mean(), 1),
    "auc": round(float(auc), 3),
    "shap_mean_abs": [{"feature": f, "mean_abs_shap": float(v)} for f, v in shap_rank],
    "eng_rate_by_abs_diff": {
        str(k): round(100 * v, 1)
        for k, v in sub.groupby("abs_diff_end3")["target_eng"].mean().items()},
    "eng_rate_home_trail_pct": round(100 * sub[sub["trail_is_home"] == 1]["target_eng"].mean(), 1),
    "eng_rate_away_trail_pct": round(100 * sub[sub["trail_is_home"] == 0]["target_eng"].mean(), 1),
}

# ---------------------------------------------------------------- 7. players + Oilers
pg = players.copy()
top_eng = {}
for s in [2024, 2025]:
    d = pg[pg["season"] == s].sort_values("eng_goals", ascending=False).head(10)
    top_eng[str(s)] = d[["player_name", "goals", "eng_goals"]].to_dict("records")
top_scorers_eng_share = {}
for s in [2024, 2025]:
    d = pg[pg["season"] == s].sort_values("goals", ascending=False).head(10).copy()
    d["eng_share_pct"] = (100 * d["eng_goals"] / d["goals"]).round(1)
    top_scorers_eng_share[str(s)] = d[["player_name", "goals", "eng_goals", "eng_share_pct"]].to_dict("records")
career_eng = (pg.groupby("player_name")[["goals", "eng_goals"]].sum()
              .sort_values("eng_goals", ascending=False).head(15))
career_eng["eng_share_pct"] = (100 * career_eng["eng_goals"] / career_eng["goals"]).round(1)
career_eng = career_eng.reset_index().to_dict("records")

mcdavid = pg[pg["player_name"].str.contains("McDavid", na=False)]
draisaitl = pg[pg["player_name"].str.contains("Draisaitl", na=False)]
matthews = pg[pg["player_name"].str.contains("Matthews", na=False)]
oilers_players = {
    "mcdavid_by_season": mcdavid[["season", "goals", "eng_goals"]].to_dict("records"),
    "mcdavid_career_eng": int(mcdavid["eng_goals"].sum()),
    "mcdavid_career_goals": int(mcdavid["goals"].sum()),
    "draisaitl_by_season": draisaitl[["season", "goals", "eng_goals"]].to_dict("records"),
    "draisaitl_career_eng": int(draisaitl["eng_goals"].sum()),
    "draisaitl_career_goals": int(draisaitl["goals"].sum()),
    "matthews_by_season": matthews[["season", "goals", "eng_goals"]].to_dict("records"),
    "matthews_career_eng": int(matthews["eng_goals"].sum()),
    "matthews_career_goals": int(matthews["goals"].sum()),
}
# Oilers team-level: ENG for/against and pull timing
edm = g[(g["home_abbrev"] == "EDM") | (g["away_abbrev"] == "EDM")].copy()
edm["eng_for"] = np.where(edm["home_abbrev"] == "EDM", edm["eng_by_home"], edm["eng_by_away"])
edm["eng_against"] = np.where(edm["home_abbrev"] == "EDM", edm["eng_by_away"], edm["eng_by_home"])
edm["edm_trailing_pull"] = np.where(
    ((edm["home_abbrev"] == "EDM") & (edm["first_eg_pull_team"] == "home")) |
    ((edm["away_abbrev"] == "EDM") & (edm["first_eg_pull_team"] == "away")),
    edm["first_eg_pull_time_rem"], np.nan)
edm_sum = (edm.groupby("season").agg(games=("game_id", "size"),
                                      eng_for=("eng_for", "sum"),
                                      eng_against=("eng_against", "sum"),
                                      pull_med=("edm_trailing_pull", "median"))
           .reset_index())
edm_sum["label"] = edm_sum["season"].map(SEASON_LABEL)
oilers = {
    "by_season": edm_sum.to_dict("records"),
    "career_eng_for": int(edm["eng_for"].sum()),
    "career_eng_against": int(edm["eng_against"].sum()),
    "career_eng_diff": int(edm["eng_for"].sum() - edm["eng_against"].sum()),
}

results = {
    "games": int(len(g)),
    "seasons": [SEASON_LABEL[s] for s in sorted(g["season"].unique())],
    "season_summary": S.round(3).to_dict("records"),
    "decomposition": decomp,
    "pull_trend": pull_trend,
    "rates": rates,
    "breakeven_model": be_model,
    "ml_eng_prediction": ml,
    "top_eng_scorers": top_eng,
    "top_scorers_eng_share": top_scorers_eng_share,
    "career_eng_leaders": career_eng,
    "players": oilers_players,
    "oilers": oilers,
}
with open(os.path.join(OUT, "analysis_results.json"), "w") as f:
    json.dump(results, f, indent=2)

# ---------------------------------------------------------------- findings.txt
lines = []
lines.append(f"GAMES ANALYZED: {len(g)} regular-season games, "
             f"{SEASON_LABEL[min(g['season'])]} to {SEASON_LABEL[max(g['season'])]}")
lines.append("")
lines.append("== 1. THE SCORING BOOM IS PARTLY AN EMPTY-NET BOOM ==")
lines.append(f"Goals/game: {decomp['gpg_2015_16']} (2015-16) -> {decomp['gpg_last_full']} ({decomp['last_full_label']})")
lines.append(f"ENG/game: {decomp['eng_per_game_2015_16']} -> {decomp['eng_per_game_last_full']}  ({decomp['eng_growth_multiple']}x)")
lines.append(f"ENG share of all goals: {decomp['eng_share_2015_16_pct']}% -> {decomp['eng_share_last_full_pct']}%")
lines.append(f"Non-ENG goals/game: {decomp['non_eng_gpg_2015_16']} -> {decomp['non_eng_gpg_last_full']}")
lines.append(f"Of the +{decomp['gpg_growth_2015_to_last']} goals/game added 2015-16 -> {decomp['last_full_label']}, "
             f"+{decomp['eng_growth_2015_to_last']} were empty-netters "
             f"({decomp['eng_share_of_growth_2015_to_last_pct']}%).")
lines.append("")
lines.append("== 2. COACHES PULL EARLIER EVERY YEAR ==")
lines.append(f"Median first endgame pull, down 1: {pull_trend['first_pull_median_down1_2015']:.0f}s left "
             f"(2015-16) -> {pull_trend['first_pull_median_down1_last']:.0f}s left (2025-26)")
lines.append(f"Mean first endgame pull, down 1: {pull_trend['first_pull_mean_down1_2015']:.0f}s -> "
             f"{pull_trend['first_pull_mean_down1_last']:.0f}s")
lines.append(f"Median first endgame pull, down 2: {pull_trend['first_pull_median_down2_2015']:.0f}s -> "
             f"{pull_trend['first_pull_median_down2_last']:.0f}s")
lines.append(f"Games with an endgame pull: {pull_trend['eg_pull_rate_2015_pct']:.1f}% -> "
             f"{pull_trend['eg_pull_rate_last_pct']:.1f}%")
for s, e in pull_trend["down1_early_pull_share"].items():
    lines.append(f"Down-1 pulls, {s}: n={e['n']}, {e['pct_before_180s']}% pulled with >=3:00 left, "
                 f"{e['pct_before_120s']}% with >=2:00 left, median {e['median_sec']:.0f}s")
lines.append("")
lines.append("== 3. 6-ON-5 vs THE POWER PLAY ==")
lines.append(f"Power play: {rates['pp_gf_per_60_pooled']} goals/60 ({rates['pp_hours']} hours of PP time)")
lines.append(f"6-on-5: {rates['sixv5_gf_per_60_pooled']} goals-for/60, "
             f"{rates['sixv5_eng_per_60_pooled']} ENG-against/60 ({rates['sixv5_hours']} hours)")
lines.append(f"Down 1 pull outcomes (n={rates['down1_pulls']}): tie {rates['down1_tie_rate_pct']}%, "
             f"concede ENG {rates['down1_eng_against_rate_pct']}%")
lines.append(f"Down 2 pull outcomes (n={rates['down2_pulls']}): tie {rates['down2_tie_rate_pct']}%, "
             f"concede ENG {rates['down2_eng_against_rate_pct']}%")
lines.append("")
lines.append("== 4. BREAK-EVEN PULL TIME (Poisson first-goal model) ==")
lines.append(f"5v5 GF rate (trailing team): {be_model['lam_5v5_gf_per_60']} /60")
lines.append(f"6v5 GF rate: {rates['sixv5_gf_per_60_pooled']} /60; ENG-against rate: "
             f"{rates['sixv5_eng_per_60_pooled']} /60")
lines.append(f"Crossover: pulling beats staying 5v5 while under {be_model['crossover_pull_minutes']} min remain")
lines.append(f"P(tie) pulling at 2:00 left: {be_model['p_tie_pull_at_2min']} vs staying 5v5: "
             f"{be_model['p_tie_stay_at_2min']}")
lines.append(f"P(tie) pulling at 5:00 left: {be_model['p_tie_pull_at_5min']} vs staying 5v5: "
             f"{be_model['p_tie_stay_at_5min']}")
lines.append("Outcome by pull time (down 1):")
for b in be_model["outcome_by_pull_time_bucket"]:
    lines.append(f"  {b['bucket']}: n={b['n']}, tie {b['tie_rate']}%, ENG against {b['eng_rate']}%")
lines.append("")
lines.append("== 5. WHAT PREDICTS AN EMPTY-NET GOAL? (XGBoost, train <=2022-23, test >=2023-24) ==")
lines.append(f"AUC {ml['auc']} (test n={ml['n_test']}, base rate {ml['base_rate_test_pct']}%)")
for s in ml["shap_mean_abs"]:
    lines.append(f"  {s['feature']}: mean|SHAP| {s['mean_abs_shap']}")
lines.append(f"ENG rate by deficit entering 3rd: {ml['eng_rate_by_abs_diff']}")
lines.append(f"ENG rate when trailing team is home: {ml['eng_rate_home_trail_pct']}%, away: "
             f"{ml['eng_rate_away_trail_pct']}%")
lines.append("")
lines.append("== 6. THE GOAL RACE HAS EMPTY-NET PADDING ==")
for s, lst in top_scorers_eng_share.items():
    lines.append(f"Top-10 goal scorers {s}:")
    for r in lst:
        lines.append(f"  {r['player_name']}: {r['goals']} goals, {r['eng_goals']} ENG "
                     f"({r['eng_share_pct']}%)")
lines.append("Career ENG leaders (2015-16 to present):")
for r in career_eng[:10]:
    lines.append(f"  {r['player_name']}: {r['eng_goals']} ENG of {r['goals']} goals "
                 f"({r['eng_share_pct']}%)")
lines.append("")
lines.append("== 7. OILERS ==")
lines.append(f"McDavid career: {oilers_players['mcdavid_career_goals']} goals, "
             f"{oilers_players['mcdavid_career_eng']} ENG")
lines.append(f"Draisaitl career: {oilers_players['draisaitl_career_goals']} goals, "
             f"{oilers_players['draisaitl_career_eng']} ENG")
lines.append(f"Matthews career: {oilers_players['matthews_career_goals']} goals, "
             f"{oilers_players['matthews_career_eng']} ENG")
lines.append(f"Oilers ENG for/against since 2015-16: {oilers['career_eng_for']} / "
             f"{oilers['career_eng_against']} (diff {oilers['career_eng_diff']:+d})")
for r in oilers["by_season"]:
    lines.append(f"  {r['label']}: ENG for {int(r['eng_for'])}, against {int(r['eng_against'])}, "
                 f"median pull {r['pull_med']:.0f}s" if pd.notna(r['pull_med']) else
                 f"  {r['label']}: ENG for {int(r['eng_for'])}, against {int(r['eng_against'])}")
with open(os.path.join(OUT, "findings.txt"), "w") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
print("\nWrote analysis_results.json, findings.txt, data/season_summary.csv")
