#!/usr/bin/env python3
"""
Analyze the collected EDM data and produce charts + summary stats.

Reads:
  data/subgenre_counts.json   (MusicBrainz release-group counts)
  data/festival_attendance.csv (Wikipedia attendance tables)
  data/djmag_no1.csv          (DJ Mag Top 100 #1s, from Wikipedia)

Writes figures/*.png and prints key statistics for the write-up.
"""
import csv
import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.rcParams.update({"figure.dpi": 150, "font.size": 10})
BASE = Path(__file__).resolve().parent.parent
DATA, FIG = BASE / "data", BASE / "figures"
FIG.mkdir(exist_ok=True)

# ---------------------------------------------------------------- subgenres
# (Discogs; see src/01d_discogs_styles.py. An earlier MusicBrainz attempt was
#  abandoned after the API tarpitted sustained polling.)
HAVE_SUBGENRES = (DATA / "discogs_style_counts.json").exists()
if HAVE_SUBGENRES:
    with open(DATA / "discogs_style_counts.json") as f:
        payload = json.load(f)
    raw = payload["counts"]
    # require reasonably complete data (>=90% of the 286 style-year pairs, no failures)
    n_ok = sum(1 for v in raw.values() for x in v.values() if x != -1)
    HAVE_SUBGENRES = n_ok >= 0.9 * 11 * 26
    if not HAVE_SUBGENRES:
        print(f"subgenre data incomplete ({n_ok}/286 ok) - skipping subgenre charts")

if HAVE_SUBGENRES:
    df = pd.DataFrame(raw, dtype=float).sort_index()
    df.index = df.index.astype(int)
    plot_df = df.replace(-1, float("nan"))

    print("=== subgenre peak years & latest values (Discogs) ===")
    for col in plot_df.columns:
        s = plot_df[col].dropna()
        peak_year = int(s.idxmax())
        latest = s.get(2024, float("nan"))
        print(
            f"{col:18s} peak {peak_year} ({int(s.max()):6d} releases) | "
            f"2024: {int(latest):6d} | "
            f"change since peak: {(latest / s.max() - 1) * 100:+.0f}%"
        )

    # Fig 1: absolute counts
    fig, ax = plt.subplots(figsize=(11, 6))
    for col in plot_df.columns:
        ax.plot(plot_df.index, plot_df[col], label=col, linewidth=1.8)
    ax.set_title("EDM subgenre output over time: new releases per year (Discogs)", fontsize=13, weight="bold")
    ax.set_xlabel("Release year")
    ax.set_ylabel("Releases catalogued with style tag")
    ax.legend(ncol=3, fontsize=8, loc="upper left")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "fig1_subgenre_counts.png")
    plt.close(fig)

    # Fig 2: normalized share (stacked area) -> the genre cycle
    share = plot_df.div(plot_df.sum(axis=1), axis=0).fillna(0)
    order = share.mean().sort_values(ascending=False).index
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.stackplot(share.index, *[share[c] for c in order], labels=order, alpha=0.85)
    ax.set_title("The EDM genre cycle: share of new releases by style", fontsize=13, weight="bold")
    ax.set_xlabel("Release year")
    ax.set_ylabel("Share of catalogued releases")
    ax.legend(ncol=3, fontsize=8, loc="upper left")
    ax.set_xlim(2000, 2025)
    fig.tight_layout()
    fig.savefig(FIG / "fig2_subgenre_share.png")
    plt.close(fig)

# ---------------------------------------------------------------- DJ Mag
dj = pd.read_csv(DATA / "djmag_no1.csv")
wins = dj["winner"].value_counts()
countries = dj["country"].value_counts()
print("\n=== DJ Mag #1 wins (1997-2025) ===")
print(wins.to_string())
print("\n=== #1s by country ===")
print(countries.to_string())
print(f"\nDutch winners: {(dj['country'] == 'Netherlands').sum()}/{len(dj)}")

ERAS = [
    (1997, 2001, "UK superclub era", "#7b9e6b"),
    (2002, 2010, "Trance era", "#5b8dd9"),
    (2011, 2012, "EDM goes mainstream", "#c9a13b"),
    (2013, 2019, "Big-room era", "#d95f5f"),
    (2020, 2025, "Guetta/Garrix duopoly", "#9b6bd3"),
]

def era_of(year):
    for lo, hi, name, color in ERAS:
        if lo <= year <= hi:
            return name, color
    return "", "#999"

fig, ax = plt.subplots(figsize=(12, 4.8))
ys = {w: i for i, w in enumerate(dj["winner"].unique())}
for _, r in dj.iterrows():
    name, color = era_of(r["year"])
    ax.scatter(r["year"], ys[r["winner"]], s=100, color=color, zorder=3, edgecolor="white")
ax.set_yticks(list(ys.values()))
ax.set_yticklabels(list(ys.keys()), fontsize=9)
from matplotlib.patches import Patch
legend_handles = [Patch(color=color, alpha=0.35, label=f"{name} ({lo}-{hi})")
                  for lo, hi, name, color in ERAS]
for lo, hi, name, color in ERAS:
    ax.axvspan(lo - 0.5, hi + 0.5, color=color, alpha=0.12)
ax.set_title("Who ruled dance music? DJ Mag #1 DJ, 1997-2025", fontsize=13, weight="bold")
ax.set_xlabel("Year")
ax.set_xlim(1996.5, 2025.5)
ax.grid(axis="x", alpha=0.25)
ax.legend(handles=legend_handles, fontsize=8, loc="upper left", ncols=2)
fig.tight_layout()
fig.savefig(FIG / "fig3_djmag_timeline.png")
plt.close(fig)

# ---------------------------------------------------------------- festivals
fest = pd.read_csv(DATA / "festival_attendance.csv")
print("\n=== festival growth ===")
for name, g in fest.groupby("festival"):
    g = g.sort_values("year")
    first, last = g.iloc[0], g.iloc[-1]
    print(
        f"{name}: {first['year']} {first['attendance']:,} -> "
        f"{last['year']} {last['attendance']:,} ({last['attendance']/first['attendance']:.0f}x)"
    )

fig, ax = plt.subplots(figsize=(11, 6))
for name, g in fest.groupby("festival"):
    g = g.sort_values("year")
    ax.plot(g["year"], g["attendance"], marker="o", linewidth=2.2, label=name)
ax.set_title("From warehouses to mega-festivals: attendance growth", fontsize=13, weight="bold")
ax.set_xlabel("Year")
ax.set_ylabel("Total attendance")
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
ax.legend()
ax.grid(alpha=0.25)
ax.annotate(
    "Ultra 2013: two weekends",
    xy=(2013, 330000), xytext=(2008, 420000),
    arrowprops=dict(arrowstyle="->", color="gray"), fontsize=9, color="gray",
)
fig.tight_layout()
fig.savefig(FIG / "fig4_festival_growth.png")
plt.close(fig)

print("\nfigures written to", FIG)
