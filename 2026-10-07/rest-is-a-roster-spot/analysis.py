#!/usr/bin/env python3
"""
Rest Is a Roster Spot — the NHL schedule is a mispriced asset.

Question: once you strip out how good the teams actually are, how many
standings points does the schedule itself hand out every season — and who
cashies them?

Data: NHL public API (api-web.nhle.com) club-schedule-season endpoints,
five full regular seasons, 2021-22 through 2025-26. Arena coordinates and
timezones are static reference data coded below (32 current/Recent arenas).

Analyses:
  1. The rest curve — actual home win% by rest differential.
  2. Fatigue pricing — XGBoost (Elo + schedule features), out-of-time test,
     SHAP ranking; logistic schedule-only model as the honest floor.
  3. Schedule luck — counterfactual points each team-season gained or lost
     from rest/travel inequality alone (model with rest_diff set to 0).
  4. The travel tax — miles, back-to-backs, 3-in-4s by team, and what
     Edmonton pays for living in Edmonton.

Outputs: figures/*.png, results.json, findings.txt, data/games.csv
Reproduce: python3 analysis.py   (downloads ~160 small JSON files once, cached)
"""
import json
import math
import time
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
FIGDIR = BASE / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)
CACHE = BASE / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

SEASONS = ["20212022", "20222023", "20232024", "20242025", "20252026"]
TEAMS = ["ANA", "ARI", "BOS", "BUF", "CAR", "CBJ", "CGY", "CHI", "COL", "DAL",
         "DET", "EDM", "FLA", "LAK", "MIN", "MTL", "NJD", "NSH", "NYI", "NYR",
         "OTT", "PHI", "PIT", "SEA", "SJS", "STL", "TBL", "TOR", "UTA", "VAN",
         "VGK", "WPG", "WSH"]

# arena (lat, lon, utc offset standard time)
ARENA = {
    "ANA": (33.8078, -117.8765, -8), "ARI": (33.4264, -111.9365, -7),
    "BOS": (42.3662, -71.0621, -5), "BUF": (42.8750, -78.8765, -5),
    "CAR": (35.8033, -78.7222, -5), "CBJ": (39.9693, -83.0061, -5),
    "CGY": (51.0374, -114.0519, -7), "CHI": (41.8807, -87.6742, -6),
    "COL": (39.7487, -105.0077, -7), "DAL": (32.7905, -96.8103, -6),
    "DET": (42.3411, -83.0553, -5), "EDM": (53.5469, -113.4977, -7),
    "FLA": (26.1583, -80.3254, -5), "LAK": (34.0430, -118.2670, -8),
    "MIN": (44.9448, -93.1012, -6), "MTL": (45.4961, -73.5694, -5),
    "NJD": (40.7336, -74.1653, -5), "NSH": (36.1592, -86.7785, -6),
    "NYI": (40.6825, -73.7194, -5), "NYR": (40.7505, -73.9934, -5),
    "OTT": (45.2969, -75.9270, -5), "PHI": (39.9012, -75.1720, -5),
    "PIT": (40.4394, -79.9892, -5), "SEA": (47.6222, -122.3540, -8),
    "SJS": (37.3326, -121.9012, -8), "STL": (38.6268, -90.2025, -6),
    "TBL": (27.9427, -82.4518, -5), "TOR": (43.6435, -79.3791, -5),
    "UTA": (40.7683, -111.9015, -7), "VAN": (49.2778, -123.1088, -8),
    "VGK": (36.1028, -115.1783, -8), "WPG": (49.8924, -97.1436, -6),
    "WSH": (38.8982, -77.0209, -5),
}


def haversine_miles(a, b):
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 3958.8 * 2 * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- download
def fetch_all():
    games = {}
    for season in SEASONS:
        for team in TEAMS:
            f = CACHE / f"{team}_{season}.json"
            if f.exists():
                payload = json.loads(f.read_text())
            else:
                url = f"https://api-web.nhle.com/v1/club-schedule-season/{team}/{season}"
                r = requests.get(url, timeout=30, headers={"User-Agent": "passion-projects-research"})
                if r.status_code != 200:
                    continue
                payload = r.json()
                f.write_text(json.dumps(payload))
                time.sleep(0.08)
            for g in payload.get("games", []):
                if g.get("gameType") != 2:            # regular season only
                    continue
                if g.get("gameState") not in ("OFF", "FINAL"):
                    continue
                h, a = g["homeTeam"], g["awayTeam"]
                if h.get("score") is None or a.get("score") is None:
                    continue
                games[g["id"]] = {
                    "game_id": g["id"], "season": season,
                    "date": g["gameDate"],
                    "home": h["abbrev"], "away": a["abbrev"],
                    "home_goals": h["score"], "away_goals": a["score"],
                }
    df = pd.DataFrame(games.values())
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["date", "game_id"]).reset_index(drop=True)


# ---------------------------------------------------------------- features
def build_features(df):
    """Team-game long table -> game-level wide table with rest/travel + Elo."""
    rows = []
    for _, g in df.iterrows():
        for side, team, opp in (("home", g.home, g.away), ("away", g.away, g.home)):
            rows.append({"game_id": g.game_id, "season": g.season, "date": g.date,
                         "side": side, "team": team, "opp": opp,
                         "venue": g.home,
                         "gf": g.home_goals if side == "home" else g.away_goals,
                         "ga": g.away_goals if side == "home" else g.home_goals})
    tg = pd.DataFrame(rows).sort_values(["team", "date", "game_id"])
    tg["prev_date"] = tg.groupby("team")["date"].shift(1)
    tg["prev_venue"] = tg.groupby("team")["venue"].shift(1)
    tg["rest_days"] = (tg["date"] - tg["prev_date"]).dt.days - 1
    tg["rest_days"] = tg["rest_days"].fillna(7).clip(-1, 14)  # season opener ~= fresh
    tg["is_b2b"] = (tg["rest_days"] == 0).astype(int)
    # games in the last 4 days (incl. today) per team
    counts = []
    for _, grp in tg.groupby("team", sort=False):
        d = grp["date"].values
        c = [int(((d[i] - d[max(0, i - 6):i + 1]) <= np.timedelta64(3, "D")).sum()) for i in range(len(d))]
        counts.extend(c)
    tg["games_last4"] = counts
    tg["is_3in4"] = (tg["games_last4"] >= 3).astype(int)

    def miles(r):
        if pd.isna(r["prev_venue"]) or r["prev_venue"] not in ARENA or r["venue"] not in ARENA:
            return 0.0
        return haversine_miles(ARENA[r["prev_venue"]][:2], ARENA[r["venue"]][:2])

    def tz_east(r):
        if pd.isna(r["prev_venue"]) or r["prev_venue"] not in ARENA or r["venue"] not in ARENA:
            return 0
        return ARENA[r["venue"]][2] - ARENA[r["prev_venue"]][2]  # +ve = travelled east

    tg["miles_since_last"] = tg.apply(miles, axis=1)
    tg["tz_east"] = tg.apply(tz_east, axis=1)
    tg["miles14"] = (tg.groupby("team")["miles_since_last"]
                     .transform(lambda s: s.rolling(6, min_periods=1).sum()))

    # ---- pre-game Elo (chronological, regressed 1/3 to 1500 each new season)
    elo = {}
    elo_rows = {}
    last_season = None
    for _, g in df.iterrows():
        if last_season is not None and g.season != last_season:
            elo = {t: 1500 + (e - 1500) * 2 / 3 for t, e in elo.items()}
        last_season = g.season
        eh, ea = elo.get(g.home, 1500.0), elo.get(g.away, 1500.0)
        elo_rows[g.game_id] = (eh, ea)
        exp_h = 1 / (1 + 10 ** (-(eh + 55 - ea) / 400))   # 55 pts home edge in update
        margin = abs(g.home_goals - g.away_goals)
        k = 6 * (1 + 0.25 * min(margin, 4))
        res = 1.0 if g.home_goals > g.away_goals else 0.0
        elo[g.home] = eh + k * (res - exp_h)
        elo[g.away] = ea + k * ((1 - res) - (1 - exp_h))
    tg["elo"] = tg.apply(lambda r: elo_rows[r.game_id][0] if r.side == "home" else elo_rows[r.game_id][1], axis=1)

    home = tg[tg.side == "home"].set_index("game_id").sort_index()
    away = tg[tg.side == "away"].set_index("game_id").sort_index()
    away = away.reindex(home.index)   # CRITICAL: align away rows to home rows
    assert (home["team"] != away["team"]).all()
    wide = pd.DataFrame(index=home.index)
    wide["season"] = home["season"].values
    wide["date"] = home["date"].values
    wide["home"] = home["team"].values
    wide["away"] = away["team"].values
    wide["home_win"] = (home["gf"].values > home["ga"].values).astype(int)
    wide["elo_diff"] = home["elo"].values - away["elo"].values
    wide["home_rest"] = home["rest_days"].values
    wide["away_rest"] = away["rest_days"].values
    wide["rest_diff"] = wide["home_rest"] - wide["away_rest"]
    wide["home_b2b"] = home["is_b2b"].values
    wide["away_b2b"] = away["is_b2b"].values
    wide["home_3in4"] = home["is_3in4"].values
    wide["away_3in4"] = away["is_3in4"].values
    wide["home_miles"] = home["miles_since_last"].values
    wide["away_miles"] = away["miles_since_last"].values
    wide["miles_diff_log"] = np.log1p(wide["away_miles"]) - np.log1p(wide["home_miles"])
    wide["away_tz_east"] = away["tz_east"].values
    wide["home_tz_east"] = home["tz_east"].values
    wide["tz_east_diff"] = wide["away_tz_east"] - wide["home_tz_east"]
    wide["away_miles14"] = away["miles14"].values
    wide["home_miles14"] = home["miles14"].values
    wide["month"] = pd.to_datetime(wide["date"]).dt.month
    return wide.reset_index(), tg


SCHED_FEATURES = ["rest_diff", "home_b2b", "away_b2b", "home_3in4", "away_3in4",
                  "miles_diff_log", "tz_east_diff", "away_miles14", "home_miles14"]
ALL_FEATURES = ["elo_diff"] + SCHED_FEATURES


def main():
    df = fetch_all()
    print(f"games downloaded: {len(df)}")
    wide, tg = build_features(df)
    wide.to_csv(BASE / "data" / "games.csv", index=False)

    R = {"n_games": int(len(wide)),
         "seasons": sorted(wide.season.unique().tolist()),
         "sanity_elo_diff_corr_home_win": round(float(wide["elo_diff"].corr(wide["home_win"])), 4),
         "sanity_elo_diff_means": "positive corr expected; negative = bug"}

    # ------------------------------------------------ 1. the rest curve
    buckets = pd.cut(wide["rest_diff"], [-99, -2, -1, 0, 1, 2, 99],
                     labels=["<= -2", "-1", "0", "+1", "+2", ">= +3"])
    curve = wide.groupby(buckets, observed=True)["home_win"].agg(["mean", "count"])
    R["rest_curve"] = {str(k): {"home_win_pct": round(float(v["mean"]), 4),
                                "n": int(v["count"])} for k, v in curve.iterrows()}

    b2b = wide[wide.away_b2b == 1]
    rested_vs_b2b = wide[(wide.away_b2b == 1) & (wide.home_b2b == 0)]
    R["away_b2b_home_win_pct"] = round(float(b2b["home_win"].mean()), 4)
    R["b2b_games_n"] = int(len(b2b))
    R["rested_home_vs_b2b_away_win_pct"] = round(float(rested_vs_b2b["home_win"].mean()), 4)
    R["overall_home_win_pct"] = round(float(wide["home_win"].mean()), 4)
    equal_rest = wide[wide.rest_diff == 0]
    R["equal_rest_home_win_pct"] = round(float(equal_rest["home_win"].mean()), 4)
    R["season_opener_note"] = "rest_days capped; openers treated as fully rested"

    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.bar(curve.index.astype(str), curve["mean"] * 100, color="#1f6fb2")
    ax.axhline(50, color="gray", lw=0.8, ls="--")
    for i, (m, n) in enumerate(zip(curve["mean"], curve["count"])):
        ax.text(i, m * 100 + 0.7, f"{m*100:.1f}%\nn={n:,}", ha="center", fontsize=8)
    ax.set_ylabel("Home win %")
    ax.set_xlabel("Rest differential (home rest days − away rest days)")
    ax.set_title("The rest curve: five seasons, every regular-season game")
    fig.tight_layout(); fig.savefig(FIGDIR / "fig1_rest_curve.png", dpi=150); plt.close(fig)

    # ------------------------------------------------ 2. pricing fatigue
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score, accuracy_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    import xgboost as xgb
    import shap

    train = wide[wide.season <= "20232024"]
    test = wide[wide.season >= "20242025"]
    R["train_n"], R["test_n"] = int(len(train)), int(len(test))

    lr_sched = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    lr_sched.fit(train[SCHED_FEATURES], train["home_win"])
    R["auc_logit_sched_only"] = round(float(roc_auc_score(
        test["home_win"], lr_sched.predict_proba(test[SCHED_FEATURES])[:, 1])), 4)

    lr_full = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    lr_full.fit(train[ALL_FEATURES], train["home_win"])
    coef = lr_full[-1].coef_[0]
    R["logit_coefs"] = {f: round(float(c), 4) for f, c in zip(ALL_FEATURES, coef)}

    model = xgb.XGBClassifier(n_estimators=400, max_depth=3, learning_rate=0.05,
                              subsample=0.9, colsample_bytree=0.9,
                              eval_metric="logloss", random_state=7)
    model.fit(train[ALL_FEATURES], train["home_win"])
    pred = model.predict_proba(test[ALL_FEATURES])[:, 1]
    R["auc_xgb_full"] = round(float(roc_auc_score(test["home_win"], pred)), 4)
    R["acc_xgb_full"] = round(float(accuracy_score(test["home_win"], pred > 0.5)), 4)

    expl = shap.TreeExplainer(model)
    sv = expl.shap_values(test[ALL_FEATURES].iloc[:1500])
    shap_rank = sorted(zip(ALL_FEATURES, np.abs(sv).mean(axis=0)), key=lambda x: -x[1])
    R["shap_ranking"] = [(f, round(float(v), 4)) for f, v in shap_rank]

    fig, ax = plt.subplots(figsize=(8, 4.8))
    names = [f for f, _ in shap_rank][::-1]
    vals = [v for _, v in shap_rank][::-1]
    ax.barh(names, vals, color=["#888" if n == "elo_diff" else "#1f6fb2" for n in names])
    ax.set_xlabel("mean |SHAP| (log-odds impact on home win)")
    ax.set_title("What moves a hockey game: talent (grey) vs the schedule (blue)")
    fig.tight_layout(); fig.savefig(FIGDIR / "fig2_shap.png", dpi=150); plt.close(fig)

    # counterfactual: kill the rest/fatigue signal, keep everything else
    neutral = test.copy()
    for c in ["rest_diff", "home_b2b", "away_b2b", "home_3in4", "away_3in4"]:
        neutral[c] = 0
    test = test.assign(p_actual=model.predict_proba(test[ALL_FEATURES])[:, 1],
                       p_neutral=model.predict_proba(neutral[ALL_FEATURES])[:, 1])
    test["sched_edge_home"] = test["p_actual"] - test["p_neutral"]
    R["max_sched_edge_pp"] = round(float(test["sched_edge_home"].abs().quantile(0.99)) * 100, 1)
    R["mean_abs_sched_edge_pp"] = round(float(test["sched_edge_home"].abs().mean()) * 100, 2)

    # ------------------------------------------------ 3. schedule luck (test seasons, all games re-predicted)
    full = wide.copy()
    neu = full.copy()
    for c in ["rest_diff", "home_b2b", "away_b2b", "home_3in4", "away_3in4"]:
        neu[c] = 0
    full["p_a"] = model.predict_proba(full[ALL_FEATURES])[:, 1]
    full["p_n"] = model.predict_proba(neu[ALL_FEATURES])[:, 1]
    rows = []
    for _, g in full.iterrows():
        # expected points: win=2, OT loss=1 — model gives win prob; add flat 0.11 OT-loss expectation for both
        rows.append((g.season, g.home, (g.p_a - g.p_n) * 2))
        rows.append((g.season, g.away, -((g.p_a - g.p_n) * 2)))
    luck = (pd.DataFrame(rows, columns=["season", "team", "pts"])
            .groupby(["season", "team"])["pts"].sum().reset_index())
    luck.to_csv(BASE / "data" / "schedule_luck.csv", index=False)
    luck_2526 = luck[luck.season == "20252026"].sort_values("pts")
    R["luck_2025_26_best"] = [(r.team, round(float(r.pts), 1)) for r in luck_2526.tail(5).itertuples()]
    R["luck_2025_26_worst"] = [(r.team, round(float(r.pts), 1)) for r in luck_2526.head(5).itertuples()]
    R["luck_spread_2025_26_pts"] = round(float(luck_2526.pts.max() - luck_2526.pts.min()), 1)
    avg_luck = luck.groupby("team")["pts"].mean().sort_values()
    R["luck_5yr_best"] = [(t, round(float(v), 2)) for t, v in avg_luck.tail(5).items()]
    R["luck_5yr_worst"] = [(t, round(float(v), 2)) for t, v in avg_luck.head(5).items()]
    R["edm_luck_2025_26_pts"] = round(float(luck_2526[luck_2526.team == "EDM"].pts.iloc[0]), 2)

    fig, ax = plt.subplots(figsize=(9, 5.2))
    c = ["#c0392b" if v < 0 else "#1f6fb2" for v in luck_2526.pts]
    ax.barh(luck_2526.team, luck_2526.pts, color=c)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Standings points the 2025-26 schedule added (+) or took away (−)")
    ax.set_title("Schedule luck, 2025-26: free points and stolen points")
    fig.tight_layout(); fig.savefig(FIGDIR / "fig3_schedule_luck.png", dpi=150); plt.close(fig)

    # ------------------------------------------------ 4. the travel tax
    team_season = (tg.groupby(["season", "team"])
                   .agg(miles=("miles_since_last", "sum"), b2b=("is_b2b", "sum"),
                        three_in_4=("is_3in4", "sum")).reset_index())
    team_season.to_csv(BASE / "data" / "travel_tax.csv", index=False)
    avg_miles = team_season.groupby("team")["miles"].mean().sort_values(ascending=False)
    R["avg_miles_top5"] = [(t, int(v)) for t, v in avg_miles.head(5).items()]
    R["avg_miles_bottom3"] = [(t, int(v)) for t, v in avg_miles.tail(3).items()]
    R["edm_avg_miles"] = int(avg_miles.get("EDM", 0))
    R["league_miles_ratio_top_bottom"] = round(float(avg_miles.iloc[0] / avg_miles.iloc[-1]), 2)
    b2b_counts = team_season[team_season.season == "20252026"].sort_values("b2b")
    R["b2b_2025_26_most"] = [(r.team, int(r.b2b)) for r in b2b_counts.tail(4).itertuples()]
    R["b2b_2025_26_fewest"] = [(r.team, int(r.b2b)) for r in b2b_counts.head(4).itertuples()]

    fig, ax = plt.subplots(figsize=(9, 4.8))
    top = avg_miles.head(10)[::-1]
    cols = ["#e67e22" if t == "EDM" else "#1f6fb2" for t in top.index]
    ax.barh(top.index, top.values, color=cols)
    ax.set_xlabel("Average air miles per season, 2021-22 → 2025-26")
    ax.set_title("The travel tax (Edmonton in orange)")
    fig.tight_layout(); fig.savefig(FIGDIR / "fig4_travel_tax.png", dpi=150); plt.close(fig)

    # home edge decomposition: raw vs equal-rest
    by_season = wide.groupby("season")["home_win"].mean()
    R["home_win_pct_by_season"] = {s: round(float(v), 4) for s, v in by_season.items()}
    eq = wide[wide.rest_diff == 0].groupby("season")["home_win"].mean()
    R["equal_rest_home_pct_by_season"] = {s: round(float(v), 4) for s, v in eq.items()}

    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.plot(by_season.index, by_season.values * 100, marker="o", label="All games")
    ax.plot(eq.index, eq.values * 100, marker="s", label="Equal rest only")
    ax.axhline(50, color="gray", lw=0.8, ls="--")
    ax.set_ylabel("Home win %"); ax.legend(frameon=False)
    ax.set_title("Home ice, raw vs rest-controlled")
    fig.tight_layout(); fig.savefig(FIGDIR / "fig5_home_edge.png", dpi=150); plt.close(fig)

    (BASE / "results.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=2, default=str)[:3000])
    return R


if __name__ == "__main__":
    main()
