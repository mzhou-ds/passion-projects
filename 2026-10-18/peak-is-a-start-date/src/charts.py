#!/usr/bin/env python3
"""Charts for The Peak Is a Start Date. Reads output/results.json + data."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
R = json.load(open(os.path.join(ROOT, "output", "results.json")))
CH = os.path.join(ROOT, "charts")
plt.rcParams.update({"figure.dpi": 130, "font.size": 10, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False})
C1, C2, C3 = "#1f6f54", "#c0392b", "#2e5f8a"

# 01 peak age vs start age
b = R["peak_by_start_band"]
mids = [np.mean([int(x) for x in r["band"].split("-")]) + 0.5 for r in b]
fig, ax = plt.subplots(figsize=(7.2, 4.6))
ax.scatter(mids, [r["peak_age_med"] for r in b], s=[r["n"] / 2 for r in b],
           color=C1, zorder=3, label="Median peak age (bubble = careers)")
xs = np.linspace(16, 62, 10)
ax.plot(xs, R["peak_regression"]["slope"] * xs + R["peak_regression"]["intercept"],
        color=C1, lw=1.2, ls="--", label=f"Fit: peak = 0.89 x start + 10")
ax.plot(xs, xs, color="grey", lw=1, ls=":", label="Peak age = start age")
ax.axhline(24, color=C2, lw=1.2, ls="-", label="Cross-sectional 'peak' (age 24)")
for x, r in zip(mids, b):
    ax.annotate(f"{r['peak_age_med']:.0f}", (x, r["peak_age_med"]), textcoords="offset points",
                xytext=(0, 9), ha="center", fontsize=9)
ax.set_xlabel("Age at first competition"); ax.set_ylabel("Median age at career-best Goodlift")
ax.set_title("Your peak follows your start date, not the textbook curve")
ax.legend(fontsize=8, loc="upper left"); fig.tight_layout()
fig.savefig(f"{CH}/01_peak_vs_start.png"); plt.close(fig)

# 02 retained: cross-section curve vs within-lifter at-age
df = pd.read_parquet(os.path.join(ROOT, "data", "careers.parquet"))
xs = df.groupby("Age").Goodlift.median(); cnt = df.groupby("Age").size()
ages = [a for a in xs.index if cnt[a] >= 100 and 20 <= a <= 75]
ret = xs[ages] / xs[ages].max() * 100
fig, ax = plt.subplots(figsize=(7.2, 4.6))
ax.plot(ages, ret, color=C2, lw=1.8, label="Cross-section (different people at each age)")
wa = R["retained_at_age_within"]
ax.scatter([50, 60, 70], [wa["50"]["retained_med"], wa["60"]["retained_med"], wa["70"]["retained_med"]],
           s=90, color=C1, zorder=4, label="Same lifters vs their own peak (still competing)")
for a in ["50", "60", "70"]:
    ax.annotate(f"{wa[a]['retained_med']:.0f}%", (int(a), wa[a]["retained_med"]),
                textcoords="offset points", xytext=(0, 10), ha="center", color=C1, fontweight="bold")
ax.set_xlabel("Age"); ax.set_ylabel("% of peak Goodlift")
ax.set_title("The age cliff is a collage. The same lifters barely fade.")
ax.legend(fontsize=8.5, loc="lower left"); fig.tight_layout()
fig.savefig(f"{CH}/02_two_curves.png"); plt.close(fig)

# 03 post-peak retention horizons
h = R["retained_post_peak"]
fig, ax = plt.subplots(figsize=(6.4, 4.2))
ax.bar([f"+{k} years" for k in h], [v["retained_med"] for v in h.values()], color=C3, width=0.5)
for i, v in enumerate(h.values()):
    ax.annotate(f"{v['retained_med']:.1f}%\n(n={v['n']})", (i, v["retained_med"]),
                textcoords="offset points", xytext=(0, 6), ha="center")
ax.set_ylim(70, 102); ax.set_ylabel("Median % of own peak (annual best)")
ax.set_title("After your own peak: a slope, not a cliff")
fig.tight_layout(); fig.savefig(f"{CH}/03_post_peak.png"); plt.close(fig)

# 04 exit by meet outcome
e = R["exit_by_vs_pb"]
fig, ax = plt.subplots(figsize=(7.2, 4.4))
labels = [r["bin"].replace(" vs PB", "") for r in e]
cols = [C2 if i == 0 else C1 if r["bin"] == "new PR" else "grey" for i, r in enumerate(e)]
ax.bar(labels, [r["exit_rate"] * 100 for r in e], color=cols, width=0.6)
for i, r in enumerate(e):
    ax.annotate(f"{r['exit_rate']*100:.1f}%", (i, r["exit_rate"] * 100),
                textcoords="offset points", xytext=(0, 5), ha="center")
ax.set_ylabel("% with no meet in the next 3 years"); ax.set_ylim(0, 40)
ax.set_title("A disaster meet barely raises the chance a lifter disappears")
fig.tight_layout(); fig.savefig(f"{CH}/04_exit_by_outcome.png"); plt.close(fig)

# 05 SHAP for exit model
sh = R["exit_model"]["shap"]
names = {"vs_pb_pct": "Result vs personal best", "Age": "Age", "career_year": "Years competing",
         "meets_so_far": "Meets so far", "days_since_last": "Days since previous meet",
         "Goodlift": "Strength level (Goodlift)", "sex_m": "Sex", "BodyweightKg": "Bodyweight"}
fig, ax = plt.subplots(figsize=(7.2, 4.4))
items = sorted(sh.items(), key=lambda t: t[1])
ax.barh([names.get(k, k) for k, _ in items], [v for _, v in items],
        color=[C2 if k == "vs_pb_pct" else C3 for k, _ in items])
ax.set_xlabel("Mean |SHAP| — XGBoost exit model (AUC "
              f"{R['exit_model']['auc']})")
ax.set_title("What predicts quitting: career fatigue, not one bad day")
fig.tight_layout(); fig.savefig(f"{CH}/05_exit_shap.png"); plt.close(fig)

# 06 early velocity by start band
v = R["early_velocity"]
fig, ax = plt.subplots(figsize=(7.2, 4.4))
ax.bar([r["band"] for r in v], [r["gain_pct_per_yr_med"] for r in v], color=C1, width=0.6)
for i, r in enumerate(v):
    ax.annotate(f"{r['gain_pct_per_yr_med']:.1f}%", (i, r["gain_pct_per_yr_med"]),
                textcoords="offset points", xytext=(0, 5), ha="center")
ax.set_xlabel("Age at first competition"); ax.set_ylabel("Median Goodlift gain, %/yr, career years 0-3")
ax.set_title("Older beginners improve too - at about a third of the teenage rate")
fig.tight_layout(); fig.savefig(f"{CH}/06_velocity.png"); plt.close(fig)
print("charts done")
