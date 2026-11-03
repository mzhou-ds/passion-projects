"""Step 5: charts. Reads the analysis outputs, writes charts/*.png."""

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
COLORS = {"pioneer": "#8a5a2b", "peak-edm": "#2b6e8a", "new-wave": "#c23b5e"}
LABELS = {"pioneer": "Pioneers (pre-2013)",
          "peak-edm": "Peak-EDM gen (2013-2018)",
          "new-wave": "New wave (2019+)"}


def save(fig, name):
    fig.tight_layout()
    fig.savefig(f"charts/{name}", bbox_inches="tight")
    plt.close(fig)
    print(f"charts/{name}")


def main():
    s = pd.read_csv("data/artist_summary.csv")
    cy = pd.read_csv("data/cohort_year.csv")
    cb = pd.read_csv("data/career_curve.csv")
    er = pd.read_csv("data/era_stats.csv")

    fig, ax = plt.subplots(figsize=(9, 4.6))
    for cohort, g in cy.groupby("cohort"):
        gg = g[g["year"] >= 2010]
        ax.plot(gg["year"], gg["per_artist"], marker="o", ms=3,
                color=COLORS[cohort], label=LABELS[cohort])
    ax.set_ylabel("Singles+EPs per active artist")
    ax.set_xlabel("Release year")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("New-music output per artist, by generation")
    save(fig, "cohort_output_trend.png")

    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
    order = ["pioneer", "peak-edm", "new-wave"]
    agg = s.groupby("cohort").agg(recent=("recent_rate", "mean"),
                                  medyear=("median_year", "mean")).reindex(order)
    axes[0].bar([LABELS[c] for c in order], agg["recent"],
                color=[COLORS[c] for c in order])
    axes[0].set_ylabel("Singles+EPs / year, 2023-25")
    axes[0].set_title("Who is actually releasing now")
    axes[1].bar([LABELS[c] for c in order], agg["medyear"],
                color=[COLORS[c] for c in order])
    axes[1].set_ylabel("Mean median catalog year")
    axes[1].set_title("How old is each generation's catalog")
    for ax in axes:
        ax.tick_params(axis="x", labelsize=8, rotation=12)
    save(fig, "cohort_now_vs_catalog.png")

    fig, ax = plt.subplots(figsize=(9, 4.4))
    fmt = s.groupby("cohort")[["single_share"]].mean().reindex(order)
    ax.bar([LABELS[c] for c in order], fmt["single_share"],
           color=[COLORS[c] for c in order])
    ax.set_ylabel("Share of singles+EPs that are singles")
    ax.set_ylim(0, 1)
    ax.set_title("The single ate every generation's format mix")
    save(fig, "format_mix.png")

    # 4. The new wave is genre-pure: pop share + single length, 2019-25
    rel = pd.read_csv("data/releases_clean.csv")
    rel = rel[rel["record_type"].isin(["single", "ep"])]
    rel = rel[(rel["year"] >= 2019) & (rel["year"] <= 2025)]
    pop = rel.groupby("_panel_cohort")["is_pop"].mean().reindex(order)
    dur = rel[rel["record_type"] == "single"].groupby(
        "_panel_cohort")["single_duration"].mean().reindex(order) / 60
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
    axes[0].bar([LABELS[c] for c in order], pop * 100,
                color=[COLORS[c] for c in order])
    axes[0].set_ylabel("% of 2019-25 singles+EPs tagged Pop")
    axes[0].set_title("Pop tags: the new wave opts out")
    axes[1].bar([LABELS[c] for c in order], dur,
                color=[COLORS[c] for c in order])
    axes[1].set_ylabel("Mean single length, minutes (2019-25)")
    axes[1].set_title("New-wave singles run longer")
    for ax in axes:
        ax.tick_params(axis="x", labelsize=8, rotation=12)
    save(fig, "pop_generation.png")

    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
    er = er.set_index("era").reindex(["2005-2012", "2013-2018", "2019-2025"])
    axes[0].bar(er.index, er["collab_share"], color="#2b6e8a")
    axes[0].set_ylabel("Share of singles+EPs with 2+ artists")
    axes[0].set_title("Collaboration share by era")
    axes[1].bar(er.index, er["pop_share"], color="#c23b5e")
    axes[1].set_ylabel("Share tagged Pop")
    axes[1].set_title("Pop-tag share by era")
    for ax in axes:
        ax.tick_params(axis="x", labelsize=8, rotation=12)
    save(fig, "era_collab_pop.png")

    fig, ax = plt.subplots(figsize=(9, 5.0))
    for cname, g in s.groupby("cluster_name"):
        ax.scatter(g["lifetime_single_ep"], g["recent_rate"], s=70,
                   label=cname, alpha=0.85)
    for _, r in s.iterrows():
        ax.annotate(r["artist"], (r["lifetime_single_ep"], r["recent_rate"]),
                    fontsize=7.5, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("Lifetime singles+EPs")
    ax.set_ylabel("Singles+EPs / year, 2023-25")
    ax.set_title("Four release strategies in one scene")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "clusters.png")

    imp = pd.read_csv("data/shap_importance.csv", index_col=0).squeeze("columns")
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.barh(imp.index, imp.values, color="#2b6e8a")
    ax.set_xlabel("Mean |SHAP value| on recent release rate")
    ax.set_title("What predicts who still releases? (XGBoost, n=32)")
    save(fig, "shap_importance.png")


if __name__ == "__main__":
    main()
