"""Charts for The One-Person Internet (npm census, 2026-11-28).

Reads data/packages.csv, data/deps_top200.json and output/findings.json.
All charts are plain matplotlib, single muted palette, no seaborn dependency.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
OUT = BASE / "output"
CH = BASE / "charts"
CH.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#666666", "axes.labelcolor": "#222222",
    "xtick.color": "#333333", "ytick.color": "#333333",
    "figure.facecolor": "white", "axes.facecolor": "white",
})
NAVY = "#1f3a5f"; TEAL = "#2a9d8f"; AMBER = "#e9a03b"; RUST = "#c0563a"
GREY = "#8a8a8a"; LIGHT = "#d9e2ec"

NOW = datetime.now(timezone.utc)
ORDER = ["1", "2", "3-5", "6-10", "11+"]


def bucket(n):
    if n <= 1:
        return "1"
    if n == 2:
        return "2"
    if n <= 5:
        return "3-5"
    if n <= 10:
        return "6-10"
    return "11+"


def main():
    df = pd.read_csv(DATA / "packages.csv")
    df["last_publish"] = pd.to_datetime(df["last_publish"], utc=True, errors="coerce")
    df["age_days"] = (NOW - df["last_publish"]).dt.days
    df["abandoned"] = df["age_days"] > 730
    df["maint_bucket"] = df["n_maintainers"].apply(bucket)
    df = df.sort_values("weekly_downloads", ascending=False).reset_index(drop=True)
    top = df.head(1000).copy()
    total = top["weekly_downloads"].sum()
    with open(OUT / "findings.json") as f:
        F = json.load(f)

    # --- Chart 1: download-weighted vs package-count share by maintainer bucket
    g = top.groupby("maint_bucket").agg(
        n=("name", "count"), dl=("weekly_downloads", "sum")).reindex(ORDER)
    x = np.arange(len(ORDER)); w = 0.38
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - w / 2, g["dl"] / total * 100, w, label="Share of weekly downloads",
           color=NAVY)
    ax.bar(x + w / 2, g["n"] / len(top) * 100, w, label="Share of packages (count)",
           color=TEAL)
    for i, b in enumerate(ORDER):
        ax.text(i - w / 2, g["dl"].iloc[i] / total * 100 + 1,
                f"{g['dl'].iloc[i] / total * 100:.0f}%", ha="center", fontsize=10,
                fontweight="bold")
        ax.text(i + w / 2, g["n"].iloc[i] / len(top) * 100 + 1,
                f"{g['n'].iloc[i] / len(top) * 100:.0f}%", ha="center", fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels([f"{b} maintainer{'s' if b != '1' else ''}"
                                          for b in ORDER])
    ax.set_ylabel("Share of the top 1,000 npm packages (%)")
    ax.set_title("Who maintains the code you actually download?\n"
                 "More than half of all downloads in the top 1,000 run through one person",
                 loc="left", fontsize=12, fontweight="bold")
    ax.legend(frameon=False, loc="upper right")
    ax.set_ylim(0, max(g["dl"] / total * 100) * 1.25)
    fig.tight_layout(); fig.savefig(CH / "01_maintainer_buckets.png", dpi=150)
    plt.close(fig)

    # --- Chart 2: abandonment rate + abandoned download share by bucket
    ab = top.groupby("maint_bucket").apply(
        lambda d: pd.Series({
            "rate": d["abandoned"].mean() * 100,
            "dl_share_ab": d.loc[d["abandoned"], "weekly_downloads"].sum()
                             / d["weekly_downloads"].sum() * 100,
        })).reindex(ORDER)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - w / 2, ab["rate"], w, label="% of packages abandoned",
           color=RUST)
    ax.bar(x + w / 2, ab["dl_share_ab"], w,
           label="% of bucket downloads via abandoned packages", color=AMBER)
    for i, b in enumerate(ORDER):
        ax.text(i - w / 2, ab["rate"].iloc[i] + 1, f"{ab['rate'].iloc[i]:.0f}%",
                ha="center", fontsize=10, fontweight="bold")
        ax.text(i + w / 2, ab["dl_share_ab"].iloc[i] + 1,
                f"{ab['dl_share_ab'].iloc[i]:.0f}%", ha="center", fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels([f"{b} maintainer{'s' if b != '1' else ''}"
                                          for b in ORDER])
    ax.set_ylabel("%")
    ax.set_title("Abandonment is a solo-maintainer problem\n"
                 "Solo packages go quiet most often, and their downloads keep flowing",
                 loc="left", fontsize=12, fontweight="bold")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12),
              ncol=2, fontsize=9)
    ax.set_ylim(0, max(ab["rate"].max(), ab["dl_share_ab"].max()) * 1.25)
    fig.tight_layout(); fig.savefig(CH / "02_abandonment_by_bucket.png", dpi=150)
    plt.close(fig)

    # --- Chart 3: concentration curve (Lorenz-style) for top 1000
    cum = np.cumsum(top["weekly_downloads"].values) / total * 100
    ranks = np.arange(1, len(top) + 1)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(ranks, cum, color=NAVY, lw=2)
    ax.fill_between(ranks, cum, alpha=0.08, color=NAVY)
    for k in (10, 50, 100, 500):
        ax.scatter([k], [cum[k - 1]], color=RUST, zorder=5)
        ax.annotate(f"top {k}: {cum[k - 1]:.0f}%", (k, cum[k - 1]),
                    textcoords="offset points", xytext=(8, 6), fontsize=10)
    ax.axhline(50, color=GREY, ls="--", lw=1)
    ax.set_xscale("log")
    ax.set_xlabel("Package rank by weekly downloads (log scale)")
    ax.set_ylabel("Cumulative share of top-1,000 downloads (%)")
    ax.set_title("The registry looks decentralised. By downloads, it is not.\n"
                 "A handful of packages carry most of the internet's installs",
                 loc="left", fontsize=12, fontweight="bold")
    ax.set_xlim(1, 1000); ax.set_ylim(0, 102)
    fig.tight_layout(); fig.savefig(CH / "03_concentration.png", dpi=150)
    plt.close(fig)

    # --- Chart 4: survival curve — share of packages still "alive" vs months
    # since last publish, by maintainer bucket (empirical survival from age).
    fig, ax = plt.subplots(figsize=(9, 5))
    months = np.arange(0, 61)
    colors = {b: c for b, c in zip(ORDER, [RUST, AMBER, TEAL, NAVY, "#6a4c93"])}
    for b in ORDER:
        sub = top[top["maint_bucket"] == b]
        ages_m = sub["age_days"].values / 30.44
        alive = np.array([np.mean(ages_m <= m) for m in months])
        ax.plot(months, alive * 100, label=f"{b} maintainer{'s' if b != '1' else ''}",
                color=colors[b], lw=2)
    ax.axvline(24, color=GREY, ls="--", lw=1)
    ax.text(25, 8, "24 months:\nour 'abandoned' line", fontsize=9, color="#555555")
    ax.set_xlabel("Months since last publish")
    ax.set_ylabel("Share of packages published within the last N months (%)")
    ax.set_title("How fast packages go quiet, by maintainer count\n"
                 "Solo-maintained packages decay fastest — the gap opens within a year",
                 loc="left", fontsize=12, fontweight="bold")
    ax.legend(frameon=False, loc="lower right")
    ax.set_xlim(0, 60); ax.set_ylim(0, 102)
    fig.tight_layout(); fig.savefig(CH / "04_survival_by_maintainers.png", dpi=150)
    plt.close(fig)

    # --- Chart 5: blast radius — how solo-dependent are the top 200?
    # Bucket every top-200 package by the share of its direct deps that are
    # single-maintainer, including packages with no direct deps at all.
    with open(DATA / "deps_top200.json") as f:
        deps_all = json.load(f)
    top200_names = set(df.head(200)["name"])
    deps = {k: v for k, v in deps_all.items() if k in top200_names}
    pool = df.set_index("name")
    cats = {"No direct dependencies": 0, "Deps, none solo": 0,
            "Some deps solo": 0, "All deps solo": 0, "Has an abandoned dep": 0}
    for parent, children in deps.items():
        known = [c for c in children if c in pool.index]
        if not children:
            cats["No direct dependencies"] += 1
        elif not known:
            continue
        else:
            n_solo = sum(1 for c in known if pool.loc[c, "n_maintainers"] <= 1)
            if n_solo == 0:
                cats["Deps, none solo"] += 1
            elif n_solo == len(known):
                cats["All deps solo"] += 1
            else:
                cats["Some deps solo"] += 1
        if any(c in pool.index and bool(pool.loc[c, "abandoned"]) for c in children):
            cats["Has an abandoned dep"] += 1
    labels = ["No direct\ndependencies", "Deps, none\nsolo",
              "Some deps\nsolo", "All deps\nsolo"]
    vals = [cats["No direct dependencies"], cats["Deps, none solo"],
            cats["Some deps solo"], cats["All deps solo"]]
    colors5 = [LIGHT, TEAL, AMBER, NAVY]
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(labels, vals, color=colors5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 3, str(v),
                ha="center", fontsize=12, fontweight="bold")
    ax.set_ylabel("Top-200 packages")
    ax.set_title("Blast radius: the big packages sit on solo maintainers too\n"
                 f"{cats['Has an abandoned dep']} of the top 200 have a direct "
                 "dependency untouched for 2+ years",
                 loc="left", fontsize=12, fontweight="bold")
    ax.set_ylim(0, max(vals) * 1.25)
    fig.tight_layout(); fig.savefig(CH / "05_blast_radius.png", dpi=150)
    plt.close(fig)

    print("charts written:", sorted(p.name for p in CH.glob("*.png")))


if __name__ == "__main__":
    main()
