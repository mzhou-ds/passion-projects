"""Five publication-style charts for the hype-arbitrage build."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

LEGEND_HANDLES = lambda: [Line2D([0], [0], marker="o", color="w", markerfacecolor=c,
                                  markeredgecolor="white", markersize=9, label=s)
                          for s, c in SEG_COLORS.items()]

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150,
    "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "--",
})
SEG_COLORS = {
    "Grift zone": "#d62728",
    "Validated blockbusters": "#2ca02c",
    "Sleepers": "#1f77b4",
    "Lab curiosities": "#7f7f7f",
}
FOOT = ("Musing with Mike · Hype Arbitrage · Wikipedia pageviews + PubMed + ClinicalTrials.gov")

df = pd.read_csv("data/hype_evidence.csv")
monthly = pd.read_csv("data/pageviews_monthly.csv")
monthly["date"] = pd.to_datetime(monthly["date"], format="%Y%m")


def finish(fig, name, title, subtitle):
    fig.suptitle(title, fontsize=14, fontweight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.94, subtitle, fontsize=9.5, color="#555", ha="left")
    fig.text(0.98, 0.01, FOOT, fontsize=7, color="#999", ha="right")
    fig.savefig(f"charts/{name}", bbox_inches="tight")
    plt.close(fig)
    print("wrote charts/" + name)


# 1 — Attention vs evidence scatter
fig, ax = plt.subplots(figsize=(10, 6.5))
gmax = np.log1p(df["views_growth"]).max()
for _, r in df.iterrows():
    size = 40 + 280 * (np.log1p(r["views_growth"]) / gmax)  # >0 for all growth>0
    ax.scatter(r["trials"] + 1, r["views_2026"], s=size,
               c=SEG_COLORS[r["segment"]], alpha=0.78, edgecolors="white",
               linewidths=0.8, zorder=3)
    ax.annotate(r["keyword"], (r["trials"] + 1, r["views_2026"]),
                xytext=(5, 4), textcoords="offset points", fontsize=8.5)
ax.set_xscale("log"); ax.set_yscale("log")
ax.axvline(df["trials"].median(), color="#999", ls=":", lw=1)
ax.axhline(df["views_2026"].median(), color="#999", ls=":", lw=1)
ax.text(0.98, 0.04, "bubble size = attention growth\nfirst 12 mo → last 12 mo", transform=ax.transAxes,
        ha="right", va="bottom", fontsize=8, color="#555",
        bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#ccc"))
ax.legend(handles=LEGEND_HANDLES(), frameon=True, fontsize=9, loc="upper left", title="Segment")
ax.set_xlabel("Registered clinical trials (log scale, +1 so zeros show)")
ax.set_ylabel("Wikipedia views / month, 2026 avg (log scale)")
finish(fig, "01_attention_vs_evidence.png",
       "Attention vs. evidence: the biohacking market, mapped",
       "15 biohacks · x = clinical trials registered · y = public attention (pageviews)")


# 2 — Mispricing ranking
d2 = df.sort_values("mispricing")
fig, ax = plt.subplots(figsize=(9, 6.5))
colors = [SEG_COLORS[s] for s in d2["segment"]]
bars = ax.barh(d2["keyword"], d2["mispricing"], color=colors, edgecolor="white", height=0.62)
ax.axvline(0, color="black", lw=1)
ax.set_xlim(-1.8, 2.35)
ax.set_xlabel("Mispricing  =  z(log attention) − z(log trials)   →  attention outruns evidence")
for b, v in zip(bars, d2["mispricing"]):
    ax.text(v + (0.07 if v >= 0 else -0.07), b.get_y() + b.get_height() / 2, f"{v:+.2f}",
            va="center", ha="left" if v >= 0 else "right", fontsize=8.5)
finish(fig, "02_mispricing_rank.png",
       "The mispricing leaderboard: where attention outruns the science",
       "Positive = more public attention than the trial record justifies")


# 3 — Attention trajectories, top 6
top6 = df.nlargest(6, "views_2026")["keyword"].tolist()
fig, ax = plt.subplots(figsize=(10.5, 5.5))
for kw in top6:
    s = monthly[monthly["keyword"] == kw].sort_values("date")
    ax.plot(s["date"], s["views"], lw=2, label=kw)
ax.legend(fontsize=9, ncol=3, loc="upper left", frameon=True)
ax.set_ylabel("Pageviews / month")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
finish(fig, "03_trajectories.png",
       "Six years of biohacking attention, month by month",
       "en.wikipedia pageviews · the six most-read biohack articles")


# 4 — Public attention growth vs research growth
fig, ax = plt.subplots(figsize=(9.5, 6.5))
bw = df[df["keyword"] == "breathwork"].iloc[0]
rest = df[df["keyword"] != "breathwork"]
for _, r in rest.iterrows():
    ax.scatter(r["papers_growth"], r["views_growth"], s=110,
               c=SEG_COLORS[r["segment"]], alpha=0.78, edgecolors="white",
               linewidths=0.8, zorder=3)
ax.set_xlim(0, 2.75); ax.set_ylim(0, 1.6)
for _, r in rest.iterrows():
    ax.annotate(r["keyword"], (r["papers_growth"], r["views_growth"]),
                xytext=(5, 4), textcoords="offset points", fontsize=8.5)
ax.annotate(f'breathwork → research {bw["papers_growth"]:.1f}×, off chart',
            xy=(2.7, 0.06), xytext=(1.9, 0.35),
            arrowprops=dict(arrowstyle="->", color="#7f7f7f"),
            fontsize=8.5, color="#555")
lim = [0, 2.75]
ax.plot(lim, [0, min(1.6, 2.75)], color="#999", ls="--", lw=1)
ax.text(2.6, 1.45, "public and research\nin lockstep", ha="right",
        fontsize=8, color="#888")
ax.set_xlabel("Research growth: PubMed papers 2026 ÷ 2020")
ax.set_ylabel("Attention growth: pageviews, first 12 mo → last 12 mo")
ax.legend(handles=LEGEND_HANDLES(), frameon=True, fontsize=9, loc="upper left", title="Segment")
finish(fig, "04_attention_vs_research_growth.png",
       "Where the public ran ahead of the literature",
       "Above the diagonal: attention grew faster than published research")


# 5 — Segment profiles
seg = json.load(open("data/segments.json"))
names = list(seg.keys())
fig, axes = plt.subplots(1, 3, figsize=(11, 4.2))
metrics = [("mean_views_2026", "Mean 2026 views/mo"),
           ("mean_trials", "Mean registered trials"),
           ("mean_mispricing", "Mean mispricing")]
for ax, (key, label) in zip(axes, metrics):
    vals = [seg[n][key] for n in names]
    ax.bar(names, vals, color=[SEG_COLORS[n] for n in names], edgecolor="white")
    ax.set_title(label, fontsize=10)
    ax.tick_params(axis="x", labelrotation=18, labelsize=8.5)
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:,.1f}", ha="center", va="bottom", fontsize=8.5)
finish(fig, "05_segments.png",
       "Four market segments, by the numbers",
       "quadrants split on median attention and median trial volume")
