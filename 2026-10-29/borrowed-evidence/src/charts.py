"""Charts for borrowed-evidence. Style: clean, single accent, no chartjunk."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
ACCENT, GREY = "#c2410c", "#94a3b8"
s = pd.read_csv(ROOT / "data" / "summary.csv")

# 01: patient-only share, sorted, with young-healthy dots
d = s.sort_values("pct_patient_only")
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(d["intervention"], d["pct_patient_only"], color=ACCENT, alpha=.85,
        label="Trials that exclude healthy volunteers")
ax.scatter(d["pct_young_healthy"], d["intervention"], color="#0f172a", zorder=5,
           label="Trials enrolling healthy adults under 40")
ax.axvline(50, color=GREY, ls="--", lw=1)
for i, (_, r) in enumerate(d.iterrows()):
    ax.text(r["pct_patient_only"] + 1.5, i, f"{r['pct_patient_only']:.0f}%", va="center")
ax.set_xlim(0, 108)
ax.set_xlabel("% of registered trials")
ax.set_title("Most biohack trials do not accept healthy volunteers at all")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), fontsize=9, ncol=1)
fig.tight_layout(); fig.savefig(ROOT / "charts" / "01_patient_share.png"); plt.close()

# 02: young-healthy share ranking
d = s.sort_values("pct_young_healthy")
fig, ax = plt.subplots(figsize=(9, 6))
colors = [ACCENT if v < 30 else "#0f172a" for v in d["pct_young_healthy"]]
ax.barh(d["intervention"], d["pct_young_healthy"], color=colors)
for i, v in enumerate(d["pct_young_healthy"]):
    ax.text(v + 1.5, i, f"{v:.0f}%", va="center")
ax.set_xlim(0, 95)
ax.set_xlabel("% of trials enrolling healthy adults under 40")
ax.set_title("The 'healthy 30-year-old' evidence base, by biohack")
fig.tight_layout(); fig.savefig(ROOT / "charts" / "02_young_healthy.png"); plt.close()

# 03: trend, ex-rapamycin, through 2025
t = pd.read_csv(ROOT / "data" / "trend_by_category.csv", index_col=0)
t = t[(t.index >= 2010) & (t.index <= 2025)]
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(t.index, t.sum(axis=1), color=ACCENT, marker="o", ms=4)
ax.set_xlabel("Trial start year (rapamycin excluded: its pagination was capped)")
ax.set_ylabel("Trials started")
ax.set_title("The biohacking trial boom did not fix the transfer gap")
fig.tight_layout(); fig.savefig(ROOT / "charts" / "03_trend.png"); plt.close()

# 04: literature size vs transfer (log n vs young-healthy share)
fig, ax = plt.subplots(figsize=(9, 5))
ax.scatter(s["n"], s["pct_young_healthy"], s=90, color=ACCENT)
for _, r in s.iterrows():
    ax.annotate(r["intervention"], (r["n"], r["pct_young_healthy"]),
                fontsize=8, xytext=(4, 3), textcoords="offset points")
ax.set_xscale("log")
ax.set_xlabel("Registered trials (log scale)")
ax.set_ylabel("% enrolling healthy adults under 40")
ax.set_title("The bigger the literature, the more borrowed it tends to be")
corr = np.corrcoef(np.log(s["n"]), s["pct_young_healthy"])[0, 1]
ax.text(0.03, 0.95, f"r = {corr:.2f} (log trials vs young-healthy share)",
        transform=ax.transAxes, fontsize=10)
fig.tight_layout(); fig.savefig(ROOT / "charts" / "04_size_vs_transfer.png"); plt.close()

# 05: category patient share
df = pd.read_csv(ROOT / "data" / "trials_enriched.csv")
cat = df.groupby("category").apply(
    lambda g: pd.Series({"n": len(g),
        "patient": (g[g["healthy_volunteers"].notna()]["healthy_volunteers"] == False).mean() * 100,
        "young": g["young_healthy"].mean() * 100}), include_groups=False)
cat = cat.sort_values("patient")
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.barh(cat.index, cat["patient"], color=ACCENT, alpha=.85, label="Patient-only")
ax.scatter(cat["young"], cat.index, color="#0f172a", zorder=5, label="Young-healthy")
ax.set_xlabel("% of trials")
ax.set_title("No category escapes it; longevity drugs are the most borrowed")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), fontsize=9, ncol=2)
fig.tight_layout(); fig.savefig(ROOT / "charts" / "05_category.png"); plt.close()
print("charts done; size-vs-transfer r =", round(corr, 2))
print(cat.round(1))
