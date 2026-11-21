"""Charts for The Release Glut.

Part A (always): Discogs genre counts + Beatport Top 100 snapshot.
Part B (when data/results_samples.json exists): format mix, demand collapse,
label concentration, SHAP importances.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "..", "data")
CH = os.path.join(BASE, "..", "charts")
os.makedirs(CH, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "-",
    "axes.axisbelow": True, "figure.dpi": 150,
})
C = {"electronic": "#D9481C", "rock": "#2E5E8C", "hip hop": "#2E7D4F",
     "pop": "#8E6BBF", "grey": "#6B7280"}


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(CH, name), bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def part_a():
    df = pd.read_csv(os.path.join(DATA, "counts_by_genre_year.csv"), index_col=0)
    # 1. supply divergence, raw + lag-corrected electronic
    fig, ax = plt.subplots(figsize=(9, 5))
    for g in ("electronic", "rock", "pop", "hip hop"):
        ax.plot(df.index, df[g] / 1000, label=g.title(), color=C[g], lw=2.2)
    ax.plot(df.index[17:], df["electronic_lagcorr"].iloc[17:] / 1000,
            color=C["electronic"], lw=2.2, ls="--",
            label="Electronic, lag-corrected (pop control)")
    ax.axvspan(2021.5, 2026.6, color="#9CA3AF", alpha=0.10)
    ax.text(2023.55, 62, "cataloguing lag:\nrecent years still\nbeing added",
            ha="center", fontsize=9.5, color="#4B5563")
    ax.annotate("2020 peak: 199,047\n(+11.7% in a single year)",
                xy=(2020, 199), xytext=(2012.6, 206),
                arrowprops=dict(arrowstyle="->", color=C["electronic"]),
                fontsize=10, color=C["electronic"])
    ax.set_ylabel("Discogs releases catalogued per year (thousands)")
    ax.set_xlabel("Release year")
    ax.set_title("Electronic releases doubled while pop stood still (Discogs, 2005-2026)",
                 loc="left")
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    ax.set_xlim(2005, 2026)
    ax.set_ylim(0, 225)
    save(fig, "01_supply_divergence.png")

    # 2. format flip 2005 vs 2020 (population counts, data/format_totals.csv)
    ft = pd.read_csv(os.path.join(DATA, "format_totals.csv"))
    fmt = ft[ft["year"].isin([2005, 2020])].pivot(
        index="format", columns="year", values="releases")
    fmt = fmt.reindex(["Vinyl", "CD", "CDr", "File", "Cassette"])
    fmt.columns = ["2005", "2020"]
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(fmt.index))
    w = 0.38
    ax.bar(x - w / 2, fmt["2005"], w, label="2005", color="#9CA3AF")
    ax.bar(x + w / 2, fmt["2020"], w, label="2020", color=C["electronic"])
    for i, f in enumerate(fmt.index):
        ax.text(i - w / 2, fmt.loc[f, "2005"] + 3000, f"{fmt.loc[f, '2005']:,}",
                ha="center", fontsize=10)
        ax.text(i + w / 2, fmt.loc[f, "2020"] + 3000, f"{fmt.loc[f, '2020']:,}",
                ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(x, fmt.index)
    ax.set_ylabel("Electronic releases catalogued")
    ax.set_title("The format flip: files went 10.6k -> 146.4k in fifteen years\n"
                 "while CD and CDr collapsed and vinyl shrank (Discogs, electronic)",
                 loc="left")
    ax.legend(frameon=False)
    ax.set_ylim(0, 165000)
    save(fig, "02_format_flip.png")

    # 3. Beatport BPM histogram
    bp = pd.read_csv(os.path.join(DATA, "raw", "beatport_top100_2026-11-21.csv"))
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.hist(bp["bpm"], bins=np.arange(80, 145, 2), color=C["electronic"],
            edgecolor="white")
    ax.axvspan(128, 132, color="#F59E0B", alpha=0.25)
    ax.text(130, ax.get_ylim()[1] * 0.92 if ax.get_ylim()[1] else 30,
            "60% sit in 128-132 BPM", ha="center", fontsize=10,
            color="#92400E")
    ax.set_xlabel("BPM")
    ax.set_ylabel("Tracks in Beatport Top 100")
    ax.set_title("The DJ chart lives in a 12-BPM corridor: 92% of the Top 100\n"
                 "is 124-136 BPM (Beatport Top 100, 21 Nov 2026)", loc="left")
    save(fig, "03_beatport_bpm.png")

    # 4. Beatport age: cumulative share released within N days
    bp["age_days"] = (pd.Timestamp("2026-11-21") -
                      pd.to_datetime(bp["release_date"])).dt.days
    days = np.arange(0, 400)
    cum = [(bp["age_days"] <= d).mean() * 100 for d in days]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(days, cum, color=C["electronic"], lw=2.2)
    ax.axhline(50, color=C["grey"], ls=":", lw=1)
    ax.axvline(29, color=C["grey"], ls=":", lw=1)
    ax.annotate("median age: 29 days", xy=(29, 50), xytext=(90, 68),
                arrowprops=dict(arrowstyle="->", color=C["grey"]), fontsize=10)
    ax.annotate("3 tracks are over a year old\n(2013, 2019, Nov 2025)",
                xy=(365, 97), xytext=(210, 88),
                arrowprops=dict(arrowstyle="->", color=C["grey"]), fontsize=10)
    ax.set_xlabel("Days since release")
    ax.set_ylabel("% of Top 100 released within N days")
    ax.set_xlim(0, 400)
    ax.set_ylim(0, 102)
    ax.set_title("Half the Beatport Top 100 is less than a month old",
                 loc="left")
    save(fig, "04_beatport_age.png")

    # 5. Beatport keys
    fig, ax = plt.subplots(figsize=(9, 4.6))
    kc = bp["key"].value_counts()
    minor = kc[[k for k in kc.index if "Min" in k]].sum()
    ax.barh(["Minor keys", "Major keys"], [minor, 100 - minor],
            color=[C["electronic"], "#9CA3AF"])
    for i, v in enumerate([minor, 100 - minor]):
        ax.text(v + 1.5, i, f"{v}%", va="center", fontsize=12, fontweight="bold")
    ax.set_xlim(0, 72)
    ax.set_title("62% of the Beatport Top 100 is in a minor key",
                 loc="left")
    save(fig, "05_beatport_keys.png")


def part_b():
    path = os.path.join(DATA, "results_samples.json")
    if not os.path.exists(path):
        print("skip part B (no results_samples.json yet)")
        return
    est = json.load(open(path))
    elec = {int(k.split("_")[1]): v for k, v in est.items()
            if k.startswith("electronic_")}
    years = sorted(elec)

    # 6. format mix over time (weighted shares)
    fmts = ["Vinyl", "File", "CD", "CDr", "Cassette"]
    fig, ax = plt.subplots(figsize=(9, 5))
    bottom = np.zeros(len(years))
    colors = {"Vinyl": "#2E5E8C", "File": "#D9481C", "CD": "#9CA3AF",
              "CDr": "#6B7280", "Cassette": "#E9B44C"}
    for f in fmts:
        vals = [elec[y]["format_mix_pct"].get(f, 0) for y in years]
        ax.bar([str(y) for y in years], vals, bottom=bottom,
               label=f, color=colors[f])
        for i, v in enumerate(vals):
            if v > 6:
                ax.text(i, bottom[i] + v / 2, f"{v:.0f}%", ha="center",
                        va="center", fontsize=10, color="white",
                        fontweight="bold")
        bottom += np.array(vals)
    ax.set_ylabel("Share of electronic releases (%)")
    ax.set_title("The shelf went digital: files are now almost two-thirds of\n"
                 "electronic releases (HT-weighted Discogs sample)", loc="left")
    ax.legend(frameon=False, ncol=4, loc="upper center",
              bbox_to_anchor=(0.5, -0.08))
    save(fig, "06_format_mix.png")

    # 7. demand collapse: median collectors + zero-collector share by year
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4.6))
    hm = [elec[y]["have_median"] for y in years]
    ax1.plot(years, hm, "o-", color=C["electronic"], lw=2.4, ms=8)
    for x, v in zip(years, hm):
        ax1.annotate(f"{v:.0f}", (x, v), textcoords="offset points",
                     xytext=(0, 10), ha="center", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Median Discogs collectors per release")
    ax1.set_title("Median collectors", loc="left", fontsize=11)
    z = [elec[y]["have_zero_pct"] for y in years]
    ax2.plot(years, z, "o-", color=C["electronic"], lw=2.4, ms=8)
    for x, v in zip(years, z):
        ax2.annotate(f"{v:.0f}%", (x, v), textcoords="offset points",
                     xytext=(0, 10), ha="center", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Releases owned by nobody (%)")
    ax2.set_title("Zero-collector share", loc="left",
                  fontsize=11)
    fig.suptitle("The audience per release collapsed", fontsize=13, x=0.02,
                 ha="left")
    save(fig, "07_demand_collapse.png")

    # 8. label concentration
    fig, ax = plt.subplots(figsize=(9, 5))
    hhi = [elec[y]["label_hhi"] for y in years]
    top10 = [elec[y]["top10_label_share_pct"] for y in years]
    ax2 = ax.twinx()
    ax.plot(years, hhi, "o-", color=C["electronic"], lw=2.4, ms=8,
            label="Label HHI")
    ax2.plot(years, top10, "s--", color="#2E5E8C", lw=2, ms=7,
             label="Top-10 label share (%)")
    ax.set_ylabel("Herfindahl-Hirschman Index (labels)")
    ax2.set_ylabel("Top-10 labels' share of releases (%)")
    ax.set_xlabel("Release year")
    ax.set_title("The gatekeepers dissolved: label concentration fell as\n"
                 "supply doubled (HT-weighted Discogs sample)", loc="left")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    fig.legend(h1 + h2, l1 + l2, frameon=False, loc="upper center",
               bbox_to_anchor=(0.5, -0.02), ncol=2)
    save(fig, "08_label_concentration.png")

    # 10. format gap: median collectors by format within each cohort
    fig, ax = plt.subplots(figsize=(9, 5))
    fmts = ["Vinyl", "CD", "Cassette", "CDr", "File"]
    x = np.arange(len(fmts))
    wdt = 0.24
    colors = {2005: "#9CA3AF", 2015: "#2E5E8C", 2025: "#D9481C"}
    for i, y in enumerate(years):
        vals = [elec[y]["format_have"].get(f, {}).get("have_median", np.nan)
                for f in fmts]
        ax.bar(x + (i - 1) * wdt, vals, wdt, label=str(y), color=colors[y])
        for j, v in enumerate(vals):
            if not np.isnan(v):
                ax.text(j + (i - 1) * wdt, v + 1.5, f"{v:.0f}", ha="center",
                        fontsize=9)
    ax.set_xticks(x, fmts)
    ax.set_ylabel("Median Discogs collectors per release")
    ax.set_title("The format is the audience: vinyl collects, files don't\n"
                 "median collectors within each release year", loc="left")
    ax.legend(frameon=False, title="Release year")
    ax.set_ylim(0, 95)
    save(fig, "10_format_gap.png")

    # 9. SHAP importances
    mm = os.path.join(DATA, "model_metrics.json")
    if os.path.exists(mm):
        m = json.load(open(mm))
        items = list(m["shap_top"].items())
        labels = {"first_format_Vinyl": "Format: Vinyl",
                  "age_years": "Age (years)",
                  "first_format_File": "Format: File",
                  "first_format_CD": "Format: CD",
                  "has_master": "Has a master entry",
                  "label_n": "Label size (releases)",
                  "n_styles": "Styles listed",
                  "country_group_Other": "Country: other",
                  "is_album": "Is an album",
                  "year": "Release year",
                  "country_group_Netherlands": "Country: Netherlands",
                  "is_exp": "Style: Experimental"}
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.barh([labels.get(k, k) for k, _ in items][::-1],
                [v for _, v in items][::-1],
                color=C["electronic"])
        ax.set_xlabel("Mean |SHAP value| (log1p collectors per year)")
        ax.set_title("What predicts whether a release gets collected?\n"
                     f"XGBoost, 5-fold CV R2 = {m['cv_r2_mean']}", loc="left")
        save(fig, "09_shap.png")


if __name__ == "__main__":
    part_a()
    part_b()
    print("DONE")
