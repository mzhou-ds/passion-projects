"""05_oilers.py — what is Edmonton's goaltending actually worth?

  1. Converts goals to standings points (OLS on 344 team-seasons).
  2. Prices the Oilers' 2025-26 goaltending: actual vs league-average crease.
  3. Benchmarks Tristan Jarry ($5.375M AAV through 2028, per PuckPedia via
     USA Today Sep 2026) against every other goalie in the $5-6M band.
  4. States the portfolio conclusion: since goalie performance is ~95% noise
     (see 02_repeatability), the optimal strategy is diversification, not
     star-buying.

Outputs: figures/05_oilers.png, printed findings.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "figures"


def main():
    tm = pd.read_csv(PROC / "team_season.csv")
    gs = pd.read_csv(PROC / "goalie_season.csv")
    sal = pd.read_csv(ROOT / "data" / "salaries_2026_27_goalies.csv")

    # 1. goals -> points
    slope, intercept, r, p, se = stats.linregress(tm["goal_diff"], tm["points"])
    print(f"points = {intercept:.1f} + {slope:.3f} * goal_diff   (R2={r**2:.3f}, n={len(tm)})")
    print(f"  => ~{1/slope:.1f} goals of differential = 1 standings point")

    # 2. Oilers 2025-26
    edm = tm[(tm["season"] == 2025) & (tm["team"] == "EDM")].iloc[0]
    avg_pts = intercept + slope * (edm["goal_diff"] - edm["team_GSAx"])  # avg crease
    good_pts = intercept + slope * (edm["goal_diff"] - edm["team_GSAx"] + 10)  # +10 GSAx starter
    print(f"\n=== Edmonton 2025-26 ===")
    print(f"record-relevant: {edm['points']:.0f} pts, goal diff {edm['goal_diff']:+.0f}, "
          f"team GSAx {edm['team_GSAx']:+.1f}")
    print(f"with league-average goaltending (0 GSAx): ~{avg_pts:.1f} pts "
          f"({avg_pts - edm['points']:+.1f} vs actual)")
    print(f"with a +10 GSAx starter instead: ~{good_pts:.1f} pts "
          f"({good_pts - edm['points']:+.1f} vs actual)")

    # Oilers crease history
    hist = tm[tm["team"] == "EDM"].sort_values("season")[["season", "team_GSAx", "points"]]
    print("\nOilers team GSAx by season:")
    print(hist.to_string(index=False))

    # 3. the $5-6M band
    tr = gs[gs["season"].isin([2023, 2024, 2025]) & (gs["minutes"] >= 500)]
    agg = (tr.groupby(["playerId", "name"], as_index=False)
             .agg(GSAx3=("GSAx", "sum"), min3=("minutes", "sum")))
    band = sal[(sal["cap_hit_m"] >= 5.0) & (sal["cap_hit_m"] <= 6.0)].merge(agg, on="name")
    band = band.sort_values("GSAx3")
    jarry = band[band["name"] == "Tristan Jarry"].iloc[0]
    print(f"\n=== the $5-6M goalie band (trailing-3yr GSAx) ===")
    for r in band.itertuples():
        mark = " <== JARRY (EDM)" if r.name == "Tristan Jarry" else ""
        print(f"  {r.name:28s} ${r.cap_hit_m:5.2f}M  GSAx3 {r.GSAx3:+6.1f}{mark}")
    rank = (band["GSAx3"] > jarry["GSAx3"]).sum() + 1
    print(f"Jarry ranks {rank} of {len(band)} in his own pay band on trailing performance.")

    # 4. figure
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["#c0392b" if n == "Tristan Jarry" else "#7f8c8d" for n in band["name"]]
    bars = ax.barh(band["name"], band["GSAx3"], color=colors)
    ax.axvline(0, color="black", lw=1)
    ax.set_xlabel("Trailing 3-year GSAx (2023–2025)")
    ax.set_title("What does $5–6M buy in a goalie? Jarry vs his pay band",
                 fontsize=12, pad=10)
    ax.text(0.98, 0.02,
            "Jarry: $5.375M AAV through 2028 (PuckPedia via USA Today, Sep 2026).\n"
            "GSAx: MoneyPuck flurry-adjusted.",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color="#555")
    fig.tight_layout()
    fig.savefig(FIG / "05_oilers.png", dpi=150)
    print("\nwrote figures/05_oilers.png")

    # portfolio math for the README
    print(f"\n=== portfolio note ===")
    print(f"ICC of goalie GSAx/60 = 0.053: ~95% of season-to-season variation is noise.")
    print(f"Two $2.7M goalies (independent draws) halve the variance vs one $5.4M goalie.")


if __name__ == "__main__":
    main()
