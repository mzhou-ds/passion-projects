"""Charts for the nutritional-jetlag build."""
import json
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
CH = os.path.join(ROOT, "charts")
plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 130})
C1, C2, C3 = "#1b6f5e", "#d95f34", "#3a6ea5"


def main():
    pairs = pd.read_parquet(os.path.join(ROOT, "data", "pairs_enriched.parquet"))
    R = json.load(open(os.path.join(ROOT, "output", "results.json")))
    w = pairs["WTDR2D"]

    # 1 - shift distributions for the three clock readings
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    for col, lab, c in [("abs_shift_first", "First bite", C3),
                        ("abs_shift_mid", "Calorie midpoint", C1),
                        ("abs_shift_last", "Last bite", C2)]:
        x = pairs[col].clip(upper=8)
        bins = np.arange(0, 8.5, 0.5)
        hist, edges = np.histogram(x, bins=bins, weights=w)
        ax.plot((edges[:-1] + edges[1:]) / 2, hist / hist.sum() * 100,
                label=lab, color=c, lw=2)
    ax.set_xlabel("Absolute day-to-day shift (hours)")
    ax.set_ylabel("% of adults")
    ax.set_title("Your eating clock moves hours between two ordinary days")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(f"{CH}/01_shift_distributions.png"); plt.close(fig)

    # 2 - reliability: within vs between SD + ICC
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    names = ["first", "mid", "last", "window"]
    labels = ["First bite", "Midpoint", "Last bite", "Window"]
    iccs = [R["icc"][n]["icc"] for n in names]
    ax.barh(labels[::-1], iccs[::-1], color=C1, alpha=0.85)
    for i, v in enumerate(iccs[::-1]):
        ax.text(v + 0.02, i, f"ICC {v:.2f}", va="center")
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Intraclass correlation between a person's two days")
    ax.set_title("One recall day is a noisy photograph of an eating clock")
    fig.tight_layout(); fig.savefig(f"{CH}/02_reliability.png"); plt.close(fig)

    # 3 - pair type bars
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    order = ["both_weekday", "mixed", "both_weekend"]
    labs = ["Both days\nweekdays", "One weekday,\none weekend", "Both days\nweekend"]
    vals = [R["pair_type"][o]["median_abs_mid_shift_h"] for o in order]
    ax.bar(labs, vals, color=[C3, C2, C1], width=0.55)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.05, f"{v:.2f} h", ha="center", fontweight="bold")
    ax.set_ylabel("Median |midpoint shift| (hours)")
    ax.set_title("The calendar explains only part of the wobble")
    fig.tight_layout(); fig.savefig(f"{CH}/03_pair_type.png"); plt.close(fig)

    # 4 - age gradient
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    age = R["segments"]["age"]
    bands = [b for b in ["20s", "30s", "40s", "50s", "60s", "70s"] if b in age]
    ax.plot(bands, [age[b]["median_abs_mid_shift_h"] for b in bands],
            marker="o", color=C1, lw=2, label="Midpoint shift")
    ax.plot(bands, [age[b]["median_abs_last_shift_h"] for b in bands],
            marker="s", color=C2, lw=2, label="Last-bite shift")
    ax.set_ylabel("Median absolute shift (hours)")
    ax.set_title("Young clocks wobble most; old clocks are metronomes")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(f"{CH}/04_age.png"); plt.close(fig)

    # 5 - delta-delta binned intake link
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    b = pd.DataFrame(R["delta_bins"])
    centers = [-2.75, -1.5, -0.75, 0, 0.75, 1.5, 2.75]
    ax.bar(centers, b["d_kcal_rel"], width=0.6,
           color=[C2 if v > 0.25 else C3 if v < -0.25 else C1 for v in centers])
    ax.axhline(0, color="#444", lw=0.8)
    ax.set_xlabel("Day 2 minus day 1 calorie midpoint (hours)")
    ax.set_ylabel("Intake change vs average pair (kcal)")
    ax.set_title("The day your clock runs late is the day you eat more")
    fig.tight_layout(); fig.savefig(f"{CH}/05_delta_intake.png"); plt.close(fig)

    # 6 - SHAP importance
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    imp = pd.read_csv(os.path.join(ROOT, "output", "shap_importance.csv")).head(8)[::-1]
    ax.barh(imp["feature"], imp["mean_abs_shap_h"], color=C1, alpha=0.85)
    ax.set_xlabel("Mean |SHAP| (hours of shift)")
    ax.set_title("What predicts an unstable eating clock (XGBoost + SHAP)")
    fig.tight_layout(); fig.savefig(f"{CH}/06_shap.png"); plt.close(fig)
    print("charts done")


if __name__ == "__main__":
    main()
