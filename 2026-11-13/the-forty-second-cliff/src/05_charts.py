"""Charts for The Forty-Second Cliff. Clean, direct, finding-first titles."""
import json, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
CH = os.path.join(BASE, "charts")
os.makedirs(CH, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "-",
    "figure.dpi": 150,
})
DEF, OFF, NEU = "#C0392B", "#2471A3", "#7D7D7D"
LABELS = ["0-10", "10-20", "20-30", "30-40", "40-50", "50-60",
          "60-70", "70-80", "80-90", "90+"]
X = np.arange(len(LABELS))

def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(CH, name), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)

# 1. The cliff: xG for/against per 60 by mean shift age
d = pd.read_csv(os.path.join(DATA, "curve_defense.csv"))
a = pd.read_csv(os.path.join(DATA, "curve_offense.csv"))
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(X, d["xg_per60"], "o-", color=DEF, lw=2.5, label="Conceded (xGA/60)")
ax.plot(X, a["xg_per60"], "s-", color=OFF, lw=2.5, label="Generated (xGF/60)")
ax.axvspan(0.5, 2.5, color="green", alpha=0.07)
ax.text(1.5, 13.5, "safe zone\n10-30s", ha="center", fontsize=10, color="#1E8449")
ax.axvline(3.5, color=NEU, ls="--", lw=1.2)
ax.text(3.7, 19.0, "the cliff starts ~35-40s", fontsize=10, color="#555555")
ax.set_xticks(X, LABELS)
ax.set_xlabel("Mean shift age of the five skaters on the ice (seconds)")
ax.set_ylabel("Expected goals per 60 minutes")
ax.set_title("Past 40 seconds, defence collapses and offence does not save you",
             fontsize=13, weight="bold", loc="left")
ax.legend(frameon=False, loc="upper left")
save(fig, "cliff.png")

# 2. Decomposition: both-old vs fresh-attackers
bo = pd.read_csv(os.path.join(DATA, "curve_both_old.csv"))
fa = pd.read_csv(os.path.join(DATA, "curve_fresh_attackers.csv"))
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(X, bo["xg_per60"], "o-", color=DEF, lw=2.5,
        label="Both lines old (40s+) - no siege selection")
ax.plot(X, fa["xg_per60"], "s-", color="#E67E22", lw=2.5,
        label="Attackers fresh, defenders old (the siege)")
ax.plot(X, d["xg_per60"], ":", color=NEU, lw=1.8, label="Overall")
ax.set_xticks(X, LABELS)
ax.set_xlabel("Defending line's mean shift age (seconds)")
ax.set_ylabel("Expected goals conceded per 60")
ax.set_title("The cliff survives when the attackers are tired too: it is fatigue, not just siege",
             fontsize=12, weight="bold", loc="left")
ax.legend(frameon=False, loc="upper left", fontsize=9.5)
save(fig, "decomposition.png")

# 3. Time share vs goal share
s = pd.read_csv(os.path.join(DATA, "share_vs_time.csv"))
fig, ax = plt.subplots(figsize=(9, 4.6))
w = 0.38
ax.bar(X - w/2, s["time_share"] * 100, w, color=NEU, alpha=0.65, label="Share of 5v5 time")
ax.bar(X + w/2, s["goal_share"] * 100, w, color=DEF, label="Share of goals conceded")
for i, v in enumerate(s["goal_share"] * 100):
    if v >= 4:
        ax.text(i + w/2, v + 0.7, f"{v:.0f}%", ha="center", fontsize=9, color=DEF, weight="bold")
ax.set_xticks(X, LABELS)
ax.set_xlabel("Defending line's mean shift age (seconds)")
ax.set_ylabel("Percent of the season total")
ax.set_title("40+ seconds is 15% of the ice time and 37% of the goals against",
             fontsize=13, weight="bold", loc="left")
ax.legend(frameon=False, loc="upper right")
save(fig, "share.png")

# 4. Fresh defenders: change 2, not 5
f = pd.read_csv(os.path.join(DATA, "fresh_count.csv"))
fig, ax = plt.subplots(figsize=(9, 4.6))
colors = [DEF if n == 5 else ("#1E8449" if n == 2 else NEU) for n in f["n_fresh_defenders"]]
ax.bar(f["n_fresh_defenders"], f["xg_per60"], color=colors, width=0.65)
for _, r in f.iterrows():
    ax.text(r["n_fresh_defenders"], r["xg_per60"] + 0.5, f"{r['xg_per60']:.1f}",
            ha="center", fontsize=10, weight="bold")
ax.axhline(5.31, color=DEF, ls="--", lw=1.2)
ax.text(5.4, 5.6, "no fresh skaters: 5.3", fontsize=9.5, color=DEF, ha="right")
ax.set_xticks(range(6))
ax.set_xlabel("Defending skaters who just changed on (shift age <= 5s)")
ax.set_ylabel("Expected goals conceded per 60")
ax.set_title("Change two skaters and you are safe. Change all five and you are exposed.",
             fontsize=12.5, weight="bold", loc="left")
save(fig, "fresh_count.png")

# 5. Penalties
p = pd.read_csv(os.path.join(DATA, "penalty_rate.csv"))
fig, ax = plt.subplots(figsize=(9, 4.4))
ax.plot(X, p["pen_per60"], "o-", color="#6C3483", lw=2.5)
ax.fill_between(X, p["pen_per60"], alpha=0.12, color="#6C3483")
ax.set_xticks(X, LABELS)
ax.set_xlabel("Penalised team's mean shift age (seconds)")
ax.set_ylabel("Minor/major penalties taken per 60")
ax.set_title("Tired legs take penalties: 5x the rate past 60 seconds vs the 10-20s trough",
             fontsize=12, weight="bold", loc="left")
save(fig, "penalties.png")

# 6. SHAP ranking (excluding the shot_type_unknown recording artifact)
m = json.load(open(os.path.join(DATA, "model.json")))
rank = {k: v for k, v in m["shap_rank"].items() if k != "shot_type_unknown"}
top = pd.Series(rank).sort_values().tail(12)
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.barh(top.index, top.values, color=OFF)
ax.set_xlabel("Mean |SHAP value| on held-out games (goal probability)")
ax.set_title("What predicts a goal, once shot quality is controlled for",
             fontsize=12.5, weight="bold", loc="left")
save(fig, "shap.png")
