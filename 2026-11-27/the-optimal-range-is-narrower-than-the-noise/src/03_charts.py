"""03_charts.py — Charts for The Optimal Range Is Narrower Than the Noise.
Style: clean, muted, readable; no chartjunk (repo convention).
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent.parent
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
RED = "#B03A2E"    # the verdict is unreliable
GREEN = "#3E7A4E"  # the verdict holds
AMBER = "#C07A1A"  # borderline
GREY = "#777777"
LIGHT = "#D9D9D9"

with open(BASE / "output" / "results.json") as f:
    R = json.load(f)
df = pd.DataFrame(R["markers"])
VITD_LT = R["vitamin_d_long_term_sensitivity"]


def save(fig, name):
    fig.tight_layout(rect=[0, 0.14, 1, 1])
    fig.savefig(CH / name, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def short(m):
    return {"Total testosterone (men)": "Total testosterone",
            "Lipoprotein(a)": "Lipoprotein(a)",
            "Fasting insulin": "Fasting insulin",
            "Fasting glucose": "Fasting glucose"}.get(m, m)


def chart1_noise_vs_band():
    """Band half-width vs total noise on one draw, sorted by noise-to-band ratio."""
    d = df.sort_values("noise_to_band_ratio", ascending=True)
    labels = [short(m) for m in d["marker"]]
    y = np.arange(len(d))
    colors = [RED if r >= 1 else AMBER if r >= 0.6 else GREEN
              for r in d["noise_to_band_ratio"]]
    fig, ax = plt.subplots(figsize=(9, 6.2))
    ax.barh(y, d["band_half_width_pct"], color=LIGHT, edgecolor="none",
            label="Optimal band, half-width (%)")
    ax.barh(y, d["cv_total_pct"], color=colors, edgecolor="none",
            label="Total noise on one draw, CV (%)")
    for yi, (hw, cv, r) in enumerate(zip(d["band_half_width_pct"],
                                         d["cv_total_pct"],
                                         d["noise_to_band_ratio"])):
        ax.text(max(hw, cv) + 1.5, yi, f"ratio {r:.2f}", va="center",
                fontsize=10, color="#333333")
    ax.set_yticks(y, labels)
    ax.set_xlabel("Percent of the marker's value (%)")
    ax.set_title("Noise on one draw vs the width of the verdict",
                 fontsize=12, loc="left")
    ax.set_xlim(0, 78)
    fig.text(0.01, 0.01,
             "Grey bar: how wide the optimal band is around its centre (or the 20% margin below a threshold).\n"
             "Coloured bar: the total variation (biological + analytical) on a single result. Red = noise wider than the band.",
             fontsize=9, color=GREY)
    save(fig, "01_noise_vs_band.png")


def chart2_misclassification():
    """P(one draw misclassifies you), person dead-centre optimal on every marker."""
    d = df.sort_values("p_misclassified_pct", ascending=True)
    labels = [short(m) for m in d["marker"]]
    y = np.arange(len(d))
    colors = [RED if p >= 10 else AMBER if p >= 3 else GREEN
              for p in d["p_misclassified_pct"]]
    fig, ax = plt.subplots(figsize=(9, 6.2))
    ax.barh(y, d["p_misclassified_pct"], color=colors, edgecolor="none")
    for yi, p in enumerate(d["p_misclassified_pct"]):
        ax.text(p + 0.7, yi, f"{p:.1f}%", va="center", fontsize=10, color="#333333")
    # vitamin D long-term sensitivity as a second, hatched bar
    i_vitd = list(d["marker"]).index("Vitamin D 25(OH)D")
    ax.barh(i_vitd, VITD_LT["p_misclassified_long_term_pct"], color="none",
            edgecolor=RED, hatch="//", height=0.45)
    ax.text(VITD_LT["p_misclassified_long_term_pct"] + 0.7, i_vitd + 0.28,
            f"long-term: {VITD_LT['p_misclassified_long_term_pct']:.0f}%",
            va="center", fontsize=9, color=RED)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Chance one draw puts you on the wrong side of 'optimal' (%)")
    ax.set_title("One draw mislabels you",
                 fontsize=12, loc="left")
    ax.set_xlim(0, 42)
    fig.text(0.01, 0.01,
             "Scenario: your true value sits at the centre of the optimal band (two-sided bands),\n"
             "or 20% below the threshold (one-sided targets). 500,000 simulated draws per marker.\n"
             "Hatched bar: vitamin D using its 5-year within-person variation (14.9%) instead of the 10-week value (6.8%).",
             fontsize=9, color=GREY)
    save(fig, "02_misclassification.png")


def chart3_rcv():
    """Reference change value: how far a marker must move before the change is real."""
    d = df.sort_values("rcv95_pct", ascending=True)
    labels = [short(m) for m in d["marker"]]
    y = np.arange(len(d))
    colors = [RED if v >= 100 else AMBER if v >= 50 else GREEN for v in d["rcv95_pct"]]
    fig, ax = plt.subplots(figsize=(9, 6.2))
    ax.barh(y, d["rcv95_pct"], color=colors, edgecolor="none")
    for yi, v in enumerate(d["rcv95_pct"]):
        ax.text(v + 4, yi, f"{v:.0f}%", va="center", fontsize=10, color="#333333")
    ax.set_yticks(y, labels)
    ax.set_xlabel("Change needed between two draws to be statistically real, 95% confidence (%)")
    ax.set_title("How far must a marker move to be real?",
                 fontsize=12, loc="left")
    ax.set_xlim(0, 215)
    fig.text(0.01, 0.01,
             "Reference change value (RCV): 2.77 x total CV. A smaller move than this between two tests\n"
             "is indistinguishable from noise. hsCRP has to nearly triple before you can say it moved.",
             fontsize=9, color=GREY)
    save(fig, "03_rcv.png")


def chart4_repeats():
    """Blood draws needed for a 95%-reliable 'optimal' verdict."""
    d = df.sort_values("repeats_needed_95pct", ascending=True)
    labels = [short(m) for m in d["marker"]]
    y = np.arange(len(d))
    vals = d["repeats_needed_95pct"].tolist()
    colors = [RED if v > 2 else AMBER if v == 2 else GREEN for v in vals]
    fig, ax = plt.subplots(figsize=(9, 6.2))
    ax.barh(y, vals, color=colors, edgecolor="none")
    for yi, v in enumerate(vals):
        ax.text(v + 0.6, yi, f"{v} draw{'s' if v != 1 else ''}", va="center",
                fontsize=10, color="#333333")
    ax.set_yticks(y, labels)
    ax.set_xlabel("Repeat draws (averaged) needed for a 95%-reliable verdict")
    ax.set_title("How many draws to trust the verdict?",
                 fontsize=12, loc="left")
    ax.set_xlim(0, 33)
    fig.text(0.01, 0.01,
             "Same scenario as chart 2. Most markers need one draw. hsCRP needs 28 draws averaged\n"
             "together before a single 'optimal / not optimal' verdict is 95% reliable.",
             fontsize=9, color=GREY)
    save(fig, "04_repeats.png")


if __name__ == "__main__":
    chart1_noise_vs_band()
    chart2_misclassification()
    chart3_rcv()
    chart4_repeats()
