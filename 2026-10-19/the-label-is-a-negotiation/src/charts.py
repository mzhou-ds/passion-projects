#!/usr/bin/env python3
"""Charts for The Label Is a Negotiation. Reads output/results.json."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
R = json.load(open(os.path.join(ROOT, "output", "results.json")))
CH = os.path.join(ROOT, "charts")
plt.rcParams.update({"figure.dpi": 130, "font.size": 10, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.spines.top": False,
                     "axes.spines.right": False})
C1, C2, C3 = "#1f6f54", "#c0392b", "#2e5f8a"

# 01 zero-window census
c = R["zero_window_census"]
names = [x["nutrient"] for x in c][::-1]
zw = np.array([x["n_zero_window"] for x in c][::-1])
mat = np.array([x["n_zero_window_material"] for x in c][::-1])
fig, ax = plt.subplots(figsize=(7.4, 4.4))
ax.barh(names, zw, color=C3, label="Prints 0, own data shows some (trace or more)")
ax.barh(names, mat, color=C2, label="Material tier (real density per 100 g)")
for i, (a, b) in enumerate(zip(zw, mat)):
    ax.annotate(f"{a:,}", (a, i), textcoords="offset points", xytext=(4, -3), fontsize=9)
ax.set_xlabel("Products (of 629,114 current US branded products)")
ax.set_title("The zero window: labels that print 0 for something the product contains")
ax.legend(fontsize=8, loc="lower right"); ax.set_xlim(0, zw.max() * 1.22)
fig.tight_layout(); fig.savefig(f"{CH}/01_zero_window.png"); plt.close(fig)

# 02 proximity scoreboard
p = R["proximity"]
rows = [("Sodium <=140 (low sodium)", p["sodium_140_low_sodium"], C1),
        ("Sodium 98 (placebo)", p["sodium_98_placebo"], "grey"),
        ("Sat fat <=1g (low)", p["satfat_1_low"], C2),
        ("Sat fat 0.7g (placebo)", p["satfat_0.7_placebo"], "grey"),
        ("Fat <=3g (low fat)", p["fat_3_low_fat"], C1),
        ("Fat 2.1g (placebo)", p["fat_2.1_placebo"], "grey"),
        ("Kcal <=40 (low calorie)", p["kcal_40_low_calorie"], C1),
        ("Kcal 28 (placebo)", p["kcal_28_placebo"], "grey"),
        ("Cholesterol <=20mg (low)", p["cholesterol_20_low"], C1),
        ("Potassium 140 (no claim)", p["potassium_140_no_claim_exists"], "grey")]
fig, ax = plt.subplots(figsize=(7.4, 4.8))
ax.barh([r[0] for r in rows][::-1], [r[1]["below_share"] for r in rows][::-1],
        color=[r[2] for r in rows][::-1])
ax.axvline(0.5, color="black", lw=1, ls="--")
ax.set_xlim(0.38, 0.68)
ax.set_xlabel("Share of products near the line that fall just under it")
ax.set_title("Do products bunch under the famous claim lines? Mostly, no")
fig.tight_layout(); fig.savefig(f"{CH}/02_proximity.png"); plt.close(fig)

# 03 hideable capacity
h = R["hideable_fat"]
tiers = ["≥5", "≥10", "≥25", "≥50", "≥100"]
vals = [h["products_can_hide_ge_5g_per100g"], h["products_can_hide_ge_10g_per100g"],
        h["products_can_hide_ge_25g_per100g"], h["products_can_hide_ge_50g_per100g"],
        h["products_can_hide_ge_100g_per100g"]]
fig, ax = plt.subplots(figsize=(7.2, 4.4))
ax.bar(tiers, vals, color=C2)
for i, v in enumerate(vals):
    ax.annotate(f"{v:,}", (i, v), textcoords="offset points", xytext=(0, 4),
                ha="center", fontsize=9)
ax.set_xlabel("Grams of fat per 100 g that could hide behind a printed '0 g fat'")
ax.set_ylabel("Products whose serving is small enough")
ax.set_title("Hideable capacity: the smaller the serving, the bigger the legal zero")
fig.tight_layout(); fig.savefig(f"{CH}/03_hideable.png"); plt.close(fig)

# 04 counterfactual flips
f = R["counterfactual_flips"]
fig, ax = plt.subplots(figsize=(7.4, 4.8))
ax.barh([x["label"] for x in f][::-1], [x["lost_at_standard_serving"] for x in f][::-1],
        color=C1)
for i, x in enumerate(f[::-1]):
    ax.annotate(f"{x['lost_at_standard_serving']:,}  ({x['pct_lost']}%)",
                (x["lost_at_standard_serving"], i), textcoords="offset points",
                xytext=(4, -3), fontsize=9)
ax.set_xlabel("Labels lost when relabeled at the category's standard (median) serving")
ax.set_title("Serving-bought labels: the small serving is doing the work")
ax.set_xlim(0, max(x["lost_at_standard_serving"] for x in f) * 1.3)
fig.tight_layout(); fig.savefig(f"{CH}/04_counterfactual.png"); plt.close(fig)

# 05 spray contrast
s = R["spray_contrast"]
fig, axes = plt.subplots(1, 2, figsize=(7.4, 4.2))
axes[0].bar(["Bottled oil\n(6,572 products)", "Cooking spray\n(668 products)"],
            [s["bottled_median_fat_per100g"], 0.0], color=[C3, C2])
axes[0].set_ylabel("Fat submitted per 100 g (median)")
axes[0].set_title("Same aisle, same oil")
axes[1].bar(["Bottled oil", "Cooking spray"],
            [s["bottled_median_kcal_serv"], 0.0], color=[C3, C2])
axes[1].set_ylabel("Calories per serving (median)")
axes[1].set_title("What the label shows per serving")
fig.suptitle("The spray is oil. Its serving is a third of a second.", fontsize=11)
fig.tight_layout(); fig.savefig(f"{CH}/05_spray.png"); plt.close(fig)

# 06 SHAP for the fat-zero model
d = np.load(os.path.join(ROOT, "output", "shap_fat.npz"), allow_pickle=True)
cols = [str(x) for x in d["columns"]]
mean_abs = np.abs(d["values"]).mean(axis=0)
order = np.argsort(mean_abs)[::-1][:7]
labels = [cols[i].replace("log_serving", "log serving size")
          .replace("log_content100", "log fat content (per 100 g)")
          .replace("log_kcal100", "log calorie density")
          .replace("serving_lt_5g", "serving under 5 g")
          .replace("serving_lt_30g", "serving under 30 g") for i in order]
fig, ax = plt.subplots(figsize=(7.2, 4.2))
ax.barh(labels[::-1], mean_abs[order][::-1], color=C1)
ax.set_xlabel("Mean |SHAP| - contribution to predicting a printed 0 g fat")
ax.set_title("What decides a printed zero: the content, then the serving")
fig.tight_layout(); fig.savefig(f"{CH}/06_shap.png"); plt.close(fig)
print("charts done")
