"""05_charts.py — charts for The Handshake Test.

1. forest_hr_per_sd.png — base-adjusted HR per SD for each candidate.
2. cindex_contest.png — repeated 5-fold CV C-index by model.
3. grip_years.png — years of aging equivalent to a weaker grip.
4. quintiles.png — mortality HR by sex-specific grip quintile.
5. survival_km.png — Kaplan-Meier by sex-specific grip quartile.
6. prevalence.png — weighted % below the EWGSOP2 weak-grip cutoff.
7. bmi_u.png — categorical BMI / SBP hazard ratios (the fairness check).
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter

BASE = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(BASE, "data")
CH = os.path.join(BASE, "charts")
os.makedirs(CH, exist_ok=True)

plt.rcParams.update({
    "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "-",
    "figure.dpi": 150,
})
INK = "#1a1a1a"
GRIP = "#0b6e4f"   # green: grip
VITAL = "#8a8d93"  # grey: standard vitals
ACCENT = "#b3541e" # rust: highlight

df = pd.read_csv(os.path.join(DATA, "analytic.csv"))
sd = pd.read_csv(os.path.join(DATA, "hr_per_sd_only.csv"))
cv = pd.read_csv(os.path.join(DATA, "cv_cindex.csv"))
q = pd.read_csv(os.path.join(DATA, "quintiles.csv"))
prev = pd.read_csv(os.path.join(DATA, "prevalence.csv"))
cat = pd.read_csv(os.path.join(DATA, "bmi_sbp_categories.csv"))
pricing = pd.read_csv(os.path.join(DATA, "grip_years.csv"))

# ---------------------------------------------------------------- 1. forest
order = ["grip_combined", "grip_max", "grip_relative", "vig_any",
         "strength_any", "pulse", "waist_cm", "sbp", "bmi"]
labels = {"grip_combined": "Grip, combined (per SD = 21 kg)",
          "grip_max": "Grip, max (per SD = 11 kg)",
          "grip_relative": "Grip / bodyweight (per SD = 0.25)",
          "vig_any": "Any vigorous activity (yes vs no)",
          "strength_any": "Any strength training (yes vs no)",
          "pulse": "Resting pulse (per SD = 12 bpm)",
          "waist_cm": "Waist (per SD = 15 cm)",
          "sbp": "Systolic BP (per SD = 19 mmHg)",
          "bmi": "BMI (per SD = 6.8)"}
s = sd.set_index("variable").loc[order]
fig, ax = plt.subplots(figsize=(8.2, 4.6))
y = np.arange(len(order))[::-1]
colors = [GRIP if "grip" in v else VITAL for v in order]
ax.errorbar(s["hr_per_sd"], y, xerr=[s["hr_per_sd"] - s["hr_per_sd_lo"],
                                     s["hr_per_sd_hi"] - s["hr_per_sd"]],
            fmt="o", color=INK, ecolor=INK, capsize=3, ms=6)
for yi, v, c in zip(y, order, colors):
    ax.plot(s.loc[v, "hr_per_sd"], yi, "o", color=c, ms=7)
ax.axvline(1.0, color=INK, lw=1)
ax.set_yticks(y)
ax.set_yticklabels([labels[v] for v in order])
ax.set_xlabel("Hazard ratio for death (base-adjusted)")
ax.set_title("One SD of grip cuts mortality risk by 55%.\n"
             "BMI and systolic BP carry no signal.", loc="left",
             fontsize=12, fontweight="bold")
ax.set_xlim(0.3, 1.35)
fig.tight_layout()
fig.savefig(os.path.join(CH, "forest_hr_per_sd.png"))
plt.close(fig)

# ---------------------------------------------------------------- 2. C-index
base_c = cv.loc[cv["model"] == "base", "cv_cindex"].iloc[0]
show = ["base", "base+bmi", "base+sbp", "base+pulse", "base+waist",
        "base+strength_any", "base+vigorous", "base+all_vitals",
        "base+grip_combined", "base+all_vitals+grip",
        "base+all_vitals+grip+activity"]
names = {"base": "Base (age, sex, race,\neducation, smoking, disease)",
         "base+bmi": "+ BMI", "base+sbp": "+ systolic BP",
         "base+pulse": "+ resting pulse", "base+waist": "+ waist",
         "base+strength_any": "+ strength training",
         "base+vigorous": "+ vigorous activity",
         "base+all_vitals": "+ ALL four vitals",
         "base+grip_combined": "+ grip strength",
         "base+all_vitals+grip": "+ all vitals + grip",
         "base+all_vitals+grip+activity": "+ vitals + grip + activity"}
c = cv.set_index("model").loc[show]
fig, ax = plt.subplots(figsize=(8.2, 5.0))
y = np.arange(len(show))[::-1]
vals = c["cv_cindex"].values
cols = [GRIP if "grip" in m else (ACCENT if m == "base+all_vitals"
        else VITAL) for m in show]
ax.barh(y, vals - 0.75, left=0.75, color=cols, height=0.62)
for yi, v, m in zip(y, vals, show):
    d = v - base_c
    dstr = f"{d:+.3f}" if abs(d) >= 0.0005 else "\u00b10.000"
    ax.text(v + 0.002, yi, f"{v:.3f}  ({dstr})",
            va="center", fontsize=10)
ax.set_yticks(y)
ax.set_yticklabels([names[m] for m in show])
ax.set_xlim(0.75, 0.84)
ax.set_xlabel("Out-of-sample Harrell's C-index (repeated 5-fold CV)")
ax.set_title("Grip alone adds 4x what the four vitals add",
             loc="left", fontsize=12, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(CH, "cindex_contest.png"))
plt.close(fig)

# ---------------------------------------------------------------- 3. grip-years
p = pricing.set_index("group")
fig, ax = plt.subplots(figsize=(8.2, 3.8))
xs = [5, 10, 15]
for grp, col, mk in [("men", "#2c6e9b", "o"), ("women", "#b3541e", "s"),
                     ("all", INK, "D")]:
    yrs = [p.loc[grp, "years_per_5kg_weaker"] * k / 5 for k in xs]
    ax.plot(xs, yrs, marker=mk, color=col, lw=2, label=grp.capitalize())
    for x, yv in zip(xs, yrs):
        ax.annotate(f"{yv:.1f} yrs", (x, yv), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=10)
ax.set_xticks(xs)
ax.set_xticklabels(["5 kg weaker", "10 kg weaker", "15 kg weaker"])
ax.set_ylabel("Equivalent years of aging\n(in mortality risk)")
ax.set_title("A 10-kg weaker handshake = 6 years older",
             loc="left", fontsize=12, fontweight="bold")
ax.legend(frameon=False)
ax.set_ylim(0, 11)
fig.tight_layout()
fig.savefig(os.path.join(CH, "grip_years.png"))
plt.close(fig)

# ---------------------------------------------------------------- 4. quintiles
fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.2), sharey=True)
for ax, sex in zip(axes, ["men", "women"]):
    s = q[q["sex"] == sex].sort_values("quintile")
    x = s["quintile"].values
    ax.errorbar(x, s["hr_vs_strongest"],
                yerr=[s["hr_vs_strongest"] - s["hr_lo"],
                      s["hr_hi"] - s["hr_vs_strongest"]],
                fmt="o-", color=GRIP, capsize=3, ms=6)
    ax.axhline(1.0, color=INK, lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels([f"Q{i}\n{s.iloc[i-1]['grip_median']:.0f} kg"
                        for i in x])
    ax.set_xlabel("Grip quintile (median combined kg)")
    ax.set_title(sex.capitalize(), fontweight="bold")
axes[0].set_ylabel("Hazard ratio vs strongest quintile")
axes[0].set_title("Men: a smooth gradient", fontweight="bold")
axes[1].set_title("Women: a cliff, then flat", fontweight="bold")
fig.suptitle("Weakest-quintile men die at 5.8x the rate of the strongest",
             fontsize=12, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.92])
fig.savefig(os.path.join(CH, "quintiles.png"))
plt.close(fig)

# ---------------------------------------------------------------- 5. KM curves
fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.2), sharey=True)
for ax, sex_label, sub in zip(axes, ["Men", "Women"],
                              [df[df["female"] == 0], df[df["female"] == 1]]):
    s = sub.copy()
    s["grip_q"] = pd.qcut(s["grip_combined"], 4, labels=False,
                          duplicates="drop") + 1
    kmf = KaplanMeierFitter()
    for quartile in [1, 2, 3, 4]:
        g = s[s["grip_q"] == quartile]
        kmf.fit(g["time_months"], g["dead"],
                label=f"Q{quartile} (median {g['grip_combined'].median():.0f} kg)")
        kmf.plot_survival_function(ax=ax, ci_show=False)
    ax.set_title(sex_label, fontweight="bold")
    ax.set_xlabel("Months since exam")
    ax.set_ylim(0.55, 1.0)
axes[0].set_ylabel("Survival")
fig.suptitle("Survival by grip quartile",
             fontsize=12, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.92])
fig.savefig(os.path.join(CH, "survival_km.png"))
plt.close(fig)

# ---------------------------------------------------------------- 6. prevalence
fig, ax = plt.subplots(figsize=(8.2, 4.0))
bands = ["40-49", "50-59", "60-69", "70-80"]
x = np.arange(len(bands))
w = 0.38
for female, col, lab in [(0, "#2c6e9b", "Men (<27 kg max grip)"),
                         (1, "#b3541e", "Women (<16 kg max grip)")]:
    vals = [prev[(prev["female"] == female)
                 & (prev["age_band"] == b)]["weak_pct_weighted"].iloc[0]
            for b in bands]
    ax.bar(x + (-w / 2 if female == 0 else w / 2), vals, w, color=col,
           label=lab)
    for xi, v in zip(x + (-w / 2 if female == 0 else w / 2), vals):
        ax.text(xi, v + 0.4, f"{v:.1f}%", ha="center", fontsize=10)
ax.set_xticks(x)
ax.set_xticklabels(bands)
ax.set_ylabel("Below EWGSOP2 weak-grip cutoff (%)")
ax.set_title("Weak grip is rare before 60, then jumps tenfold",
             loc="left", fontsize=12, fontweight="bold")
ax.legend(frameon=False)
ax.set_ylim(0, 14)
fig.tight_layout()
fig.savefig(os.path.join(CH, "prevalence.png"))
plt.close(fig)

# ---------------------------------------------------------------- 7. BMI / SBP
fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.0), sharey=True)
bmi = cat[cat["variable"] == "bmi_cat"]
sbp = cat[cat["variable"] == "sbp_cat"]
for ax, d, title, ref in [
        (axes[0], bmi, "BMI: a U-shape, bottom at 25-30", "18.5-25"),
        (axes[1], sbp, "Systolic BP: flat, even above 160", "<120")]:
    xs = np.arange(len(d))
    ax.errorbar(xs, d["hr_vs_ref"],
                yerr=[d["hr_vs_ref"] - d["hr_lo"],
                      d["hr_hi"] - d["hr_vs_ref"]],
                fmt="o-", color=VITAL, capsize=3, ms=6)
    ax.axhline(1.0, color=INK, lw=1)
    ax.set_xticks(xs)
    ax.set_xticklabels(d["category"])
    ax.set_title(title, fontweight="bold")
    ax.set_xlabel(f"Category (ref: {ref})")
axes[0].set_ylabel("Hazard ratio vs reference")
fig.suptitle("BMI is U-shaped, BP is flat",
             fontsize=12, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.92])
fig.savefig(os.path.join(CH, "bmi_u.png"))
plt.close(fig)

print("charts written:", sorted(os.listdir(CH)))
