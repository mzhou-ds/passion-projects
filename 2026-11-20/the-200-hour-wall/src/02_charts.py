#!/usr/bin/env python3
"""Charts for Build #74 — The 200-Hour Wall.

Reads data/*.csv written by src/01_analysis.py. Run after 01.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
CHARTS = os.path.join(ROOT, "charts")
os.makedirs(CHARTS, exist_ok=True)

plt.rcParams.update({
    "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "--",
    "figure.dpi": 150,
})
INK = "#1a1a1a"
BLUE = "#2f5d8a"
TEAL = "#2e8b74"
RUST = "#b4552d"
GREY = "#8a8a8a"
AGE_ORDER = ["15-24", "25-34", "35-44", "45-54", "55-64", "65+"]

ytf = pd.read_csv(os.path.join(DATA, "years_to_friend.csv"))
cad = pd.read_csv(os.path.join(DATA, "cadence.csv"))
age = pd.read_csv(os.path.join(DATA, "age_friend_hours.csv"))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, name), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


# 1. Years to a close friend by age and share of friend time (pooled 200h).
sub = ytf[(ytf.ladder == "pooled") & (ytf.rung == "close")]
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(AGE_ORDER))
w = 0.26
for i, s in enumerate([1.0, 0.5, 0.2]):
    vals = [sub[(sub.ageband == ab) & (sub.share == s)].iloc[0]["years"]
            for ab in AGE_ORDER]
    bars = ax.bar(x + (i - 1) * w, vals, w,
                  label={1.0: "All of it (100%)", 0.5: "Half (50%)",
                         0.2: "One of five friends (20%)"}[s],
                  color=[RUST, TEAL, BLUE][i])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.35, f"{v:.1f}",
                ha="center", va="bottom", fontsize=8.5, color=INK)
ax.set_xticks(x, [f"{a}\n({age[(age.era == '2021-25') & (age.ageband == a)].iloc[0]['friend_hrs_year']:.0f} hrs/yr)"
                  for a in AGE_ORDER])
ax.set_ylabel("Years to 200 hours with one new person")
ax.set_title("The 200-hour wall: years to a new close friend, 2021-25",
             loc="left", fontsize=13, fontweight="bold")
ax.legend(frameon=False, fontsize=9.5, loc="upper left")
ax.set_ylim(0, 13)
ax.set_axisbelow(True)
save(fig, "01_years_by_age_share.png")

# 2. The Hall ladder: pooled vs adult thresholds, annotated in years
#    at the 35-44 realistic pace (114 hrs/yr, 1-in-5 share = 22.8 hrs/yr).
fig, ax = plt.subplots(figsize=(9, 4.2))
labels = ["Casual friend", "Friend", "Close friend"]
pooled = [50, 90, 200]
adult = [94, 164, 264]
y = np.arange(len(labels))
h = 0.36
b1 = ax.barh(y + h / 2, pooled, h, label="Pooled (students + adults)", color=TEAL)
b2 = ax.barh(y - h / 2, adult, h, label="Adults only", color=RUST)
for bars, vals in [(b1, pooled), (b2, adult)]:
    for b, v in zip(bars, vals):
        ax.text(v + 5, b.get_y() + b.get_height() / 2, f"{v} hrs",
                va="center", fontsize=10, color=INK)
pace = 22.8  # hrs/yr with a new person for a 35-44 adult at a 1-in-5 share
for i, (p, a) in enumerate(zip(pooled, adult)):
    ax.text(300, i + h / 2, f"{p / pace:.1f} yrs at 35-44 pace",
            va="center", fontsize=9, color=TEAL)
    ax.text(300, i - h / 2, f"{a / pace:.1f} yrs at 35-44 pace",
            va="center", fontsize=9, color=RUST)
ax.set_yticks(y, labels)
ax.invert_yaxis()
ax.set_xlim(0, 400)
ax.set_xlabel("Cumulative hours together from first meeting")
ax.set_title("Hall's ladder: the hours friendship costs (Hall 2019)",
             loc="left", fontsize=13, fontweight="bold")
ax.legend(frameon=False, fontsize=9.5, loc="upper right")
save(fig, "02_hall_ladder.png")

# 3. Cadence: weekly hours with the new person -> years to close friend.
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(cad["hrs_per_week_with_new_person"],
        cad["years_to_close_pooled_200h"], marker="o", color=TEAL,
        label="Close friend, pooled 200 hrs")
ax.plot(cad["hrs_per_week_with_new_person"],
        cad["years_to_close_adult_264h"], marker="s", color=RUST,
        label="Close friend, adults 264 hrs")
for _, r in cad.iterrows():
    ax.annotate(f"{r['years_to_close_pooled_200h']:.1f} yrs",
                (r["hrs_per_week_with_new_person"],
                 r["years_to_close_pooled_200h"]),
                textcoords="offset points", xytext=(0, 9), ha="center",
                fontsize=9, color=TEAL)
ax.axvline(1, color=GREY, linestyle=":", linewidth=1.2)
ax.text(1.05, 8.6, "one hour a week:\n3.9 years (pooled),\n5.1 years (adults)",
        fontsize=9, color=INK)
ax.set_xlabel("Hours per week spent with the new person")
ax.set_ylabel("Years to a close friend")
ax.set_title("Concentration is the only lever that moves",
             loc="left", fontsize=13, fontweight="bold")
ax.legend(frameon=False, fontsize=9.5, loc="upper right")
ax.set_ylim(0, 11)
save(fig, "03_cadence.png")

# 4. Era comparison: years to close friend (200h, 1-in-5 share), 2003-07 vs 2021-25.
res = pd.read_json(os.path.join(DATA, "results.json"))
era = res["era_comparison_years_to_close_200h_share20"]
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(AGE_ORDER))
old = [era[ab]["2003-07"] for ab in AGE_ORDER]
new = [era[ab]["2021-25"] for ab in AGE_ORDER]
w = 0.36
b1 = ax.bar(x - w / 2, old, w, label="2003-07", color=GREY)
b2 = ax.bar(x + w / 2, new, w, label="2021-25", color=BLUE)
for bars, vals in [(b1, old), (b2, new)]:
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.1f}",
                ha="center", va="bottom", fontsize=9, color=INK)
ax.set_xticks(x, AGE_ORDER)
ax.set_ylabel("Years to 200 hours (new person gets 1/5 of friend time)")
ax.set_title("The wall got twice as high in twenty years",
             loc="left", fontsize=13, fontweight="bold")
ax.legend(frameon=False, fontsize=9.5)
ax.set_ylim(0, 11.5)
save(fig, "04_era_comparison.png")

print("done")
