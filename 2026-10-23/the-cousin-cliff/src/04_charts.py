"""
04_charts.py - all figures. Reads only committed data/ outputs.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
CH = os.path.join(HERE, "..", "charts")
os.makedirs(CH, exist_ok=True)
plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(CH, name), bbox_inches="tight")
    plt.close(fig)
    print("chart", name)


def main():
    kin = pd.read_csv(os.path.join(DATA, "kinship_by_year.csv"))
    coh = pd.read_csv(os.path.join(DATA, "gss_cohorts.csv"))
    fert = pd.read_csv(os.path.join(DATA, "fertility_un_owid.csv"))
    sc = pd.read_csv(os.path.join(DATA, "scenarios.csv"))
    imp = pd.read_csv(os.path.join(DATA, "shap_importance.csv"))

    us = kin[kin.country == "United States"]
    obs = us[~us.projected]; proj = us[us.year >= 2023]

    # 1. The cousin cliff (US expected cousins by birth year)
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ax.plot(obs.year, obs.expected_cousins, color="#b34700", lw=2.5)
    ax.plot(proj.year, proj.expected_cousins, color="#b34700", lw=2.5, ls="--")
    pk = obs.loc[obs.expected_cousins.idxmax()]
    ax.annotate(f"peak: {pk.expected_cousins:.1f} cousins\n(born {int(pk.year)})",
                (pk.year, pk.expected_cousins), xytext=(pk.year - 16, pk.expected_cousins + 0.6))
    v23 = obs[obs.year == 2023].iloc[0]
    ax.annotate(f"born 2023: {v23.expected_cousins:.1f}", (2023, v23.expected_cousins),
                xytext=(2006, v23.expected_cousins + 2.2))
    ax.annotate("2055 if TFR stays at 2023 level: 2.0", (2055, 2.03), xytext=(2027, 0.4))
    ax.set_ylabel("Expected first cousins (US baby)")
    ax.set_title("The cousin cliff: cousins peak a generation after fertility does")
    save(fig, "cousin_cliff.png")

    # 2. The two legs of the product
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), sharey=False)
    axes[0].plot(obs.year, obs.aunts_uncles, color="#3366aa", lw=2.5)
    axes[0].plot(proj.year, proj.aunts_uncles, color="#3366aa", lw=2.5, ls="--")
    axes[0].set_title("Leg 1: aunts + uncles\n(set by grandparents' fertility)")
    axes[0].set_ylabel("expected count")
    axes[1].plot(obs.year, obs.tfr, color="#2a7f4f", lw=2.5)
    axes[1].plot(proj.year, proj.tfr, color="#2a7f4f", lw=2.5, ls="--")
    axes[1].set_title("Leg 2: kids per aunt/uncle\n(period TFR at baby's birth)")
    save(fig, "two_legs.png")

    # 3. Three countries
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    for c, col in [("United States", "#b34700"), ("Canada", "#3366aa"), ("China", "#7f2a7f")]:
        s = kin[(kin.country == c) & (~kin.projected)]
        ax.plot(s.year, s.expected_cousins, label=c, color=col, lw=2.2)
    ax.legend(frameon=False)
    ax.set_ylabel("Expected first cousins")
    ax.set_title("Same cliff, three speeds: expected cousins by baby's birth year")
    save(fig, "three_countries.png")

    # 4. GSS sibship by cohort
    sib = coh[coh.table == "sibship"]
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ax.bar(sib.decade.astype(str), sib.only_child_pct, color="#b34700", alpha=.85,
           label="Only child (%)")
    ax2 = ax.twinx()
    ax2.plot(sib.decade.astype(str), sib.mean_sibs, color="#3366aa", lw=2.5, marker="o",
             label="Mean siblings (child-weighted, sibs top-coded at 6)")
    ax.set_ylabel("Only children, % of people")
    ax2.set_ylabel("Mean siblings")
    ax.set_title("GSS: experienced sibship shrinks slowly (mean sibs 3.5 -> 2.8)")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9)
    save(fig, "gss_sibship.png")

    # 5. Scenarios
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    s2 = sc.iloc[::-1]
    ax.barh(s2.scenario, s2.expected_cousins, color="#b34700", alpha=.88)
    for i, v in enumerate(s2.expected_cousins):
        ax.text(v + 0.25, i, f"{v:.1f}", va="center")
    ax.set_xlabel("Expected first cousins")
    ax.set_title("One baby, six family trees")
    ax.set_xlim(0, max(sc.expected_cousins) * 1.18)
    save(fig, "scenarios.png")

    # 6. SHAP for childlessness
    fig, ax = plt.subplots(figsize=(8, 4.2))
    i2 = imp.iloc[::-1]
    ax.barh(i2.feature, i2.mean_abs_shap, color="#3366aa", alpha=.88)
    ax.set_xlabel("mean |SHAP| (childless by age 45-70, XGBoost)")
    ax.set_title("What sorts people into having no children at all?")
    save(fig, "shap_childless.png")

    # 7. TFR context
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    for c, col in [("United States", "#b34700"), ("Canada", "#3366aa"),
                   ("China", "#7f2a7f"), ("World", "#888888")]:
        s = fert[fert.Entity == c]
        ax.plot(s.Year, s["Fertility rate"], label=c, color=col, lw=2)
    ax.axhline(2.1, color="#444", lw=1, ls=":")
    ax.text(1952, 2.25, "replacement (2.1)", fontsize=9)
    ax.legend(frameon=False)
    ax.set_ylabel("Children per woman (period TFR)")
    ax.set_title("The input everyone watches - and the kin output nobody prices")
    save(fig, "tfr_context.png")


if __name__ == "__main__":
    main()
