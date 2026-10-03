"""
Part 3 — trends: the longevity-era acceleration, and a simple forecast.

- Trials started per year (2010-2025) for supplement interventions vs the
  two drug benchmarks.
- Share of trials that are industry-sponsored, by year.
- Naive trend forecast (linear on 2015-2024 counts, with the obvious
  caveats in the README) for supplement-trial starts through 2028.

Outputs: output/yearly_trends.csv, charts/trends.png
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT, CH = ROOT / "output", ROOT / "charts"
BENCH = {"Metformin (benchmark)", "Sirolimus/rapamycin (benchmark)"}


def main():
    OUT.mkdir(exist_ok=True)
    CH.mkdir(exist_ok=True)
    df = pd.read_csv(ROOT / "data" / "trials.csv")
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce", format="mixed")
    df["start_year"] = df["start_date"].dt.year
    df = df[(df["start_year"] >= 2010) & (df["start_year"] <= 2025)].copy()
    df["is_benchmark"] = df["intervention"].isin(BENCH)

    yearly = (
        df.groupby(["start_year", "is_benchmark"])
        .agg(starts=("nct_id", "count"),
             industry_share=("lead_sponsor_class", lambda s: (s == "INDUSTRY").mean()))
        .reset_index()
    )
    yearly.to_csv(OUT / "yearly_trends.csv", index=False)

    supp = yearly[~yearly["is_benchmark"]].set_index("start_year")
    bench = yearly[yearly["is_benchmark"]].set_index("start_year")

    # naive linear forecast on supplement starts, 2015-2024
    fit_years = np.arange(2015, 2025)
    fit_vals = supp.loc[2015:2024, "starts"].values
    coef = np.polyfit(fit_years, fit_vals, 1)
    future_years = np.arange(2025, 2029)
    forecast = np.polyval(coef, future_years)
    fc = pd.DataFrame({"year": future_years, "forecast_starts": np.round(forecast, 0)})
    fc.to_csv(OUT / "forecast.csv", index=False)
    print("forecast:\n", fc.to_string(index=False))
    print("slope starts/yr:", round(float(coef[0]), 1))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    axes[0].plot(supp.index, supp["starts"], marker="o", label="18 supplements", color="#2b6cb0")
    axes[0].plot(bench.index, bench["starts"], marker="s", label="2 drug benchmarks", color="#b5651d")
    axes[0].plot(future_years, forecast, "--", color="#2b6cb0", alpha=0.6, label="supplement trend →")
    axes[0].set_title("Trials started per year")
    axes[0].set_xlabel("Start year")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.25)

    axes[1].plot(supp.index, supp["industry_share"] * 100, marker="o", color="#2b6cb0", label="supplements")
    axes[1].plot(bench.index, bench["industry_share"] * 100, marker="s", color="#b5651d", label="benchmarks")
    axes[1].set_title("Industry-sponsored share of starts (%)")
    axes[1].set_xlabel("Start year")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(CH / "trends.png", dpi=160)
    plt.close(fig)
    print(yearly.to_string(index=False))


if __name__ == "__main__":
    main()
