#!/usr/bin/env python3
"""The Friendship Portfolio — data analysis.

Builds six charts from the project's data/ directory:
  1. 01_friendship_recession.png   — AEI: the 1990-2021 collapse (men vs all adults)
  2. 02_distribution_shift.png     — AEI: full distribution of close-friend counts
  3. 03_loneliness_by_age.png      — Meta-Gallup: loneliness falls with age
  4. 04_young_adult_support.png    — WHR 2025: young adults losing support
  5. 05_mortality_stakes.png       — Holt-Lunstad/Pantell: what friendship is worth
  6. 06_lifesat_trends.png         — OWID Cantril ladder: US & Canada 2011-2025
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
CHARTS = BASE / "charts"
CHARTS.mkdir(exist_ok=True)

# ---- style ----
TEAL = "#1b7f7a"
RUST = "#c65d3a"
NAVY = "#2b3a55"
GOLD = "#d9a441"
GREY = "#8a8a8a"
LIGHT = "#e8e4da"
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.axisbelow": True,
    "figure.dpi": 150,
})
CAPTION = dict(fontsize=8.5, color="#555555", ha="left", va="top")


def save(fig, name):
    for ax in fig.axes:
        ax.xaxis.grid(False)
    fig.tight_layout()
    fig.savefig(CHARTS / name, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


aei = pd.read_csv(DATA / "aei_friendship.csv")


def get(metric, group, year):
    row = aei[(aei.metric == metric) & (aei.group == group) & (aei.year == year)]
    return float(row.iloc[0].value_pct)


# ---------- 1. the friendship recession ----------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
labels = ["No close\nfriends", "6+ close\nfriends"]
men90 = [get("no_close_friends", "men", 1990), get("six_or_more_close_friends", "men", 1990)]
men21 = [get("no_close_friends", "men", 2021), get("six_or_more_close_friends", "men", 2021)]
x = np.arange(len(labels)); w = 0.36
for ax, a, b, title in [(axes[0], men90, men21, "American men"),
                        (axes[1],
                         [get("no_close_friends", "all_adults", 1990),
                          get("ten_or_more_close_friends", "all_adults", 1990)],
                         [get("no_close_friends", "all_adults", 2021),
                          get("ten_or_more_close_friends", "all_adults", 2021)],
                         "All US adults")]:
    ax.bar(x - w / 2, a, w, label="1990", color=NAVY)
    ax.bar(x + w / 2, b, w, label="2021", color=RUST)
    for i, (va, vb) in enumerate(zip(a, b)):
        ax.text(i - w / 2, va + 1.2, f"{va:.0f}%", ha="center", fontsize=10, fontweight="bold")
        ax.text(i + w / 2, vb + 1.2, f"{vb:.0f}%", ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(labels if ax is axes[0] else ["No close\nfriends", "10+ close\nfriends"])
    ax.set_title(title)
    ax.set_ylim(0, 68)
axes[0].set_ylabel("% of group")
axes[0].legend(frameon=False, loc="upper right")
fig.suptitle("The friendship recession: American close-friend counts, 1990 vs 2021", y=1.02)
fig.text(0.01, -0.02,
         "Source: AEI Survey Center on American Life, 'The State of American Friendship' (Cox, 2021). "
         "1990 figures from Gallup comparison surveys. 2021: American Perspectives Survey, May 2021 (N=2,019).",
         **CAPTION)
save(fig, "01_friendship_recession.png")

# ---------- 2. distribution shift ----------
cats = ["0 friends", "1\u20133 friends", "4\u20139 friends", "10+ friends"]
d1990 = [3, 24, 40, 33]          # middle bands derived: 27% had <=3; 33% had 10+
d2021 = [12, 37, 36, 13]         # 49% had <=3; 36% had 4-9; 13% had 10+
fig, ax = plt.subplots(figsize=(10, 4.8))
x = np.arange(len(cats)); w = 0.36
b1 = ax.bar(x - w / 2, d1990, w, label="1990", color=NAVY)
b2 = ax.bar(x + w / 2, d2021, w, label="2021", color=RUST)
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.9,
            f"{b.get_height():.0f}%", ha="center", fontsize=10, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(cats)
ax.set_ylabel("% of US adults")
ax.set_ylim(0, 52)
ax.legend(frameon=False)
ax.set_title("How many close friends Americans have: the whole distribution moved left")
fig.text(0.01, -0.02,
         "Source: AEI Survey Center on American Life (2021), Fig. 3. Middle bands derived from reported "
         "totals (1990: 27% with \u22643 friends; 2021: 49% with \u22643, 36% with 4\u20139). "
         "Figures may not sum to 100% due to rounding.",
         **CAPTION)
save(fig, "02_distribution_shift.png")

# ---------- 3. loneliness by age ----------
lon = pd.read_csv(DATA / "gallup_loneliness_by_age.csv")
order = ["19-29", "all_adults", "65_plus"]
labels3 = ["Ages 19\u201329", "All adults", "Ages 65+"]
vals = [float(lon[lon.age_group == o].iloc[0].pct_lonely) for o in order]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
bars = ax.bar(labels3, vals, color=[RUST, GREY, TEAL], width=0.55)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.7, f"{v:.0f}%", ha="center",
            fontsize=12, fontweight="bold")
ax.set_ylim(0, 34); ax.set_ylabel("% feeling very or fairly lonely")
ax.set_title("Loneliness is a young person's epidemic, not an old person's")
ax.annotate("The loneliest group is the youngest —\nnot retirees, as the stereotype goes.",
            xy=(0, 27), xytext=(1.35, 30),
            arrowprops=dict(arrowstyle="->", color=NAVY), fontsize=10, color=NAVY)
fig.text(0.01, -0.02,
         "Source: Meta-Gallup Global State of Social Connections (fieldwork 2022, 142 countries/territories, "
         "adults 15+). Reported by Gallup, Oct 2023.",
         **CAPTION)
save(fig, "03_loneliness_by_age.png")

# ---------- 4. young adults losing support ----------
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
# left: no one to count on, 2006 vs 2023
base2006 = 19 / 1.39
axes[0].bar(["2006", "2023"], [base2006, 19], color=[GREY, RUST], width=0.5)
for x_, v in zip(["2006", "2023"], [base2006, 19]):
    axes[0].text(x_, v + 0.5, f"{v:.0f}%", ha="center", fontsize=11, fontweight="bold")
axes[0].set_ylim(0, 25)
axes[0].set_ylabel("% of young adults")
axes[0].set_title("No one to count on\n(Gallup World Poll)")
axes[0].annotate("+39% since 2006", xy=(1, 19), xytext=(0.35, 22),
                 arrowprops=dict(arrowstyle="->", color=NAVY), fontsize=10, color=NAVY)
# right: GFS social isolation by country
countries = ["Japan", "Global\naverage", "Nigeria /\nEgypt /\nPhilippines"]
iso = [30, 17, 10]
bars = axes[1].bar(countries, iso, color=[RUST, GREY, TEAL], width=0.55)
for b, v, lab in zip(bars, iso, [">30%", "17%", "<10%"]):
    axes[1].text(b.get_x() + b.get_width() / 2, v + 0.8, lab, ha="center",
                 fontsize=11, fontweight="bold")
axes[1].set_ylim(0, 38)
axes[1].set_ylabel("% with no close relationships")
axes[1].set_title("Social isolation varies wildly by culture\n(Global Flourishing Study)")
fig.suptitle("Young adults are losing their safety net", y=1.02)
fig.text(0.01, -0.04,
         "Source: World Happiness Report 2025, Ch. 5 (Pei & Zaki). Left: Gallup World Poll, 'no one to count on "
         "for social support'. Right: Global Flourishing Study, 22 countries/regions, young adults reporting "
         "no one they feel close to.",
         **CAPTION)
save(fig, "04_young_adult_support.png")

# ---------- 5. mortality stakes ----------
mort = pd.read_csv(DATA / "mortality_effect_sizes.csv")
order5 = ["Complex social integration", "Smoking (women)", "Social isolation (women)",
          "Smoking (men)", "Social isolation (men)", "All social relationship measures",
          "High blood pressure (women)", "Living alone (vs with others)", "High blood pressure (men)"]
m = mort.set_index("factor").loc[order5]
social = {"Complex social integration", "Social isolation (women)", "Social isolation (men)",
          "All social relationship measures", "Living alone (vs with others)"}
colors = [TEAL if f in social else GREY for f in order5]
fig, ax = plt.subplots(figsize=(10.5, 5.4))
y = np.arange(len(order5))
ax.barh(y, m["effect"], xerr=[m["effect"] - m["ci_low"], m["ci_high"] - m["effect"]],
        color=colors, capsize=4, error_kw=dict(ecolor="#333333", lw=1.2))
ax.axvline(1.0, color="#333333", ls="--", lw=1)
for i, v in enumerate(m["effect"]):
    ax.text(v + 0.04, i, f"{v:.2f}", va="center", fontsize=10, fontweight="bold")
ax.set_yticks(y); ax.set_yticklabels(order5)
ax.set_xlabel("Effect on mortality  (odds / hazard ratio; 1.0 = no effect)")
ax.set_xlim(0.9, 2.15)
ax.set_title("What friendship is worth: social connection rivals smoking as a mortality risk")
ax.invert_yaxis()
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=TEAL, label="Social-relationship factors"),
                   Patch(color=GREY, label="Clinical risk factors")],
          frameon=False, loc="lower right")
fig.text(0.01, -0.02,
         "Sources: Holt-Lunstad, Smith & Layton (2010), PLoS Medicine — meta-analysis of 148 studies, 308,849 "
         "participants (odds ratios of survival, strong vs weak ties). Clinical factors: Pantell et al. (2013), "
         "Am. J. Public Health (hazard ratios, NHANES). Error bars = 95% CI.",
         **CAPTION)
save(fig, "05_mortality_stakes.png")

# ---------- 6. life-satisfaction trends ----------
can = pd.read_csv(DATA / "cantril_ladder_owid.csv")
piv = can.pivot_table(index="year", columns="entity", values="cantril_ladder_score")
fig, ax = plt.subplots(figsize=(10.5, 4.8))
for ent, col, ls in [("United States", RUST, "-"), ("Canada", TEAL, "-"), ("Finland", GOLD, "--")]:
    s = piv[ent].dropna()
    ax.plot(s.index, s.values, label=ent, color=col, lw=2.4, ls=ls, marker="o", ms=4)
ax.set_ylabel("Cantril ladder (0\u201310)")
ax.set_xlabel("Year")
ax.set_title("Life satisfaction has drifted down in North America since the early 2010s")
ax.legend(frameon=False)
ax.set_ylim(6.2, 7.9)
fig.text(0.01, -0.02,
         "Source: Our World in Data / Wellbeing Research Centre (2026), 'Self-reported life satisfaction' "
         "[dataset]; original data: World Happiness Report / Gallup World Poll. Annual national averages.",
         **CAPTION)
save(fig, "06_lifesat_trends.png")

print("done.")
