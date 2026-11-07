"""Charts for build #61."""
import json
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "output")
CH = os.path.join(HERE, "..", "charts")
os.makedirs(CH, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "--",
    "figure.dpi": 150,
})
C_BF = "#C0392B"   # breakfast red
C_SN = "#E67E22"   # snack orange
C_OT = "#7F8C8D"   # grey
C_KID = "#8E44AD"  # kids purple


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(CH, name), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def main():
    res = json.load(open(os.path.join(OUT, "results.json")))
    fu = json.load(open(os.path.join(OUT, "followups.json")))
    mdl = json.load(open(os.path.join(OUT, "model.json")))
    occ = pd.read_parquet(os.path.join(DATA, "occasions.parquet"))
    a1 = occ[(occ["day"] == 1) & (occ["reliable"] == 1)
             & (occ["age"] >= 20) & (occ["age"] <= 79)
             & (occ["day_kcal"] >= 500) & (occ["day_kcal"] <= 6000)
             & (occ["WTDRD1"] > 0)].copy()

    # 1. Sugar density by meal ----------------------------------------------
    meals = res["meals_adult_d1"]
    order = ["breakfast", "snack", "lunch", "dinner"]
    labels = ["Breakfast", "Snack", "Lunch", "Dinner"]
    vals = [meals[m]["sugar_per_100kcal"] for m in order]
    lo = [meals[m]["sugar_per_100kcal_ci"][0] for m in order]
    hi = [meals[m]["sugar_per_100kcal_ci"][1] for m in order]
    colors = [C_BF, C_SN, C_OT, C_OT]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    x = np.arange(len(order))
    ax.bar(x, vals, color=colors, width=0.62, zorder=3)
    ax.errorbar(x, vals, yerr=[[v - l for v, l in zip(vals, lo)],
                               [h - v for v, h in zip(vals, hi)]],
                fmt="none", ecolor="black", capsize=5, zorder=4)
    for xi, v in zip(x, vals):
        ax.text(xi, v + 0.25, f"{v:.2f}", ha="center", fontweight="bold")
    ax.axhline(res["evening_snack"]["sugar_per_100kcal"], color=C_SN,
               linestyle=":", linewidth=1.5)
    ax.text(3.45, res["evening_snack"]["sugar_per_100kcal"] + 0.15,
            "9pm snack (dessert slot): 7.41", color=C_SN, ha="right",
            fontsize=10)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Total sugars, g per 100 kcal")
    ax.set_title("Breakfast is the second-sweetest meal — and it is not close\n"
                 "Adults 20–79, NHANES 2007–2018, day 1 (n = 24,156 person-days)",
                 loc="left")
    ax.set_ylim(0, 8.6)
    save(fig, "01_sugar_density_by_meal.png")

    # 2. Survival curves: share of occasions sweeter than X -------------------
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for meal, color, lab in [("breakfast", C_BF, "Breakfast"),
                             ("snack", C_SN, "Snack"),
                             ("lunch", C_OT, "Lunch"),
                             ("dinner", "#2C3E50", "Dinner")]:
        d = a1[a1["meal"] == meal].copy()
        d = d.sort_values("sugar_share")
        w = d["WTDRD1"].to_numpy()
        surv = 1 - np.cumsum(w) / w.sum()
        ax.step(d["sugar_share"], surv, where="post", color=color,
                linewidth=2.2, label=lab, zorder=3)
    ax.axvline(0.25, color="black", linestyle="--", linewidth=1)
    ax.text(0.255, 0.93, "25% sugar:\n55.5% of breakfasts", fontsize=10)
    ax.axvline(0.30, color="black", linestyle="--", linewidth=1)
    ax.text(0.305, 0.60, "30% sugar:\n46.2% of breakfasts", fontsize=10)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Share of the occasion's calories from sugar")
    ax.set_ylabel("Share of occasions sweeter than that")
    ax.set_title("Most breakfasts are dessert by the numbers", loc="left")
    ax.legend(frameon=False, loc="upper right")
    save(fig, "02_breakfast_distribution.png")

    # 3. Sugar clock -----------------------------------------------------------
    clock = pd.read_csv(os.path.join(OUT, "sugar_clock.csv"))
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.bar(clock["hour"], clock["sugar_share_of_day_pct"], color=C_BF,
           width=0.8, zorder=3)
    ax.axvspan(-0.5, 11.5, color="grey", alpha=0.08, zorder=0)
    ax.text(5.5, max(clock["sugar_share_of_day_pct"]) * 0.92,
            f"Before noon: {res['sugar_before_noon_pct']:.1f}% of the day's sugar",
            ha="center", fontsize=11, fontweight="bold")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Share of the day's sugar (%)")
    ax.set_title("The sugar clock: a third of America's sugar is eaten "
                 "before noon", loc="left")
    ax.set_xticks(range(0, 24, 2))
    save(fig, "03_sugar_clock.png")

    # 4. Trend ------------------------------------------------------------------
    tr = res["trend"]
    cyc = [t["cycle"] for t in tr]
    bfd = [t["breakfast_sugar_per_100kcal"] for t in tr]
    snd = [t["snack_sugar_per_100kcal"] for t in tr]
    b25 = [t["breakfast_above_25pct"] for t in tr]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4.2))
    ax1.plot(cyc, bfd, "o-", color=C_BF, label="Breakfast")
    ax1.plot(cyc, snd, "s-", color=C_SN, label="Snack")
    ax1.set_ylabel("Sugars, g per 100 kcal")
    ax1.set_title("Breakfast got 15% less sweet,\n2007 → 2018", loc="left")
    ax1.tick_params(axis="x", rotation=35)
    ax1.legend(frameon=False)
    ax2.plot(cyc, b25, "o-", color=C_BF)
    ax2.set_ylabel("% of breakfasts over 25% sugar calories")
    ax2.set_title("Share of dessert-like\nbreakfasts fell 60% → 49%", loc="left")
    ax2.tick_params(axis="x", rotation=35)
    save(fig, "04_trend.png")

    # 5. What carries breakfast sugar -------------------------------------------
    grp = res["breakfast_sugar_by_foodgrp1"]
    grp = sorted(grp, key=lambda g: -g["sugar_share_pct"])
    labels = [g["label"] for g in grp]
    sshare = [g["sugar_share_pct"] for g in grp]
    kshare = [g["kcal_share_pct"] for g in grp]
    fig, ax = plt.subplots(figsize=(8, 5.0))
    y = np.arange(len(labels))
    ax.barh(y, sshare, color=C_BF, height=0.55, label="Share of breakfast sugar",
            zorder=3)
    ax.barh(y, kshare, color="none", edgecolor="black", height=0.55,
            label="Share of breakfast calories", zorder=4)
    for yi, s, k in zip(y, sshare, kshare):
        ax.text(s + 0.7, yi, f"{s:.0f}% sugar / {k:.0f}% kcal", va="center",
                fontsize=10)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Share (%)")
    ax.set_xlim(0, 42)
    ax.set_title("Where breakfast sugar comes from: four groups carry 96%\n"
                 "Fruit is a fifth of it — the rest is not fruit", loc="left")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "05_whats_in_it.png")

    # 6. Classifier: sugar is the blind spot ------------------------------------
    single = mdl["single_feature_auc"]
    feats = ["sugar_per_100kcal", "prot_share", "fat_share", "carb_share",
             "fiber_per_100kcal", "sodium_per_100kcal",
             "caffeine_per_100kcal", "log_kcal", "n_items"]
    names = {"sugar_per_100kcal": "Sugar density", "prot_share": "Protein share",
             "fat_share": "Fat share", "carb_share": "Carb share",
             "fiber_per_100kcal": "Fiber density",
             "sodium_per_100kcal": "Sodium density",
             "caffeine_per_100kcal": "Caffeine density",
             "log_kcal": "Occasion size (kcal)", "n_items": "Items in occasion"}
    vals = [single[f] for f in feats]
    order_idx = np.argsort(vals)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    cols = [C_BF if f == "sugar_per_100kcal" else C_OT for f in feats]
    ax.barh(np.arange(len(feats)), [vals[i] for i in order_idx],
            color=[cols[i] for i in order_idx], height=0.6, zorder=3)
    ax.set_yticks(np.arange(len(feats)),
                  [names[feats[i]] for i in order_idx])
    ax.axvline(0.5, color="black", linestyle="--")
    ax.text(0.505, len(feats) - 0.4, "coin flip", fontsize=10)
    ax.set_xlabel("AUC telling a breakfast occasion from a snack occasion\n"
                  "(single feature; nutrients-only model AUC = 0.89)")
    ax.set_xlim(0.35, 0.85)
    ax.set_title("Sugar is the one nutrient that cannot tell breakfast\n"
                 "from a snack — everything else can", loc="left")
    save(fig, "06_classifier.png")


if __name__ == "__main__":
    main()
