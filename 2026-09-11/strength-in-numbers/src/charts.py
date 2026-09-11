"""Generate all charts for Strength in Numbers."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "output")
CH = os.path.join(HERE, "charts")
os.makedirs(CH, exist_ok=True)

BLUE, PINK = "#2a6fbf", "#d95f02"   # men / women
INK, GRID = "#222222", "#d9d9d9"

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150,
    "font.size": 10, "axes.edgecolor": GRID,
    "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(CH, name), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


standards = pd.read_csv(os.path.join(OUT, "standards.csv"))
age = pd.read_csv(os.path.join(OUT, "age_curve.csv"))
yearly = pd.read_csv(os.path.join(OUT, "yearly.csv"))
dots = pd.read_csv(os.path.join(OUT, "dots_bias.csv"))

# ---------------------------------------------------------------- 1. standards
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
for ax, sex, title in zip(axes, ["M", "F"],
                          ["Men — best raw total by bodyweight",
                           "Women — best raw total by bodyweight"]):
    g = standards[(standards.sex == sex)
                  & (standards.equipment == "Raw")].sort_values("bw_bin")
    x = g["bw_bin"] + 2.5
    for p, ls, alpha in [("p90", "-", 1.0), ("p75", "--", .8),
                         ("p50", "-", 1.0), ("p25", "--", .8), ("p10", "-", 1.0)]:
        lw = 2.2 if p == "p50" else 1.2
        ax.plot(x, g[p], ls=ls, lw=lw, alpha=alpha,
                color=BLUE if sex == "M" else PINK,
                label={"p90": "90th", "p75": "75th", "p50": "median",
                       "p25": "25th", "p10": "10th"}[p])
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xlabel("Bodyweight (kg)")
    ax.grid(axis="y", color=GRID, alpha=.5)
axes[0].set_ylabel("Total (kg)")
axes[0].legend(title="Percentile", fontsize=8)
fig.suptitle("Strength standards: 225,463 raw powerlifters, one best total each",
             fontsize=12, fontweight="bold", y=1.02)
save(fig, "01_standards.png")

# ---------------------------------------------------------------- 2. age curve
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
for ax, sex, title in zip(axes, ["M", "F"], ["Men", "Women"]):
    g = age[age.sex == sex].sort_values("age")
    ax.fill_between(g["age"], g["p25_gl"], g["p75_gl"],
                    color=BLUE if sex == "M" else PINK, alpha=.18,
                    label="middle 50%")
    ax.plot(g["age"], g["median_gl"], color=BLUE if sex == "M" else PINK,
            lw=2.2, label="median")
    ax.plot(g["age"], g["p90_gl"], color=INK, lw=1.4, ls="--",
            label="90th pct (elites)")
    pk = g.loc[g["median_gl"].idxmax()]
    ax.annotate(f"peak {int(pk['age'])}", xy=(pk["age"], pk["median_gl"]),
                xytext=(8, 12), textcoords="offset points", fontsize=9,
                arrowprops=dict(arrowstyle="->", color=INK))
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xlabel("Age")
    ax.set_xlim(14, 75)
    ax.grid(axis="y", color=GRID, alpha=.5)
axes[0].set_ylabel("Goodlift points (bodyweight-adjusted)")
axes[0].legend(fontsize=8)
fig.suptitle("The age curve of strength: median competitor peaks at 26 (M) / 24 (F)",
             fontsize=12, fontweight="bold", y=1.02)
save(fig, "02_age_curve.png")

# ------------------------------------------------- 3. participation + strength
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
y = yearly[yearly.year >= 2005].copy()
for ax, col, title, logy in [
        (axes[0], "lifters", "Unique raw lifters per year", True),
        (axes[1], "median_total", "Median raw total per year (kg)", False)]:
    for sex, c in [("M", BLUE), ("F", PINK)]:
        g = y[y.sex == sex].sort_values("year")
        ax.plot(g["year"], g[col], color=c, lw=2,
                label="Men" if sex == "M" else "Women")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xlabel("Year")
    if logy:
        ax.set_yscale("log")
    ax.grid(axis="y", color=GRID, alpha=.5)
axes[0].legend(fontsize=9)
axes[0].set_ylabel("Lifters (log scale)")
axes[1].set_ylabel("Median total (kg)")
fig.suptitle("Powerlifting's boom: participation up 16–38x since 2010",
             fontsize=12, fontweight="bold", y=1.02)
save(fig, "03_growth.png")

# ---------------------------------------------------------------- 4. sex gap
fig, ax = plt.subplots(figsize=(8, 4.5))
piv = y.pivot(index="year", columns="sex", values="median_total")
gap = (piv["F"] / piv["M"] * 100).dropna()
ax.plot(gap.index, gap.values, color=PINK, lw=2.2)
ax.fill_between(gap.index, gap.values, 100, color=PINK, alpha=.12)
ax.set_title("The strength gap is closing", fontsize=12, fontweight="bold")
ax.set_xlabel("Year")
ax.set_ylabel("Women's median total as % of men's (raw)")
ax.set_ylim(45, 65)
ax.grid(axis="y", color=GRID, alpha=.5)
for yr in [gap.index[0], gap.index[-1]]:
    ax.annotate(f"{gap.loc[yr]:.1f}%", xy=(yr, gap.loc[yr]),
                xytext=(0, 10), textcoords="offset points", fontsize=9,
                ha="center", fontweight="bold")
save(fig, "04_sex_gap.png")

# ---------------------------------------------------------------- 5. dots bias
fig, ax = plt.subplots(figsize=(8, 4.5))
for sex, c, lab in [("M", BLUE, "Men"), ("F", PINK, "Women")]:
    g = dots[dots.sex == sex].sort_values("bw_bin")
    ax.plot(g["bw_bin"] + 2.5, g["median_dots"], color=c, lw=2, label=lab)
ax.set_title("Dots still favors heavyweights", fontsize=12, fontweight="bold")
ax.set_xlabel("Bodyweight (kg)")
ax.set_ylabel("Median Dots score (raw lifters)")
ax.legend(fontsize=9)
ax.grid(axis="y", color=GRID, alpha=.5)
fig.text(0.5, -0.02,
         "A perfect formula would be flat: the median 140 kg man outscores the median "
         "60 kg man by ~12%.", ha="center", fontsize=9, style="italic")
save(fig, "05_dots_bias.png")

# ---------------------------------------------------------------- 6. equipment
equip = pd.read_csv(os.path.join(OUT, "equipment.csv"))
fig, ax = plt.subplots(figsize=(8, 4.5))
x = np.arange(len(equip))
w = 0.35
ax.bar(x - w / 2, equip["raw_median"], w, label="Raw best", color="#9db8dd")
ax.bar(x + w / 2, equip["sp_median"], w, label="Single-ply best", color=BLUE)
for i, r in equip.iterrows():
    ax.text(i, r["sp_median"] + 8, f"+{r['median_uplift_pct']:.1f}%",
            ha="center", fontsize=10, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(["Men\n(n=21,608 paired)", "Women\n(n=7,795 paired)"])
ax.set_ylabel("Median best total (kg)")
ax.set_title("What the suit is worth: same lifter, raw vs single-ply",
             fontsize=12, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(axis="y", color=GRID, alpha=.5)
save(fig, "06_equipment.png")

print("All charts done.")
