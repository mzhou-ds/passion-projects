"""Charts for Fake Parity."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CH = ROOT / "charts"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})

trends = pd.read_csv(ROOT / "data" / "season_trends.csv")
hope = pd.read_csv(ROOT / "data" / "hope_snapshots.csv")

# 1 -- OT rate by season ------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(trends.season_label, trends.ot_rate * 100, marker="o", color="#b5541e",
        label="Games reaching OT/SO (= games awarding 3 points)")
ax.plot(trends.season_label, trends.so_rate * 100, marker="s", color="#4a6fa5",
        label="Games reaching a shootout")
ax.axvline(1.5, color="grey", ls="--", lw=0.8)
ax.annotate("3-on-3 OT\nstarts 2015-16", xy=(1.55, 26.5), fontsize=8, color="grey")
ax.axvspan(6.5, 7.5, color="grey", alpha=0.12)
ax.annotate("COVID\nseasons", xy=(6.62, 12), fontsize=8, color="grey")
ax.set_ylabel("% of regular-season games")
ax.set_title("One in four NHL games now pays out a bonus point")
ax.legend(fontsize=8, frameon=False)
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(CH / "ot_rate.png")
plt.close()

# 2 -- standings spread by system ----------------------------------------------
fig, ax = plt.subplots(figsize=(8, 4.2))
for col, lab, c in [("spread_pct_nhl", "Actual (loser point)", "#b5541e"),
                    ("spread_pct_wl", "Win/loss only", "#4a6fa5"),
                    ("spread_pct_iihf", "3-2-1-0 (IIHF)", "#3d7a44")]:
    ax.plot(trends.season_label, trends[col], marker="o", label=lab, color=c)
ax.set_ylabel("SD of team points% (higher = more separation)")
ax.set_title("The loser point compresses the table in every season")
ax.legend(fontsize=8, frameon=False)
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(CH / "spread.png")
plt.close()

# 3 -- hope on March 1 -----------------------------------------------------------
mar = hope[hope.date == "03-01"]
fig, ax = plt.subplots(figsize=(8, 4.2))
x = range(len(mar))
w = 0.27
for i, (col, lab, c) in enumerate([("hope_nhl", "Actual", "#b5541e"),
                                   ("hope_wl", "Win/loss only", "#4a6fa5"),
                                   ("hope_iihf", "3-2-1-0", "#3d7a44")]):
    ax.bar([j + (i - 1) * w for j in x], mar[col], width=w, label=lab, color=c)
ax.set_xticks(list(x))
ax.set_xticklabels(mar.season_label, rotation=45, ha="right")
ax.set_ylabel("Teams within .030 points% of the cutline, Mar 1")
ax.set_title("Hope, manufactured: more fanbases 'in the race' under the loser point")
ax.legend(fontsize=8, frameon=False)
plt.tight_layout()
plt.savefig(CH / "hope.png")
plt.close()

# 4 -- SHAP ----------------------------------------------------------------------
s = pd.read_csv(ROOT / "data" / "shap_ot.csv").head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 4.4))
ax.barh(s.feature, s.mean_abs_shap, color="#b5541e")
ax.set_xlabel("Mean |SHAP| -- predicting whether a game reaches OT (test 2022-25)")
ax.set_title("What sends a game to overtime")
plt.tight_layout()
plt.savefig(CH / "shap.png")
plt.close()

print("charts done")
