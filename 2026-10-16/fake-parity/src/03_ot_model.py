"""What sends a game to overtime? A chronological, leak-free model.

Every feature is computed from games played BEFORE the game in question
(season-to-date points%, OT rate, rest days, and each team's distance to its
conference playoff cutline going into the night). Train on 2013-14..2021-22,
test on 2022-23..2024-25. XGBoost + SHAP, with a logistic-regression baseline.

The behavioural question underneath: the loser point pays both teams to
reach overtime tied. If that incentive bites, games between two bubble teams
-- and games where a tie late is worth more than a win gamble -- should reach
OT more often than team strength alone predicts, especially late in the
season and especially across conferences, where the extra point you hand
your opponent costs you nothing in the standings race.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent


def build_features(games, meta):
    games = games.sort_values(["date", "game_id"]).reset_index(drop=True)
    m = meta.set_index(["season", "team"])
    state = {}   # (season, team) -> dict of season-to-date counters
    last_date = {}
    rows = []
    for date, day in games.groupby("date"):
        season = day.season.iloc[0]
        # conference cutline (8th-best points%) from state before today's games
        conf_pct = {}
        for (s, team), st in state.items():
            if s != season or st["gp"] == 0:
                continue
            conf = m.loc[(s, team), "conference"]
            conf_pct.setdefault(conf, []).append((team, st["pts"] / (2 * st["gp"])))
        cutline = {}
        for conf, lst in conf_pct.items():
            pcts = sorted([p for _, p in lst], reverse=True)
            cutline[conf] = pcts[7] if len(pcts) >= 8 else 0.5

        for _, g in day.iterrows():
            feats = {"game_id": g.game_id, "season": g.season, "date": g.date,
                     "went_ot": g.went_ot, "went_so": g.went_so}
            dists = []
            for side in ("home", "away"):
                team = g[side]
                st = state.get((season, team), {"gp": 0, "pts": 0, "ot": 0})
                pct = st["pts"] / (2 * st["gp"]) if st["gp"] else 0.5
                conf = m.loc[(season, team), "conference"]
                div = m.loc[(season, team), "division"]
                rest = (pd.Timestamp(date) - last_date[(season, team)]).days \
                    if (season, team) in last_date else 4
                feats[f"{side}_pct"] = pct
                feats[f"{side}_ot_rate"] = st["ot"] / st["gp"] if st["gp"] else 0.23
                feats[f"{side}_rest"] = min(rest, 10)
                feats[f"{side}_gp"] = st["gp"]
                feats[f"{side}_dist_cut"] = pct - cutline.get(conf, 0.5)
                feats[f"{side}_conf"] = conf
                feats[f"{side}_div"] = div
                dists.append(feats[f"{side}_dist_cut"])
            feats["pct_diff"] = feats["home_pct"] - feats["away_pct"]
            feats["abs_pct_diff"] = abs(feats["pct_diff"])
            feats["min_pct"] = min(feats["home_pct"], feats["away_pct"])
            feats["both_bubble"] = int(
                abs(dists[0]) <= 0.05 and abs(dists[1]) <= 0.05)
            feats["one_longshot"] = int(min(dists) < -0.10)
            feats["divisional"] = int(feats["home_div"] == feats["away_div"])
            feats["same_conf"] = int(feats["home_conf"] == feats["away_conf"])
            feats["inter_conf"] = 1 - feats["same_conf"]
            d = pd.Timestamp(date)
            feats["month"] = d.month
            feats["late_season"] = int(d.month >= 3)
            feats["season_progress"] = (feats["home_gp"] + feats["away_gp"]) / 164.0
            rows.append(feats)
        # update state after the whole day's games (no same-day leakage)
        for _, g in day.iterrows():
            for team, is_home in ((g.home, True), (g.away, False)):
                st = state.setdefault((g.season, team), {"gp": 0, "pts": 0, "ot": 0})
                st["gp"] += 1
                st["ot"] += int(g.went_ot)
                won = g.winner == team
                st["pts"] += 2 if won else (1 if g.went_ot else 0)
                last_date[(g.season, team)] = pd.Timestamp(g.date)
    return pd.DataFrame(rows)


def main():
    games = pd.read_csv(ROOT / "data" / "games.csv")
    meta = pd.read_csv(ROOT / "data" / "standings_final.csv")
    df = build_features(games, meta)
    df.to_csv(ROOT / "data" / "ot_features.csv", index=False)

    feats = ["home_pct", "away_pct", "abs_pct_diff", "home_ot_rate", "away_ot_rate",
             "home_rest", "away_rest", "home_gp", "both_bubble", "one_longshot",
             "divisional", "inter_conf", "late_season", "season_progress",
             "home_dist_cut", "away_dist_cut"]
    train = df[df.season <= 20212022]
    test = df[df.season >= 20222023]

    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    lr.fit(train[feats], train.went_ot)
    auc_lr = roc_auc_score(test.went_ot, lr.predict_proba(test[feats])[:, 1])

    model = xgb.XGBClassifier(
        n_estimators=400, max_depth=3, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.9, eval_metric="logloss",
        random_state=7)
    model.fit(train[feats], train.went_ot)
    auc_xgb = roc_auc_score(test.went_ot, model.predict_proba(test[feats])[:, 1])

    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(test[feats])
    shap_df = pd.DataFrame({
        "feature": feats,
        "mean_abs_shap": np.abs(sv).mean(axis=0),
    }).sort_values("mean_abs_shap", ascending=False)
    shap_df.to_csv(ROOT / "data" / "shap_ot.csv", index=False)

    # conditional OT rates -- the behavioural cuts for the write-up
    cuts = {
        "overall": df.went_ot.mean(),
        "divisional": df[df.divisional == 1].went_ot.mean(),
        "intra_conf_nondiv": df[(df.same_conf == 1) & (df.divisional == 0)].went_ot.mean(),
        "inter_conf": df[df.inter_conf == 1].went_ot.mean(),
        "both_bubble": df[df.both_bubble == 1].went_ot.mean(),
        "not_both_bubble": df[df.both_bubble == 0].went_ot.mean(),
        "late_season": df[df.late_season == 1].went_ot.mean(),
        "early_season": df[df.season_progress < 0.25].went_ot.mean(),
        "late_both_bubble": df[(df.late_season == 1) & (df.both_bubble == 1)].went_ot.mean(),
        "late_inter_conf": df[(df.late_season == 1) & (df.inter_conf == 1)].went_ot.mean(),
        "mismatch_absdiff_gt_015": df[df.abs_pct_diff > 0.15].went_ot.mean(),
        "close_absdiff_lt_005": df[df.abs_pct_diff < 0.05].went_ot.mean(),
    }
    counts = {
        "late_both_bubble_n": int(((df.late_season == 1) & (df.both_bubble == 1)).sum()),
        "both_bubble_n": int((df.both_bubble == 1).sum()),
        "inter_conf_n": int((df.inter_conf == 1).sum()),
    }
    findings = {
        "auc_logreg_test": round(float(auc_lr), 3),
        "auc_xgboost_test": round(float(auc_xgb), 3),
        "train_games": int(len(train)), "test_games": int(len(test)),
        "conditional_ot_rates": {k: round(float(v), 4) for k, v in cuts.items()},
        "counts": counts,
        "shap_top": shap_df.head(8).to_dict("records"),
    }
    (ROOT / "data" / "findings_model.json").write_text(json.dumps(findings, indent=1))
    print(json.dumps(findings, indent=1))


if __name__ == "__main__":
    main()
