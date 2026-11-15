"""Charts for The Exchange Rate of Youth. Clean, direct, finding-first titles."""
import os

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
MEN, WOMEN, NEU = "#2471A3", "#C0392B", "#7D7D7D"
SQUAT, BENCH, DEAD = "#2471A3", "#E67E22", "#1E8449"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(CH, name), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


rates = pd.read_csv(os.path.join(DATA, "exchange_rates.csv"))
curves = pd.read_csv(os.path.join(DATA, "age_curves.csv"))

# 1. Hero: the exchange rate for the total, men and women
fig, ax = plt.subplots(figsize=(9, 4.8))
for sex, color, bw, label in [("M", MEN, 90, "Men, 90 kg bodyweight"),
                              ("F", WOMEN, 65, "Women, 65 kg bodyweight")]:
    sub = rates[(rates.sex == sex) & (rates.lift == "total") & (rates.bw == bw)]
    sub = sub[(sub.age >= 25) & (sub.age <= 70)]
    ax.plot(sub.age, sub.kg_per_year, "o-", color=color, lw=2.5, label=label)
ax.axhline(0, color=NEU, lw=1)
ax.axhspan(-3.5, 0, color="#1E8449", alpha=0.06)
ax.text(26, -2.9, "under 30, getting older is free strength\n(the rate is negative: age adds kilos)",
        fontsize=10, color="#1E8449")
ax.annotate("age 40: 1.3 kg/yr", xy=(40, 1.26), xytext=(33, 2.6),
            arrowprops=dict(arrowstyle="->", color=MEN), fontsize=10, color=MEN)
ax.annotate("age 60: 2.4 kg/yr", xy=(60, 2.37), xytext=(52, 4.1),
            arrowprops=dict(arrowstyle="->", color=MEN), fontsize=10, color=MEN)
ax.set_xlabel("Age (years)")
ax.set_ylabel("Kilos of bodyweight that buy back one year of aging")
ax.set_title("How many kilos is a year of youth worth?", fontsize=13, weight="bold")
ax.set_ylim(-3.5, 4.6)
ax.legend(frameon=False, loc="upper left")
save(fig, "exchange_rate.png")

# 2. Per lift (men): bench is cheap to buy back, deadlift is expensive
fig, ax = plt.subplots(figsize=(9, 4.8))
for lift, color in [("squat", SQUAT), ("bench", BENCH), ("deadlift", DEAD)]:
    sub = rates[(rates.sex == "M") & (rates.lift == lift) & (rates.bw == 90)]
    sub = sub[(sub.age >= 25) & (sub.age <= 65)]
    ax.plot(sub.age, sub.kg_per_year, "o-", color=color, lw=2.5, label=lift.capitalize())
ax.axhline(0, color=NEU, lw=1)
ax.set_xlabel("Age (years)")
ax.set_ylabel("Kilos of bodyweight per year of aging (men, 90 kg)")
ax.set_title("The bench is the cheapest lift to buy back; the deadlift is the dearest",
             fontsize=13, weight="bold")
ax.annotate("at 45, a year of aging costs\n0.9 kg on bench, 1.8 kg on deadlift",
            xy=(45, 1.3), xytext=(26, 3.75), fontsize=10, color="#555555",
            arrowprops=dict(arrowstyle="->", color=NEU))
ax.set_ylim(-1.0, 4.3)
ax.legend(frameon=False, loc="lower right")
save(fig, "per_lift.png")

# 3. The age curves themselves, with peaks marked
fig, ax = plt.subplots(figsize=(9, 4.8))
for sex, color, bw in [("M", MEN, 90), ("F", WOMEN, 65)]:
    sub = curves[(curves.sex == sex) & (curves.lift == "total")]
    ax.plot(sub.age, sub.pred_kg, "-", color=color, lw=2.5,
            label=f"{'Men' if sex == 'M' else 'Women'}, {bw} kg")
    pk = sub.loc[sub.pred_kg.idxmax()]
    ax.plot([pk.age], [pk.pred_kg], "o", color=color, ms=8)
    ax.annotate(f"peak: {int(pk.age)} yr, {pk.pred_kg:.0f} kg",
                xy=(pk.age, pk.pred_kg), xytext=(pk.age + 6, pk.pred_kg + 25),
                fontsize=10, color=color,
                arrowprops=dict(arrowstyle="->", color=color))
ax.set_xlabel("Age (years)")
ax.set_ylabel("Predicted powerlifting total (kg)")
ax.set_title("Strength peaks at 27-28, then the long slide", fontsize=13, weight="bold")
ax.legend(frameon=False, loc="upper right")
save(fig, "age_curves.png")

# 4. The masters cliff: year-on-year % change in total, from the model
fig, ax = plt.subplots(figsize=(9, 4.8))
for sex, color, bw, knot in [("M", MEN, 90, 52), ("F", WOMEN, 65, 44)]:
    sub = curves[(curves.sex == sex) & (curves.lift == "total")].sort_values("age")
    pct = sub.pred_kg.pct_change() * 100
    ax.plot(sub.age.values[1:], pct.values[1:], "-", color=color, lw=2.5,
            label=f"{'Men' if sex == 'M' else 'Women'} ({bw} kg)")
    ax.axvline(knot, color=color, ls="--", lw=1.2, alpha=0.6)
    ax.text(knot + 0.7, -0.35, f"cliff: {knot}", fontsize=10, color=color)
ax.axhline(0, color=NEU, lw=1)
ax.set_xlabel("Age (years)")
ax.set_ylabel("Change in total per year of age (%)")
ax.set_title("The slide is gentle for decades, then it steepens 4- to 5-fold",
             fontsize=13, weight="bold")
ax.set_ylim(-2.6, 0.6)
ax.legend(frameon=False, loc="lower left")
save(fig, "cliff.png")

# 5. Cross-section vs within-lifter: the aging curve is mostly not aging
fig, ax = plt.subplots(figsize=(9, 4.6))
labels = ["Men", "Women"]
x = np.arange(len(labels))
cross = [-0.82, -0.90]   # model decade cost 45-55, per year
within = [-0.20, 1.08]   # within-lifter slope, meets at age 45+, n=2206 / 1091
w = 0.36
b1 = ax.bar(x - w / 2, cross, w, color=NEU, label="Cross-sectional: what the age curve says")
b2 = ax.bar(x + w / 2, within, w, color="#1E8449",
            label="Within-lifter: what actually happens to lifters who keep competing")
for bars in (b1, b2):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + (0.08 if b.get_height() >= 0 else -0.22),
                f"{b.get_height():+.2f}%", ha="center", fontsize=11)
ax.axhline(0, color="black", lw=0.8)
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel("Change in total per year of age, past 45 (%)")
ax.set_title("The cross-section overstates aging 4x: the 55-year-olds at a meet\nare mostly people who started lifting at 50",
             fontsize=12, weight="bold")
ax.legend(frameon=False, loc="upper left", fontsize=10)
ax.set_ylim(-1.3, 1.7)
save(fig, "longitudinal.png")
