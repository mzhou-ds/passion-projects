"""05_charts.py — Six charts for the README."""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import shap

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CH = ROOT / "charts"
CH.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "--",
    "figure.dpi": 150,
})
C_SOLO = "#E4572E"   # burnt orange: solo-billed
C_LEAD = "#2E86AB"   # blue: EDM lead with pop feature
C_FEAT = "#7FB069"   # green: EDM as featured act
C_COLLAB = "#F2A541" # amber: EDM+EDM
C_GREY = "#8A8A8A"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(CH / name, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def main():
    yearly = pd.read_csv(DATA / "yearly.csv", index_col=0)
    entries = pd.read_csv(DATA / "edm_entries.csv", parse_dates=["week"])
    f = json.load(open(DATA / "findings.json"))

    # 1. EDM's share of Hot 100 slots
    y = yearly[(yearly.index >= 2010) & (yearly.index <= 2026)]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(y.index, y["edm_share"] * 100, color=C_LEAD, width=0.75)
    ax.set_ylabel("Share of Hot 100 slots (%)")
    ax.set_title("EDM's share of the Hot 100: 7.4% at the 2017 peak, 0.3% by 2025")
    ax.annotate("2017 peak: 7.4%", (2017, 7.4), xytext=(2013.2, 6.4),
                arrowprops=dict(arrowstyle="->", color="black"))
    ax.annotate("2025: 0.35%", (2025, 0.35), xytext=(2021.5, 2.2),
                arrowprops=dict(arrowstyle="->", color="black"))
    ax.set_xticks(range(2010, 2027, 2))
    save(fig, "edm_share.png")

    # 2. Billing mix: share of EDM slots by billing type, per year
    mix = (entries.groupby(["year", "edm_type"]).size().unstack(fill_value=0))
    mix = mix.div(mix.sum(axis=1), axis=0) * 100
    order = ["solo", "edm_collab", "edm_lead", "edm_featured"]
    colors = {"solo": C_SOLO, "edm_collab": C_COLLAB,
              "edm_lead": C_LEAD, "edm_featured": C_FEAT}
    labels = {"solo": "Solo-billed DJ", "edm_collab": "DJ + DJ",
              "edm_lead": "DJ lead, pop feature", "edm_featured": "DJ as feature"}
    fig, ax = plt.subplots(figsize=(10, 5))
    bottom = np.zeros(len(mix))
    for t in order:
        if t in mix.columns:
            ax.bar(mix.index, mix[t], bottom=bottom, color=colors[t], label=labels[t], width=0.8)
            bottom += mix[t].values
    ax.set_ylabel("Share of EDM Hot 100 slots (%)")
    ax.set_title("The solo DJ's slice of the billing collapses after 2014")
    ax.legend(frameon=False, ncol=2, loc="upper center",
              bbox_to_anchor=(0.5, -0.12))
    ax.set_xticks(range(2010, 2027, 2))
    save(fig, "billing_mix.png")

    # 3. The collab gap: EDM vs the whole chart
    y2 = yearly[(yearly.index >= 2011) & (yearly.index <= 2024)]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(y2.index, y2["edm_collab_share"] * 100, "o-", color=C_SOLO, lw=2,
            label="EDM entries that are collaborations")
    ax.plot(y2.index, y2["collab_share_all"] * 100, "s-", color=C_GREY, lw=2,
            label="All Hot 100 entries that are collaborations")
    ax.fill_between(y2.index, y2["collab_share_all"] * 100,
                    y2["edm_collab_share"] * 100, color=C_SOLO, alpha=0.12)
    ax.set_ylabel("Share of chart slots that are collaborations (%)")
    ax.set_title("EDM's collaboration rate runs 28-73 points above the rest of the chart")
    ax.legend(frameon=False, loc="lower right")
    ax.set_xticks(range(2011, 2025, 2))
    ax.set_ylim(0, 105)
    save(fig, "collab_gap.png")

    # 4. Survival curves by era
    fig, ax = plt.subplots(figsize=(10, 5))
    surv = f["survival_by_era"]
    era_colors = {"boom": "#2E86AB", "toll": "#7FB069",
                  "fade": "#E4572E", "remnant": "#8A8A8A"}
    for era in ["boom", "toll", "fade", "remnant"]:
        ks = sorted(int(k) for k in surv[era])
        ax.plot(ks, [surv[era][str(k)] * 100 for k in ks], "o-",
                color=era_colors[era], lw=2,
                label=f"{era} (median {f['longevity_by_era'][era]['median']:.0f} wks)")
    ax.set_xlabel("Weeks on the chart")
    ax.set_ylabel("Share of EDM songs still charting (%)")
    ax.set_title("EDM hits stopped lasting: half of boom-era songs survived 20 weeks")
    ax.legend(frameon=False)
    save(fig, "survival.png")

    # 5. Concentration: distinct lead artists vs top-3 slot share
    conc = pd.DataFrame(f["concentration_by_year"]).set_index("year")
    conc = conc[(conc.index >= 2010) & (conc.index <= 2026)]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(conc.index, conc["distinct_lead_artists"], color=C_LEAD, width=0.75,
           label="Distinct EDM lead artists charting")
    ax.set_ylabel("Distinct EDM lead artists")
    ax2 = ax.twinx()
    ax2.plot(conc.index, conc["top3_slot_share"] * 100, "o-", color=C_SOLO, lw=2,
             label="Top-3 artists' share of EDM slots")
    ax2.set_ylabel("Top-3 share of EDM slots (%)")
    ax2.spines["top"].set_visible(False)
    ax2.grid(False)
    ax.set_title("The remnant is two men: 19 EDM acts charted in 2018, 3 in 2025")
    ax.set_xticks(range(2010, 2027, 2))
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.12), ncol=1)
    save(fig, "concentration.png")

    # 6. SHAP: what predicts a top-40 (spoiler: almost nothing about the song)
    model = json.load(open(DATA / "model.json"))
    frame = pd.read_csv(DATA / "model_frame.csv")
    sv = np.load(DATA / "shap_values.npy")
    feats = model["features"]
    pretty = {"prior_top40": "Lead artist's prior top-40s",
              "prior_songs": "Lead artist's prior Hot 100 songs",
              "debut_year": "Debut year",
              "n_artists": "Number of credited artists",
              "is_featured": "EDM act is the feature",
              "is_solo": "Solo-billed DJ",
              "era_toll_plus": "Debuted 2015 or later",
              "is_edm_collab": "DJ + DJ collab",
              "era_remnant": "Debuted 2021 or later"}
    fig, ax = plt.subplots(figsize=(10, 5))
    shap.summary_plot(sv, frame[feats].rename(columns=pretty), show=False,
                      plot_size=None, max_display=9)
    fig = plt.gcf()
    fig.set_size_inches(10, 5)
    fig.suptitle("What predicts a top-40 EDM song? Incumbency, not billing (CV AUC 0.55)",
                 fontsize=12)
    save(fig, "shap.png")


if __name__ == "__main__":
    main()
