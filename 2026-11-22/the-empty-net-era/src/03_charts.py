#!/usr/bin/env python3
"""Charts for The Empty-Net Era (build #76).

Reads data/season_summary.csv, analysis_results.json, data/game_features.csv,
data/player_goals.csv.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "..", "data")
CH = os.path.join(BASE, "..", "charts")
os.makedirs(CH, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "-",
    "axes.axisbelow": True, "figure.dpi": 150,
})
NAVY = "#1F3864"
ORANGE = "#D9481C"
BLUE = "#2E5E8C"
GREEN = "#2E7D4F"
GREY = "#6B7280"
LIGHT = "#9CA3AF"

S = pd.read_csv(os.path.join(DATA, "season_summary.csv"))
with open(os.path.join(BASE, "..", "analysis_results.json")) as f:
    R = json.load(f)
FULL = S[~S["season"].isin([2019, 2020, 2026])]  # exclude shortened / in-progress


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(CH, name), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def season_labels(df):
    return df["label"].tolist()


# 1. GPG decomposition: total vs non-ENG goals per game
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(S))
ax.fill_between(x, S["non_eng_gpg"], S["gpg"], color=ORANGE, alpha=0.35,
                label="Empty-net goals")
ax.plot(x, S["gpg"], color=NAVY, lw=2.4, marker="o", ms=4, label="All goals")
ax.plot(x, S["non_eng_gpg"], color=BLUE, lw=2.2, marker="o", ms=4,
        label="Goals with a goalie in net")
ax.set_xticks(x, season_labels(S), rotation=45, ha="right")
ax.set_ylabel("Goals per game")
ax.set_title("Only a tenth of the scoring boom is empty nets (NHL, 2015-16 to 2026-27)", loc="left")
ax.legend(frameon=False, fontsize=10, loc="upper left")
ax.set_ylim(5.0, 6.6)
ax.annotate("ENGs: 0.30 -> 0.39\nper game (1.29x)",
            xy=(9, S["gpg"].iloc[9]), xytext=(5.6, 6.42),
            arrowprops=dict(arrowstyle="->", color=ORANGE), fontsize=10, color=ORANGE)
save(fig, "01_gpg_decomposition.png")

# 2. ENG per game + share of goals
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(x, S["eng_per_game"], color=ORANGE, alpha=0.85, label="Empty-net goals per game")
ax.set_xticks(x, season_labels(S), rotation=45, ha="right")
ax.set_ylabel("Empty-net goals per game")
ax2 = ax.twinx()
ax2.plot(x, S["eng_share_pct"], color=NAVY, lw=2.4, marker="o", ms=4,
         label="Share of all goals")
ax2.set_ylabel("Empty-net goals as % of all goals")
ax2.spines["top"].set_visible(False)
ax.set_title("One goal in nine is now scored into an empty net", loc="left")
ax.set_ylim(0, 0.42)
ax2.set_ylim(0, 14)
save(fig, "02_eng_share.png")

# 3. Pull timing trend (down 1 / down 2), minutes remaining
fig, ax = plt.subplots(figsize=(9, 5))
xf3 = np.arange(len(FULL))
ax.plot(xf3, FULL["first_pull_median_rem_down1_sec"] / 60, color=NAVY, lw=2.4,
        marker="o", ms=4, label="Down 1 goal (median)")
ax.plot(xf3, FULL["first_pull_median_rem_down2_sec"] / 60, color=ORANGE, lw=2.4,
        marker="o", ms=4, label="Down 2 goals (median)")
ax.set_xticks(xf3, season_labels(FULL), rotation=45, ha="right")
ax.set_ylabel("Minutes remaining at first goalie pull")
ax.set_title("Coaches pull the goalie earlier every year", loc="left")
ax.legend(frameon=False, fontsize=10, loc="upper left")
ax.set_ylim(0, 4.2)
save(fig, "03_pull_timing.png")

# 4. 6v5 vs power play scoring rates by season
fig, ax = plt.subplots(figsize=(9, 5))
w = 0.38
xf = np.arange(len(FULL))
ax.bar(xf - w / 2, FULL["pp_gf_per_60"], w, label="Power play (5v4/5v3)", color=BLUE)
ax.bar(xf + w / 2, FULL["sixv5_gf_per_60"], w, label="6-on-5 (goalie pulled)", color=ORANGE)
ax.set_xticks(xf, season_labels(FULL), rotation=45, ha="right")
ax.set_ylabel("Goals scored per 60 minutes")
ax.set_title("6-on-5 scores faster than a power play", loc="left")
ax.legend(frameon=False, fontsize=10, loc="upper left")
save(fig, "04_sixv5_vs_pp.png")

# 5. Break-even pull time: model curves + observed tie rates by pull-time bucket
be = R["breakeven_model"]
lam_f = be["lam_6v5_gf_per_min"]
lam_a = be["lam_6v5_eng_per_min"]
lam_5 = be["lam_5v5_gf_per_min"]
t = np.linspace(0.25, 10, 200)
p_pull = (lam_f / (lam_f + lam_a)) * (1 - np.exp(-(lam_f + lam_a) * t))
p_stay = 1 - np.exp(-lam_5 * t)
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(t, 100 * p_pull, color=ORANGE, lw=2.4, label="Pull the goalie (6-on-5)")
ax.plot(t, 100 * p_stay, color=NAVY, lw=2.4, label="Stay 5-on-5")
ax.axvline(be["crossover_pull_minutes"], color=GREY, ls="--", lw=1.5)
ax.annotate(f"Crossover: {be['crossover_pull_minutes']:.2f} min left",
            xy=(be["crossover_pull_minutes"], 100 * p_pull[np.argmin(abs(t - be["crossover_pull_minutes"]))]),
            xytext=(be["crossover_pull_minutes"] + 0.6, 12),
            arrowprops=dict(arrowstyle="->", color=GREY), fontsize=10)
ax.set_xlabel("Minutes remaining when the goalie is pulled (down 1 goal)")
ax.set_ylabel("Chance of tying the game (%)")
ax.set_title("Pulling beats staying 5-on-5 much earlier than coaches do it", loc="left")
ax.legend(frameon=False, fontsize=10, loc="upper left")
ax.set_xlim(0, 10)
save(fig, "05_breakeven.png")

# 6. SHAP importances for ENG prediction
sh = R["ml_eng_prediction"]["shap_mean_abs"]
names = [s["feature"] for s in sh][::-1]
vals = [s["mean_abs_shap"] for s in sh][::-1]
labels = {"abs_diff_end3": "Goal deficit entering 3rd",
          "trail_is_home": "Trailing team is home",
          "trail_pts_pct": "Trailing team's points %",
          "lead_pts_pct": "Leading team's points %",
          "pts_gap": "Points-% gap (trail minus lead)",
          "season": "Season"}
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.barh(names, vals, color=NAVY)
ax.set_yticks(range(len(names)), [labels.get(n, n) for n in names])
ax.set_xlabel("Mean |SHAP value| (impact on P(empty-net goal))")
ax.set_title(f"What predicts an empty-net goal? (XGBoost, test AUC {R['ml_eng_prediction']['auc']})",
             loc="left")
save(fig, "06_shap.png")

# 7. ENG padding among top-10 goal scorers, 2024-25
pg = pd.read_csv(os.path.join(DATA, "player_goals.csv"))
top = (pg[pg["season"] == 2025].sort_values("goals", ascending=False).head(10)
       .sort_values("goals"))
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(top["player_name"], top["goals"] - top["eng_goals"], color=BLUE,
        label="Goals with a goalie in net")
ax.barh(top["player_name"], top["eng_goals"], left=top["goals"] - top["eng_goals"],
        color=ORANGE, label="Empty-net goals")
for i, (_, r) in enumerate(top.iterrows()):
    ax.text(r["goals"] + 0.6, i, f"{int(r['goals'])} ({int(r['eng_goals'])} ENG)",
            va="center", fontsize=10)
ax.set_xlabel("Goals, 2025-26 regular season")
ax.set_title("The goal race has empty-net padding (top 10 scorers, 2025-26)", loc="left")
ax.legend(frameon=False, fontsize=10, loc="lower right")
ax.set_xlim(0, 60)
save(fig, "07_eng_padding.png")

# 8. Pull outcome by pull time (down 1): tie rate vs ENG-against rate
b = pd.DataFrame(be["outcome_by_pull_time_bucket"])
fig, ax = plt.subplots(figsize=(9, 5))
x8 = np.arange(len(b))
w = 0.38
ax.bar(x8 - w / 2, b["tie_rate"], w, label="Tied the game", color=GREEN)
ax.bar(x8 + w / 2, b["eng_rate"], w, label="Conceded an empty-netter", color=ORANGE)
for i, (_, r) in enumerate(b.iterrows()):
    ax.text(i, max(r["tie_rate"], r["eng_rate"]) + 1.5, f"n={int(r['n'])}",
            ha="center", fontsize=9, color=GREY)
ax.set_xticks(x8, b["bucket"])
ax.set_xlabel("Time remaining at first pull (down 1 goal)")
ax.set_ylabel("% of pulls")
ax.set_title("Pulling earlier ties more games, and the empty-net cost barely rises",
             loc="left")
ax.legend(frameon=False, fontsize=10, loc="upper left")
ax.set_ylim(0, 55)
save(fig, "08_pull_outcomes.png")
print("all charts done")
