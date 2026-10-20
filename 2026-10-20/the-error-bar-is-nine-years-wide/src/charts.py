"""All charts for the build, from output/results.json + noise_by_person.csv."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "output")
CH = os.path.join(HERE, "..", "charts")
os.makedirs(CH, exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False})


def main():
    res = json.load(open(os.path.join(OUT, "results.json")))
    noise = pd.read_csv(os.path.join(OUT, "noise_by_person.csv"))
    claims = pd.read_csv(os.path.join(DATA, "claims.csv"))

    # 01 — the error bar nobody prints
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.hist(noise["width95"], bins=40, color="#4C72B0", edgecolor="white", lw=0.3)
    med = res["noise"]["median_width95_years"]
    ax.axvline(med, color="#C44E52", lw=2, label=f"median width: {med:.1f} years")
    ax.axvline(3.23, color="#55A868", lw=1.6, ls="--",
               label="largest controlled claim in claims.csv: 3.23 y")
    ax.set_xlabel("Width of one person's 95% interval for a single PhenoAge reading (years)")
    ax.set_ylabel("People (NHANES 2015-2018 analysis sample)")
    ax.set_title("The error bar nobody prints")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(f"{CH}/01_noise_width.png", dpi=150); plt.close(fig)

    # 02 — where the wobble comes from
    dec = pd.DataFrame(res["decomposition"])
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    ax.barh(dec["label"][::-1], (100 * dec["oat_share"])[::-1], color="#4C72B0")
    for i, (s, cv) in enumerate(zip((100 * dec["oat_share"])[::-1],
                                    dec["total_cv_pct"][::-1])):
        ax.text(s + 1, i, f"{s:.0f}% of noise, CV {cv:.0f}%", va="center", fontsize=9)
    ax.set_xlabel("Share of within-person PhenoAge noise variance (one-at-a-time)")
    ax.set_title("One red-cell marker makes most of the weather")
    ax.set_xlim(0, 100)
    fig.tight_layout(); fig.savefig(f"{CH}/02_noise_decomposition.png", dpi=150); plt.close(fig)

    # 03 — regression to the mean on a pure retest (consumer band, |accel|<=10)
    rt = res["retest_consumer_band"]
    cats = ["Highest first\nreading (top 10%)", "Top quartile", "Everyone",
            "Bottom quartile"]
    vals = [rt["mean_change_top_decile_baseline"],
            rt["mean_change_top_quartile_baseline"], 0.0,
            rt["mean_change_bottom_quartile_baseline"]]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    colors = ["#C44E52", "#DD8452", "#8172B2", "#55A868"]
    ax.bar(cats, vals, color=colors)
    ax.axhline(0, color="black", lw=0.8)
    for i, v in enumerate(vals):
        ax.text(i, v + (0.18 if v >= 0 else -0.42), f"{v:+.1f} y", ha="center", fontsize=10)
    ax.set_ylim(-2.9, 2.1)
    ax.set_ylabel("Mean change on an immediate retest (years)")
    ax.set_title("Nothing changed. The highest readings still fell.\n(simulated retest, zero true change, buyers' band)")
    fig.tight_layout(); fig.savefig(f"{CH}/03_regression_to_mean.png", dpi=150); plt.close(fig)

    # 04 — claims vs the noise band (claimed changes only; negative = younger)
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    band = res["noise"]["median_width95_years"] / 2
    cp = claims[claims["effect_years"] <= 0].iloc[::-1].reset_index(drop=True)
    short = ["Rejuvant Ca-AKG, no control (~7 mo)",
             "Fitzgerald lifestyle, vs control (8 wk)",
             "Fitzgerald lifestyle, within-group (8 wk)",
             "CALERIE calorie restriction (RCT, 2 y)"]
    y = np.arange(len(cp))
    ax.axvspan(-band, band, color="#C44E52", alpha=0.15,
               label=f"one person's noise half-band: ±{band:.1f} y")
    ax.barh(y, cp["effect_years"], color="#4C72B0")
    ax.axvline(0, color="black", lw=0.8)
    for i, v in enumerate(cp["effect_years"]):
        if v == 0:
            ax.text(-0.15, i, "0.0 (no effect found)", ha="right", va="center", fontsize=9)
        else:
            ax.text(v + 0.2, i, f"{v:.2f}", ha="left", va="center",
                    fontsize=9, color="white", fontweight="bold")
    ax.set_yticks(y, short[:len(cp)])
    ax.set_xlabel("Claimed change in biological age (years; negative = younger)")
    ax.set_title("Famous claims vs one person's weather band")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout(); fig.savefig(f"{CH}/04_claims_vs_noise.png", dpi=150); plt.close(fig)

    # 05 — what the between-person spread is made of
    sig = pd.Series(res["signal"]["xb_group_shares"]).sort_values()
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    ax.barh([s.replace(" (", "\n(") for s in sig.index], 100 * sig.values,
            color=["#8172B2" if s.startswith("Chronological") else "#DD8452"
                   for s in sig.index])
    ax.set_xlabel("Share of variance in the PhenoAge linear predictor (%)")
    ax.set_title("Between people, 'aging' is mostly this month's state too")
    fig.tight_layout(); fig.savefig(f"{CH}/05_signal_decomposition.png", dpi=150); plt.close(fig)

    # 06 — repeat panels vs earned precision
    ks = np.arange(1, 41)
    widths = res["noise"]["median_width95_years"] / np.sqrt(ks)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(ks, widths, color="#4C72B0", lw=2)
    for target in (4, 2):
        k = res["repeats_needed"][f"width_le_{target}y"]
        ax.axhline(target, color="#C44E52", lw=1, ls="--")
        ax.plot([k], [target], "o", color="#C44E52")
        ax.annotate(f"{k} panels averaged -> width {target} y (±{target/2:.0f} y)",
                    (k, target), textcoords="offset points", xytext=(6, 8), fontsize=9)
    ax.set_xlabel("Panels averaged (independent draws, same person)")
    ax.set_ylabel("95% interval width (years)")
    ax.set_title("Precision is buyable, but nobody buys it")
    fig.tight_layout(); fig.savefig(f"{CH}/06_repeats.png", dpi=150); plt.close(fig)
    print("charts ->", CH)


if __name__ == "__main__":
    main()
