#!/usr/bin/env python3
"""Build #71 — The Side-Effect Shelf. Charts.
Layout rule: title via ax.set_title (pad), subtitle as a two-line caption at
the bottom via fig.text, tight_layout with rect reserving the bottom strip.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
CH = BASE / "charts"
CH.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#666666", "axes.labelcolor": "#222222",
    "figure.dpi": 150,
})
INK = "#1a1a2e"; ACCENT = "#e94560"; MUTED = "#8a8a9e"; TEAL = "#0f766e"
AMBER = "#b45309"


def finish(fig, ax, title, caption, fname, bottom=0.09):
    ax.set_title(title, fontsize=13, fontweight="bold", color=INK, loc="left", pad=10)
    fig.text(0.07, 0.015, caption, fontsize=9, color=MUTED, ha="left", va="bottom")
    plt.tight_layout(rect=[0, bottom, 1, 1])
    plt.savefig(CH / fname)
    plt.close()


summary = json.loads((BASE / "data" / "faers_summary.json").read_text())
results = json.loads((BASE / "output" / "results.json").read_text())
df = pd.read_csv(BASE / "data" / "compound_table.csv")
trend = pd.read_csv(BASE / "data" / "trend_table.csv")

# 1. Methylene blue's reaction profile --------------------------------------
mb = summary["methylene blue"]["top_reactions"][:10]
short = {"SEROTONIN SYNDROME": "Serotonin syndrome", "DRUG INTERACTION": "Drug interaction",
         "DRUG INEFFECTIVE": "Drug ineffective", "HYPOTENSION": "Hypotension",
         "OFF LABEL USE": "Off-label use", "TOXICITY TO VARIOUS AGENTS": "Toxicity to various agents",
         "OVERDOSE": "Overdose", "INTENTIONAL OVERDOSE": "Intentional overdose",
         "ENCEPHALOPATHY": "Encephalopathy", "CONFUSIONAL STATE": "Confusional state"}
labels = [short.get(r["term"], r["term"].title()) for r in mb]
vals = [r["count"] for r in mb]
fig, ax = plt.subplots(figsize=(8.5, 5.2))
colors = [ACCENT if "Serotonin" in l else (AMBER if "Drug interaction" in l else TEAL)
          for l in labels]
ax.barh(labels[::-1], vals[::-1], color=colors[::-1], height=0.62)
for i, v in enumerate(vals[::-1]):
    ax.text(v + 8, i, f"{v}", va="center", fontsize=10, fontweight="bold", color=INK)
ax.set_xlabel("Reports listing this reaction")
ax.set_xlim(0, 520)
finish(fig, ax, "Methylene blue's #1 adverse event is serotonin syndrome",
       "Reports naming methylene blue as the suspect drug, FDA FAERS (n = 1,564).\n"
       "455 reports (29%) list serotonin syndrome; 338 list a drug interaction.",
       "01_mb_reactions.png")

# 2. The shelf, counted -------------------------------------------------------
shelf = df[(df.group == "shelf") & (df.reports_suspect >= 80)].sort_values("reports_suspect")
fig, ax = plt.subplots(figsize=(8.5, 5.4))
colors = [ACCENT if c == "methylene blue" else TEAL for c in shelf.compound]
ax.barh(shelf.compound, shelf.reports_suspect, color=colors, height=0.62)
for i, (_, r) in enumerate(shelf.iterrows()):
    ax.text(r.reports_suspect + 40, i,
            f"{int(r.reports_suspect):,} reports · {r.serious_share:.0%} serious · "
            f"{int(r.deaths)} deaths",
            va="center", fontsize=9.5, color=INK)
ax.set_xlabel("Suspect reports")
ax.set_xlim(0, 3650)
finish(fig, ax, "The shelf, counted",
       "Adverse-event reports naming each molecule as the suspect drug, FDA FAERS 2004–Oct 2026.\n"
       "9,386 reports across the shelf; 62% serious; 562 deaths named.",
       "02_shelf_overview.png")

# 3. Indexed trend: reports grew faster than the database --------------------
piv = trend.pivot(index="year", columns="compound", values="reports")
faers_idx = pd.Series({2012: 1.0, 2015: 1223001 / 551378, 2020: 1421775 / 551378,
                       2025: 1386644 / 551378})
comps = ["berberine", "quercetin", "methylene blue", "creatine", "melatonin", "caffeine"]
fig, ax = plt.subplots(figsize=(8.5, 5.0))
for c in comps:
    s = piv[c].dropna()
    idx = s / s.loc[2012]
    ax.plot(s.index, idx, "o-", lw=2, ms=4,
            color=ACCENT if c in ("berberine", "quercetin") else
                  (INK if c == "methylene blue" else MUTED),
            label=f"{c} ({idx.loc[2025]:.0f}x)")
ax.plot(faers_idx.index, faers_idx.values, "s--", lw=1.6, ms=4, color=MUTED,
        label="all FAERS reports (2.5x)")
ax.set_ylabel("Reports, indexed (2012 = 1)")
ax.set_xlabel("Year received")
ax.set_xlim(2012, 2025)
ax.legend(frameon=False, fontsize=9, loc="upper left")
finish(fig, ax, "The shelf's reports grew far faster than the database",
       "Reports per year, indexed to 2012 = 1. 2026 is a partial year (FAERS data through\n"
       "Oct 28) and is excluded. Berberine 20.6x, quercetin 31.4x, creatine 13.9x.",
       "03_trend.png")

# 4. Evidence vs reports scatter ---------------------------------------------
fig, ax = plt.subplots(figsize=(8.5, 5.6))
plot = df.copy()
plot["x"] = plot.pubmed_rcts.replace(0, np.nan)
plot["y"] = plot.reports_suspect
for grp, color, marker, alpha in [("shelf", ACCENT, "o", 0.9),
                                  ("control", MUTED, "s", 0.55),
                                  ("pharma", "#c9c9d6", "D", 0.8)]:
    sub = plot[plot.group == grp]
    ax.scatter(sub.x, sub.y, c=color, marker=marker, s=90, alpha=alpha,
               edgecolors="white", linewidths=0.7, label=grp)
zero = plot[plot.pubmed_rcts == 0]
ax.scatter([0.7] * len(zero), zero.y, c=ACCENT, marker="o", s=90,
           edgecolors="white", linewidths=0.7)
offsets = {"berberine": (6, 4), "methylene blue": (6, -16), "pregnenolone": (-92, 6),
           "creatine": (6, 4), "DHEA": (6, 4), "quercetin": (6, 8),
           "resveratrol": (-78, -16), "ashwagandha": (-88, -16),
           "vitamin D": (-72, 6), "metformin": (6, 4), "semaglutide": (6, 4)}
for _, r in plot.iterrows():
    if r.compound in offsets:
        dx, dy = offsets[r.compound]
        ax.annotate(r.compound, (r.x, r.y), textcoords="offset points",
                    xytext=(dx, dy), fontsize=9, color=INK)
for _, r in zero.iterrows():
    ax.annotate(f"{r.compound} (0 RCTs)", (0.7, r.y), textcoords="offset points",
                xytext=(6, 4), fontsize=9, color=ACCENT)
xs = np.logspace(-0.2, 3.6, 50)
ax.plot(xs, xs, ls=":", color=MUTED, lw=1.2)
ax.text(60, 130, "1 report per RCT", fontsize=9, color=MUTED, rotation=32)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(0.5, 6000); ax.set_ylim(2, 600000)
ax.set_xlabel("Published randomized controlled trials (PubMed)")
ax.set_ylabel("FAERS suspect reports (log scale)")
ax.legend(frameon=False, fontsize=9, loc="lower right")
finish(fig, ax, "Evidence density is the discriminator",
       "Creatine: 2,872 RCTs, 1,139 reports. Pregnenolone: 38 RCTs, 392 reports.\n"
       "BPC-157 and lithium orotate: 0 RCTs, reports anyway.",
       "04_evidence_scatter.png", bottom=0.10)

# 5. Who files the report -----------------------------------------------------
rep = df[df.reports_suspect >= 80].sort_values("consumer_share")
fig, ax = plt.subplots(figsize=(8.5, 5.4))
colors = [ACCENT if c == "methylene blue" else
          (AMBER if c == "sirolimus" else TEAL) for c in rep.compound]
ax.barh(rep.compound, rep.consumer_share * 100, color=colors, height=0.62)
for i, (_, r) in enumerate(rep.iterrows()):
    ax.text(r.consumer_share * 100 + 1.5, i, f"{r.consumer_share:.0%}",
            va="center", fontsize=10, fontweight="bold", color=INK)
ax.set_xlabel("% of reports filed by consumers")
ax.set_xlim(0, 100)
finish(fig, ax, "Who files the report: the shelf's signal comes from consumers",
       "Share of reports filed by consumers (qualification 5). Methylene blue's reports\n"
       "come from clinicians; the supplement shelf's from the people taking it.",
       "05_reporters.png")
print("charts written:", sorted(p.name for p in CH.glob("*.png")))
