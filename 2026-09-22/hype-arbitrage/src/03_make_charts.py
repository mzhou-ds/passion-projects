"""Five publication-style charts for the hype-arbitrage build."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "savefig.bbox_inches": "tight",
    "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "--",
})
SEG_COLORS = {
    "Grift zone": "#d62728",
    "Validated blockbusters": "#2ca02c",
    "Sleepers": "#1f77b4",
    "Lab curiosities": "#7f7f7f",
}
TITLE = "Musing with Mike · Hype Arbitrage · Google Trends US + ClinicalTrials.gov"

df = pd.read_csv("data/hype_evidence.csv")
monthly = pd.read_csv("data/trends_monthly.csv", parse_dates=["date"])


def finish(fig, name, title, subtitle):
    fig.suptitle(title, fontsize=14, fontweight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.94, subtitle, fontsize=9.5, color="#555", ha="left")
    fig.text(0.98, 0.01, TITLE, fontsize=7, color="#999", ha="right")
    fig.savefig(f"charts/{name}", bbox_inches="tight")
    plt.close(fig)
    print("wrote charts/" + name)


# 1 — Hype vs evidence scatter, sized by growth, colored by segment
fig, ax = plt.subplots(figsize=(10, 6.5))
for _, r in df.iterrows():
    ax.scatter(r["trials"] + 1, r["hype_2026"],
               s=60 + 260 * min(r["hype_growth"] / df["hype_growth"].max(), 1.5),
               c=SEG_COLORS[r["segment"]], alpha=0.75, edgecolors="white", linewidths=0.8,
               zorder=3)
    ax.annotate(r["keyword"], (r["trials"] + 1, r["hype_2026"]),
                xytext=(5, 4), textcoords="offset points", fontsize=8.5)
ax.set_xscale("log")
ax.axvline(df["trials"].median(), color="#999", ls=":", lw=1)
ax.axhline(df["hype_2026"].median(), color="#999", ls=":", lw=1)
ax.text(0.98, 0.96, "bubble size = search growth\n2020 → 2026", transform=ax.transAxes,
        ha="right", va="top", fontsize=8, color="#555",
        bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#ccc"))
for seg, col in SEG_COLORS.items():
    ax.scatter([], [], c=col, s=80, label=seg, edgecolors="white")
ax.legend(frameon=True, fontsize=9, loc="lower right", title="Segment")
ax.set_xlabel("Registered clinical trials (log scale, +1 so zeros show)")
ax.set_ylabel("Search interest 2026, index (anchor = creatine)")
finish(fig, "01_hype_vs_evidence.png",
       "Attention vs. evidence: the biohacking market, mapped",
       "16 biohacks · x = clinical trials registered · y = 2026 US search interest")


# 2 — Mispricing ranking
d2 = df.sort_values("mispricing")
fig, ax = plt.subplots(figsize=(9, 7))
colors = [SEG_COLORS[s] for s in d2["segment"]]
bars = ax.barh(d2["keyword"], d2["mispricing"], color=colors, edgecolor="white", height=0.62)
ax.axvline(0, color="black", lw=1)
ax.set_xlabel("Mispricing score  =  z(hype) − z(log trials)   →  hype outruns evidence")
for b, v in zip(bars, d2["mispricing"]):
    ax.text(v + (0.06 if v >= 0 else -0.06), b.get_y() + b.get_height() / 2, f"{v:+.2f}",
            va="center", ha="left" if v >= 0 else "right", fontsize=8.5)
finish(fig, "02_mispricing_rank.png",
       "The mispricing leaderboard: where hype outruns the science",
       "Positive = more search attention than the trial record justifies · negative = under-searched")


# 3 — Trajectories of the six most-searched biohacks
top6 = df.nlargest(6, "hype_2026")["keyword"].tolist()
fig, ax = plt.subplots(figsize=(10.5, 5.5))
for kw in top6:
    s = monthly[monthly["keyword"] == kw].sort_values("date")
    ax.plot(s["date"], s["index"], lw=2, label=kw)
ax.legend(fontsize=9, ncol=3, loc="upper left", frameon=True)
ax.set_ylabel("Search index (anchor = creatine = peak 100)")
ax.set_xlabel("Month")
fig.autofmt_xdate(rotation=0)
finish(fig, "03_trajectories.png",
       "Six years of biohacking attention, month by month",
       "US Google Trends, each series scaled against creatine in the same request")


# 4 — Growth multiples 2020 → 2026
d4 = df.sort_values("hype_growth")
fig, ax = plt.subplots(figsize=(9, 7))
colors = [SEG_COLORS[s] for s in d4["segment"]]
bars = ax.barh(d4["keyword"], d4["hype_growth"], color=colors, edgecolor="white", height=0.62)
ax.axvline(1, color="black", lw=1, ls="--")
ax.set_xlabel("Search interest multiple: mean 2026 ÷ mean 2020  (1 = flat)")
for b, v in zip(bars, d4["hype_growth"]):
    ax.text(v + 0.15, b.get_y() + b.get_height() / 2, f"{v:.1f}×",
            va="center", fontsize=8.5)
finish(fig, "04_growth.png",
       "What exploded since 2020 — and what quietly faded",
       "Mouth tape and sleepmaxxing didn't exist as searches in 2020; multiples shown vs. tiny base")


# 5 — Segment profiles
seg = json.load(open("data/segments.json"))
names = list(seg.keys())
fig, axes = plt.subplots(1, 3, figsize=(11, 4.2), sharey=False)
metrics = [("mean_hype_2026", "Mean 2026 hype index"),
           ("mean_trials", "Mean registered trials"),
           ("mean_mispricing", "Mean mispricing")]
for ax, (key, label) in zip(axes, metrics):
    vals = [seg[n][key] for n in names]
    ax.bar(names, vals, color=[SEG_COLORS[n] for n in names], edgecolor="white")
    ax.set_title(label, fontsize=10)
    ax.tick_params(axis="x", labelrotation=18, labelsize=8.5)
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8.5)
axes[0].set_ylabel("Segment average")
finish(fig, "05_segments.png",
       "Four market segments, by the numbers",
       "k-means on hype level, hype growth, trial volume, and results-posting rate")
