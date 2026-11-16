"""Charts for build #66 — The 30-Gram Rule Is a Lab Artifact."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "..", "output")
CH = os.path.join(BASE, "..", "charts")
os.makedirs(CH, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#666666", "axes.labelcolor": "#222222",
    "figure.dpi": 150,
})
INK = "#1a1a2e"; ACCENT = "#e94560"; MUTED = "#8a8a9e"; TEAL = "#0f766e"

res = json.load(open(os.path.join(OUT, "results.json")))
sens = json.load(open(os.path.join(OUT, "sensitivity.json")))
dxa = pd.read_csv(os.path.join(OUT, "analytic_dxa.csv"))
d = res["descriptives"]

# 1. Protein by meal of day -------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 4.6))
meals = ["breakfast", "lunch", "dinner", "snack"]
grams = [d["weighted_mean_by_meal"][m] for m in meals]
pct25 = [d["pct_breakfast_ge25"], d["pct_lunch_ge25"], d["pct_dinner_ge25"], np.nan]
bars = ax.bar(meals, grams, color=[ACCENT, TEAL, TEAL, MUTED], width=0.62)
ax.axhline(25, color=ACCENT, ls="--", lw=1.2, alpha=0.8)
ax.text(3.45, 26.2, "25 g 'threshold'", color=ACCENT, fontsize=10, ha="right")
for b, g, p in zip(bars, grams, pct25):
    ax.text(b.get_x() + b.get_width() / 2, g + 1.2, f"{g:.1f} g",
            ha="center", fontsize=12, fontweight="bold", color=INK)
    if not np.isnan(p):
        ax.text(b.get_x() + b.get_width() / 2, -4.6, f"{p:.0f}% clear 25 g",
                ha="center", fontsize=10, color=MUTED)
ax.set_ylim(0, 44)
ax.set_ylabel("Mean protein (g), 2-day average")
ax.set_title("America eats its protein at dinner — breakfast is a desert",
             fontsize=13, fontweight="bold", color=INK, loc="left")
ax.text(0, -0.24, "NHANES 2013–2014, adults 20–59, survey-weighted (n=2,558). "
        "Only 14% of adults clear 25 g at breakfast.",
        transform=ax.transAxes, fontsize=9, color=MUTED)
plt.tight_layout(); plt.savefig(f"{CH}/01_protein_by_meal.png"); plt.close()

# 2. The flatline: adjusted ALMI by meals >= 30 g ---------------------------
adj = res["regressions"]["adjusted_ALMI_by_meals_ge30"]
fig, ax = plt.subplots(figsize=(8, 4.6))
x = [a["meals_ge30"] for a in adj]
y = [a["adj_ALMI"] for a in adj]
n = [a["n"] for a in adj]
ax.plot(x, y, "o-", color=ACCENT, lw=2.5, ms=9)
for xi, yi, ni in zip(x, y, n):
    ax.annotate(f"{yi:.2f}\n(n={ni:,})", (xi, yi), textcoords="offset points",
                xytext=(0, 14), ha="center", fontsize=10, color=INK)
ax.set_xticks(x)
ax.set_xticklabels(["0 meals ≥30 g", "1 meal", "2 meals", "3 meals"])
ax.set_ylabel("Adjusted appendicular lean mass index (kg/m²)")
ax.set_ylim(7.6, 8.1)
ax.set_title("How many meals clear 30 g of protein? It makes no difference.",
             fontsize=13, fontweight="bold", color=INK, loc="left")
ax.text(0, -0.24, "DXA-measured lean mass, adjusted for total protein, age, sex, BMI, calories,\n"
        "activity and race. Coefficient on meals≥30 g: −0.0005, p = 0.99.",
        transform=ax.transAxes, fontsize=9, color=MUTED)
plt.tight_layout(); plt.savefig(f"{CH}/02_flatline.png"); plt.close()

# 3. Breakfast protein: distribution + ALMI by quartile ----------------------
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
ax = axes[0]
ax.hist(dxa["breakfast"], bins=np.arange(0, 65, 2.5), color=TEAL, alpha=0.85)
ax.axvline(25, color=ACCENT, ls="--", lw=1.5)
ax.axvline(dxa["breakfast"].mean(), color=INK, ls=":", lw=1.5)
ax.text(26, ax.get_ylim()[1] * 0.92, "25 g", color=ACCENT, fontsize=10)
ax.text(dxa["breakfast"].mean() + 1, ax.get_ylim()[1] * 0.7,
        f"mean {dxa['breakfast'].mean():.1f} g", fontsize=10, color=INK)
ax.set_xlabel("Protein at breakfast (g)")
ax.set_ylabel("Adults")
ax.set_title("Breakfast protein is mostly 0–15 g", fontsize=12, fontweight="bold", color=INK, loc="left")
ax = axes[1]
q = sens["ALMI_by_breakfast_quartile_raw"]
labels = ["0–4 g", "4–11 g", "11–18 g", "18–93 g"]
vals = [q[str(i)]["mean_ALMI"] for i in range(4)]
bars = ax.bar(labels, vals, color=[MUTED, MUTED, TEAL, ACCENT], width=0.62)
ax.set_ylim(7.3, 8.5)
ax.set_ylabel("Mean ALMI (kg/m²), unadjusted")
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.04, f"{v:.2f}", ha="center",
            fontsize=11, fontweight="bold", color=INK)
ax.set_title("Top breakfast quartile carries ~0.5 kg/m² more lean mass",
             fontsize=12, fontweight="bold", color=INK, loc="left")
fig.suptitle("Breakfast is the only meal where protein timing shows a signal",
             fontsize=13, fontweight="bold", color=INK, x=0.02, ha="left")
plt.tight_layout(rect=[0, 0, 1, 0.92])
plt.savefig(f"{CH}/03_breakfast.png"); plt.close()

# 4. SHAP ranking (ALMI) -----------------------------------------------------
rank = res["regressions"]["shap_ranking_almi"]
feats = [r["feature"] for r in rank][::-1]
vals = [r["mean_abs_shap"] for r in rank][::-1]
colors = [ACCENT if f in ("meals_ge30", "meals_ge25", "breakfast", "protein_per_kg",
                          "max_meal", "share_largest", "cv_meals") else TEAL for f in feats]
fig, ax = plt.subplots(figsize=(8, 5.2))
ax.barh(feats, vals, color=colors, height=0.62)
ax.set_xlabel("Mean |SHAP value| — contribution to predicted ALMI (kg/m²)")
ax.set_title("What actually predicts lean mass? Body size, sex — then total protein.\n"
             "Meal-counting features sit at the bottom.",
             fontsize=12, fontweight="bold", color=INK, loc="left")
for i, v in enumerate(vals):
    ax.text(v + 0.02, i, f"{v:.3f}", va="center", fontsize=9, color=INK)
ax.set_xlim(0, max(vals) * 1.25)
plt.tight_layout(); plt.savefig(f"{CH}/04_shap.png"); plt.close()

# 5. The body-size trap: coefficient on protein/kg across specs -------------
fig, ax = plt.subplots(figsize=(8, 4.8))
specs = ["No size\ncontrol", "Height\nonly", "BMI", "Height +\nweight"]
coefs = [-1.3941, -1.4404, 0.0692, 0.0912]
ps = ["p < 1e-32", "p < 1e-34", "p = 0.33", "p = 0.19"]
cols = [ACCENT, ACCENT, TEAL, TEAL]
bars = ax.bar(specs, coefs, color=cols, width=0.55)
ax.axhline(0, color=INK, lw=1)
ax.set_ylim(-1.85, 0.55)
for b, c, p in zip(bars, coefs, ps):
    if c < 0:
        ax.text(b.get_x() + b.get_width() / 2, c / 2, f"{c:+.2f}\n({p})",
                ha="center", va="center", fontsize=11, fontweight="bold", color="white")
    else:
        ax.text(b.get_x() + b.get_width() / 2, c + 0.08, f"{c:+.2f}\n({p})",
                ha="center", va="bottom", fontsize=11, fontweight="bold", color=INK)
ax.set_ylabel("Coefficient on protein (g/kg/day) → ALMI")
ax.set_title("Same data, opposite conclusion: protein-per-kg looks toxic\nuntil you control for body size — a denominator artifact",
             fontsize=12, fontweight="bold", color=INK, loc="left")
ax.text(0, -0.24, "Heavier people have lower protein-per-kg (r = −0.43 with BMI) and more lean mass.\n"
        "Without a size control, protein looks like it destroys muscle. It doesn't.",
        transform=ax.transAxes, fontsize=9, color=MUTED)
plt.tight_layout(); plt.savefig(f"{CH}/05_size_trap.png"); plt.close()

print("charts written:", sorted(os.listdir(CH)))
