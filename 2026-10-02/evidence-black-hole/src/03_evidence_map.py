"""
Part 1 — the evidence map.

Per intervention (using only trials old enough to have finished: started
<= 2022, status COMPLETED / TERMINATED / WITHDRAWN / SUSPENDED):
  - n_finished, share that posted results on the registry (has_results)
  - completion rate (COMPLETED vs terminated/withdrawn)
  - median enrollment, industry-sponsor share, median sites
Then:
  - z-scored KMeans clustering (k=4) of interventions into evidence
    archetypes, and
  - a scatter: finished-trial volume (x) vs results-posting rate (y),
    bubble = median enrollment, colour = archetype.

Outputs: output/evidence_map.csv, output/clusters.csv,
         charts/evidence_map.png, charts/sponsor_gap.png
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
OUT, CH = ROOT / "output", ROOT / "charts"
FINISHED = ["COMPLETED", "TERMINATED", "WITHDRAWN", "SUSPENDED"]


def main():
    OUT.mkdir(exist_ok=True)
    CH.mkdir(exist_ok=True)
    df = pd.read_csv(ROOT / "data" / "trials.csv")
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce", format="mixed")
    df["start_year"] = df["start_date"].dt.year

    mature = df[(df["start_year"] <= 2022) & (df["overall_status"].isin(FINISHED))].copy()

    def agg(g):
        completed = (g["overall_status"] == "COMPLETED").mean()
        return pd.Series(
            {
                "n_finished": len(g),
                "results_rate": g["has_results"].mean(),
                "completion_rate": completed,
                "median_enrollment": g["enrollment_count"].median(),
                "industry_share": (g["lead_sponsor_class"] == "INDUSTRY").mean(),
                "median_sites": g["n_locations"].median(),
                "share_randomized": (g["allocation"] == "RANDOMIZED").mean(),
                "share_fda_drug": (g["is_fda_regulated_drug"] == True).mean(),  # noqa: E712
            }
        )

    ev = mature.groupby("intervention").apply(agg, include_groups=False)
    # PubMed merge (optional file from 02; degrade gracefully)
    pm_path = ROOT / "data" / "pubmed_counts.csv"
    if pm_path.exists():
        pm = pd.read_csv(pm_path).set_index("intervention")
        ev = ev.join(pm)
        totals = json.loads((ROOT / "data" / "registry_totals.json").read_text())
        ev["registry_total"] = [totals.get(i, {}).get("registry_total") for i in ev.index]
        ev["papers_per_trial"] = ev["pubmed_total"] / ev["registry_total"]
    ev = ev.sort_values("results_rate", ascending=False)
    ev.to_csv(OUT / "evidence_map.csv")

    # ---- clustering (interventions with >=15 finished trials only) ----
    feats = ["results_rate", "completion_rate", "median_enrollment",
             "industry_share", "median_sites", "share_randomized"]
    cl = ev.dropna(subset=feats)
    cl = cl[cl["n_finished"] >= 15].copy()
    X = StandardScaler().fit_transform(np.log1p(cl[feats].assign(median_enrollment=cl["median_enrollment"])))
    # log1p on enrollment only: rebuild properly
    cl_t = cl[feats].copy()
    cl_t["median_enrollment"] = np.log1p(cl_t["median_enrollment"])
    cl_t["median_sites"] = np.log1p(cl_t["median_sites"])
    X = StandardScaler().fit_transform(cl_t)
    km = KMeans(n_clusters=4, n_init=20, random_state=42)
    cl["cluster"] = km.fit_predict(X)
    cl_out = cl[["cluster", "n_finished", "results_rate", "completion_rate"]].copy()
    cl_out.to_csv(OUT / "clusters.csv")

    # ---- chart 1: the black-hole map ----
    fig, ax = plt.subplots(figsize=(10, 6.5))
    cmap = plt.get_cmap("tab10")
    label_of = cl["cluster"].to_dict()
    for name, row in ev.iterrows():
        c = label_of.get(name)
        ax.scatter(row["n_finished"], row["results_rate"] * 100,
                   s=max(30, (row["median_enrollment"] or 10) * 1.2),
                   color=cmap(c) if c is not None else "grey",
                   alpha=0.75, edgecolor="white")
        ax.annotate(name.replace(" (benchmark)", "*"), (row["n_finished"], row["results_rate"] * 100),
                    fontsize=7.5, xytext=(4, 4), textcoords="offset points")
    ax.set_xscale("log")
    ax.set_xlabel("Finished trials started ≤2022 (log scale)")
    ax.set_ylabel("% of finished trials that posted results")
    ax.set_title("The evidence black hole: lots of trials start,\nmost never report back  (bubble = median enrollment, * = drug benchmark)")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(CH / "evidence_map.png", dpi=160)
    plt.close(fig)

    # ---- chart 2: who sponsors, who reports ----
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    s = ev.sort_values("industry_share")
    axes[0].barh(s.index, s["industry_share"] * 100, color="#b5651d")
    axes[0].set_xlabel("% industry-sponsored (finished trials)")
    axes[0].set_title("Who pays for the trial")
    s2 = ev.sort_values("results_rate")
    axes[1].barh(s2.index, s2["results_rate"] * 100, color="#2b6cb0")
    axes[1].set_xlabel("% finished trials posting results")
    axes[1].set_title("Who reports back")
    for a in axes:
        a.tick_params(labelsize=7)
        a.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(CH / "sponsor_gap.png", dpi=160)
    plt.close(fig)

    print(ev.round(3).to_string())
    print("\nclusters:\n", cl_out.to_string())


if __name__ == "__main__":
    main()
