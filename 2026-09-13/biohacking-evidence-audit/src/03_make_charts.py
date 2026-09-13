"""
Part 3: Charts. Reads data/trials_summary.json + sleep CSVs, writes charts/.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
DATA = HERE / "data"
CH = HERE / "charts"
CH.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 150, "savefig.bbox": "tight",
})
ACCENT = "#1f7a8c"
WARM = "#e07a5f"

trials = json.loads((DATA / "trials_summary.json").read_text())
trials = sorted(trials, key=lambda s: s["interventional"], reverse=True)
labels = [t["label"] for t in trials]
interv = np.array([t["interventional"] for t in trials])
total = np.array([t["total_registered"] for t in trials])
obs = total - interv

# 1) Trial volume by biohack
fig, ax = plt.subplots(figsize=(10, 7))
y = np.arange(len(labels))
ax.barh(y, interv, color=ACCENT, label="Interventional trials")
ax.barh(y, obs, left=interv, color="#cfd8dc", label="Observational / other")
for i, v in enumerate(total):
    ax.text(v + 40, i, f"{v:,}", va="center", fontsize=10)
ax.set_yticks(y); ax.set_yticklabels(labels)
ax.set_xlabel("Registered clinical trials (ClinicalTrials.gov)")
ax.set_title("How much clinical research exists per popular biohack?")
ax.legend(frameon=False)
ax.invert_yaxis()
fig.savefig(CH / "01_trial_volume.png"); plt.close(fig)

# 2) Evidence maturity: completed share vs results-posted share, sized by enrollment
fig, ax = plt.subplots(figsize=(10, 7))
x = np.array([t["completed"] / max(t["records_retrieved"], 1) for t in trials])
y2 = np.array([t["with_results"] / max(t["records_retrieved"], 1) for t in trials])
size = np.array([t["median_enrollment"] or 30 for t in trials])
sc = ax.scatter(x, y2, s=np.clip(np.sqrt(size) * 9, 40, 900),
                c=np.log10(np.maximum(interv, 1)), cmap="YlGnBu", alpha=0.85,
                edgecolors="white")
for i, lab in enumerate(labels):
    short = lab.split(" / ")[0].split(" for ")[0]
    dy = 6 if i % 2 == 0 else -16
    ax.annotate(short, (x[i], y2[i]), fontsize=8.5,
                xytext=(6, dy), textcoords="offset points")
ax.set_xlabel("Share of trials completed")
ax.set_ylabel("Share of trials with posted results")
ax.set_title("Evidence maturity: completion vs. published results\n"
             "(bubble size ~ median enrollment; color ~ trial volume)")
ax.set_xlim(0.3, 0.9); ax.set_ylim(-0.02, 0.35)
cbar = fig.colorbar(sc, ax=ax); cbar.set_label("log10 interventional trials")
fig.savefig(CH / "02_evidence_maturity.png"); plt.close(fig)

# 3) Growth curves for the three biggest areas
fig, ax = plt.subplots(figsize=(10, 6))
top = ["creatine supplementation", "mindfulness meditation",
       "time restricted eating", "intermittent fasting", "ketogenic diet"]
seen = set()
for t in trials:
    key = t["term"]
    if key not in top or key in seen:
        continue
    seen.add(key)
    yrs = t["by_start_year"]
    years = sorted(int(k) for k in yrs if k.isdigit() and 2000 <= int(k) <= 2026)
    cum = np.cumsum([yrs[str(y)] for y in years])
    ax.plot(years, cum, marker="o", ms=3, label=t["label"])
ax.set_xlabel("Trial start year"); ax.set_ylabel("Cumulative registered trials")
ax.set_title("The biohacking research boom: cumulative trials by start year")
ax.legend(frameon=False, fontsize=9)
fig.savefig(CH / "03_research_growth.png"); plt.close(fig)

# 4) Sleep vs health (NHANES) — continuous measures + hypertension prevalence
h = pd.read_csv(DATA / "health_by_sleep.csv")
order = ["<5h", "5-6h", "6-7h", "7-8h", "8-9h", "9h+"]
h = h.set_index("sleep_bin").loc[order].reset_index()
fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), sharex=True)
panels = [
    (axes[0], "BMXBMI", "mean", "Mean BMI (measured)", None),
    (axes[1], "LBXGH", "mean", "Mean HbA1c (%)", None),
    (axes[2], "hypertension", "mean", "Told had hypertension (%)", 100),
]
for ax, base, _, title, scale in panels:
    mcol, scol = f"{base}_mean", f"{base}_se"
    mult = scale or 1
    ax.errorbar(order, h[mcol] * mult, yerr=h[scol] * mult * 1.96,
                marker="o", color=ACCENT, capsize=4, lw=2)
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=25)
axes[0].set_ylabel("Weighted mean / % of US adults")
fig.suptitle("Sleep duration vs. chronic disease (NHANES 2017–2020, n=9,110 adults)\n"
             "Both short (<6h) and long (9h+) sleepers fare worse than 7–9h sleepers",
             fontsize=12)
fig.tight_layout()
fig.savefig(CH / "04_sleep_health.png"); plt.close(fig)

# 5) Mean sleep by age group
a = pd.read_csv(DATA / "mean_sleep_by_age.csv")
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(a.age_group, a.mean_sleep, yerr=a.se * 1.96, color=ACCENT,
       capsize=5, error_kw={"ecolor": "#333"})
ax.axhline(7.5, ls="--", color=WARM, label="7.5h reference")
for i, v in enumerate(a.mean_sleep):
    ax.text(i, v + 0.12, f"{v:.2f}h", ha="center", fontsize=10)
ax.set_ylabel("Mean sleep hours (survey-weighted)")
ax.set_title("Average sleep by age group (NHANES 2017–2020)")
ax.legend(frameon=False)
fig.savefig(CH / "05_sleep_by_age.png"); plt.close(fig)

print("charts written to", CH)
