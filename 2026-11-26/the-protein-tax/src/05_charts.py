"""Charts for The Protein Tax. Style: clean, muted, readable; no chartjunk."""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
CH = BASE / "charts"
CH.mkdir(exist_ok=True)

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#888888",
        "axes.labelcolor": "#222222",
        "xtick.color": "#444444",
        "ytick.color": "#444444",
    }
)
PROTEIN_C = "#B4552D"  # burnt orange: the protein-branded side
PLAIN_C = "#3E7A4E"  # green: the plain side
GREY = "#777777"

CAT_LABELS = {
    "bars": "Bars",
    "yogurts": "Yogurts",
    "cereals": "Cereals",
    "breads": "Breads",
    "pastas": "Pastas",
    "cookies": "Cookies",
}
CATS = ["bars", "yogurts", "cereals", "breads", "pastas", "cookies"]


def save(fig, name):
    fig.tight_layout()
    fig.savefig(CH / name, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def chart1_fiber_gap():
    t = pd.read_csv(DATA / "category_table.csv")
    cats = ["bars", "yogurts", "cereals", "breads", "pastas"]  # cookies: no protein cookies found
    fig, ax = plt.subplots(figsize=(9, 4.6))
    x = np.arange(len(cats))
    w = 0.38
    prot = [t[(t.category == c) & (t.group == "protein")]["fiber_per_100kcal_med"].iloc[0] for c in cats]
    plain = [t[(t.category == c) & (t.group == "plain")]["fiber_per_100kcal_med"].iloc[0] for c in cats]
    ns = [int(t[(t.category == c) & (t.group == "protein")]["n"].iloc[0]) for c in cats]
    ax.bar(x - w / 2, prot, w, label="Protein-branded", color=PROTEIN_C)
    ax.bar(x + w / 2, plain, w, label="Plain version", color=PLAIN_C)
    for i, (a, b, n) in enumerate(zip(prot, plain, ns)):
        ax.text(i - w / 2, a + 0.12, f"{a:.2f}", ha="center", fontsize=9, color=PROTEIN_C)
        ax.text(i + w / 2, b + 0.12, f"{b:.2f}", ha="center", fontsize=9, color=PLAIN_C)
        if n < 20:
            ax.text(i - w / 2, -0.55, f"n={n}", ha="center", fontsize=8, color=PROTEIN_C)
    ax.set_xticks(x)
    ax.set_xticklabels([CAT_LABELS[c] for c in cats])
    ax.set_ylabel("Median fiber (g) per 100 kcal")
    ax.set_title("The protein version carries as much or more fiber per calorie", fontsize=13)
    ax.legend(frameon=False, loc="upper right")
    ax.set_ylim(0, max(plain + prot) * 1.25)
    save(fig, "fiber_per_100kcal_by_category.png")


def chart2_exchange_scatter():
    df = pd.read_csv(DATA / "clean_products.csv").dropna(subset=["fiber_100g"])
    df = df[(df["protein_per_100kcal"] <= 25) & (df["fiber_per_100kcal"] <= 12)]
    cats = ["bars", "yogurts", "cereals", "breads", "pastas"]
    fig, axes = plt.subplots(2, 3, figsize=(10, 6.4), sharex=True, sharey=True)
    ex = pd.read_csv(DATA / "exchange_rates.csv").set_index("category")
    panels = cats + ["POOLED"]
    for ax, cat in zip(axes.flat, panels):
        if cat == "POOLED":
            sub = df
            slope = ex.loc["POOLED (category fixed effects)", "slope_fiber_per_protein"]
            title = f"All categories pooled  (slope {slope:+.2f})"
            draw_line = False
        else:
            sub = df[df["category"] == cat]
            slope = ex.loc[cat, "slope_fiber_per_protein"]
            intercept = ex.loc[cat, "intercept"]
            title = f"{CAT_LABELS[cat]}  (slope {slope:+.2f})"
            draw_line = True
        ax.scatter(
            sub[sub["group"] == "plain"]["protein_per_100kcal"],
            sub[sub["group"] == "plain"]["fiber_per_100kcal"],
            s=6, alpha=0.35, color=PLAIN_C, label="Plain",
        )
        ax.scatter(
            sub[sub["group"] == "protein"]["protein_per_100kcal"],
            sub[sub["group"] == "protein"]["fiber_per_100kcal"],
            s=10, alpha=0.55, color=PROTEIN_C, label="Protein",
        )
        xs = np.array([0, 25])
        if draw_line:
            ax.plot(xs, intercept + slope * xs, color="#222222", lw=1.2)
        ax.set_title(title, fontsize=11)
        ax.set_xlim(0, 25)
        ax.set_ylim(0, 12)
    for ax in axes[1]:
        ax.set_xlabel("Protein (g) per 100 kcal")
    for ax in axes[:, 0]:
        ax.set_ylabel("Fiber (g) per 100 kcal")
    axes[0, 0].legend(frameon=False, loc="upper right", fontsize=9)
    fig.suptitle("More protein on the label, more fiber in the food: the exchange rate is positive", fontsize=13)
    save(fig, "exchange_scatter.png")


def chart3_slopes():
    ex = pd.read_csv(DATA / "exchange_rates.csv")
    ex = ex[ex["category"].isin(["bars", "yogurts", "cereals", "breads", "pastas"])]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    colors = [PROTEIN_C if s < 0 else PLAIN_C for s in ex["slope_fiber_per_protein"]]
    ax.barh([CAT_LABELS[c] for c in ex["category"]], ex["slope_fiber_per_protein"], color=colors)
    ax.axvline(0, color="#222222", lw=1)
    for i, s in enumerate(ex["slope_fiber_per_protein"]):
        ax.text(s + (-0.02 if s < 0 else 0.02), i, f"{s:+.2f}", va="center",
                ha="right" if s < 0 else "left", fontsize=10)
    ax.set_xlabel("Grams of fiber per 100 kcal gained for each extra gram of protein per 100 kcal")
    ax.set_title("The exchange rate: protein and fiber move together, not apart", fontsize=13)
    ax.set_xlim(min(0, ex["slope_fiber_per_protein"].min() * 1.3), max(ex["slope_fiber_per_protein"]) * 1.3)
    save(fig, "exchange_rates.png")


def chart4_claim_audit():
    a = pd.read_csv(DATA / "claim_audit.csv").set_index("metric")
    labels = [
        "Meet the 'high protein' bar\n(≥20% of calories from protein)",
        "Are fiber-poor\n(<3 g fiber / 100 g)",
        "Fail both: not high-protein\nAND fiber-poor",
    ]
    vals = [
        a.loc["protein-branded products meeting EU 'high protein' bar (>=20% energy)", "pct"],
        a.loc["protein-branded products that are fiber-poor (<3g fiber/100g)", "pct"],
        a.loc["protein-branded AND fiber-poor AND below high-protein bar", "pct"],
    ]
    fig, ax = plt.subplots(figsize=(9, 4.0))
    y = np.arange(len(labels))
    ax.barh(y, vals, color=[PLAIN_C, PROTEIN_C, "#8C2F1B"], height=0.55)
    for i, v in enumerate(vals):
        ax.text(v + 1.5, i, f"{v:.0f}%", va="center", fontsize=11)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of protein-branded products (n = {:,})".format(int(a.iloc[0]["n"])))
    ax.set_title("The label says protein. Usually it delivers, and fiber comes along", fontsize=13)
    ax.invert_yaxis()
    save(fig, "claim_audit.png")


def chart5_daily_swap():
    s = pd.read_csv(DATA / "swap_scenario.csv")
    with open(DATA / "analysis.json") as f:
        an = json.load(f)
    # fiber_lost_g is negative when the swap GAINS fiber; flip the sign for display
    gained = (-s["fiber_lost_g"]).tolist()
    labels = [CAT_LABELS[c] for c in s["category"]]
    total_gain = -an["daily_swap_fiber_lost_g"]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    y = np.arange(len(labels))
    colors = [PLAIN_C if v >= 0 else PROTEIN_C for v in gained]
    ax.barh(y, gained, color=colors, height=0.55)
    for i, v in enumerate(gained):
        lab = f"{v:+.2f} g" if abs(v) >= 0.005 else "0.00 g"
        if v >= 0:
            ax.text(v + 0.06, i, lab, va="center", ha="left", fontsize=11)
        else:
            ax.text(v - 0.06, i, lab, va="center", ha="right", fontsize=11)
    ax.axvline(0, color="#222222", lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{lab} → protein version" for lab in labels])
    ax.set_xlabel("Fiber gained per day (g) from swapping plain → protein version, equal calories")
    ax.set_title(f"One day of protein swaps gains {total_gain:.1f} g of fiber "
                 f"({abs(an['swap_as_pct_of_women_gap']):.0f}% of the average woman's daily fiber gap)",
                 fontsize=13)
    ax.invert_yaxis()
    ax.set_xlim(-0.75, max(gained) * 1.9)
    save(fig, "daily_swap.png")


def main():
    chart1_fiber_gap()
    chart2_exchange_scatter()
    chart3_slopes()
    chart4_claim_audit()
    chart5_daily_swap()


if __name__ == "__main__":
    main()
