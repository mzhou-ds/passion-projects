"""03_market.py — price the goalie market.

Joins 2026-27 goalie cap hits (USA Today / PuckPedia, Sep 25 2026 — top 30)
with trailing 3-year GSAx (2023–2025, MoneyPuck) and asks:
  1. What does $1 of cap actually buy? ($ per trailing GSAx)
  2. Who is over/underpaid vs the market line?
  3. How much of the league's positive GSAx comes from goalies OUTSIDE
     the top-30 pay bracket (< $4M AAV)?

Outputs: figures/02_market_scatter.png, figures/03_value_gap.png,
         printed findings.
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

SOURCE = ("USA Today (Mike Brehm, Sep 25 2026), figures from PuckPedia: "
          "highest-paid goaltenders 2026-27 by cap hit")


def main():
    sal = pd.read_csv(ROOT / "data" / "salaries_2026_27_goalies.csv")
    gs = pd.read_csv(PROC / "goalie_season.csv")

    # trailing 3-year GSAx (2023-2025) = the information set teams had
    tr = gs[gs["season"].isin([2023, 2024, 2025]) & (gs["minutes"] >= 500)]
    agg = (tr.groupby(["playerId", "name"], as_index=False)
             .agg(GSAx3=("GSAx", "sum"), min3=("minutes", "sum")))
    agg["GSAx60_3"] = agg["GSAx3"] / agg["min3"] * 60

    m = sal.merge(agg, on="name", how="left")
    unmatched = m[m["GSAx3"].isna()]["name"].tolist()
    print("unmatched salary names:", unmatched)

    m = m.dropna(subset=["GSAx3"]).copy()
    r_total = stats.pearsonr(m["cap_hit_m"], m["GSAx3"])[0]
    r_rate = stats.pearsonr(m["cap_hit_m"], m["GSAx60_3"])[0]
    slope, intercept, *_ = stats.linregress(m["GSAx3"], m["cap_hit_m"])[:3]
    print(f"=== The market prices the past ===")
    print(f"corr(2026-27 cap hit, trailing-3yr GSAx)      = {r_total:.3f}  (n={len(m)})")
    print(f"corr(2026-27 cap hit, trailing-3yr GSAx/60)   = {r_rate:.3f}")
    print(f"market line: cap_hit = {intercept:.2f} + {slope:.3f} * GSAx3")
    print(f"  => ~${slope:.2f}M per goal of trailing GSAx; at r=0.176 predictiveness,")
    print(f"  each $1M buys only ~{0.176/slope:.1f} goals of *expected* future GSAx.")

    m["pred"] = intercept + slope * m["GSAx3"]
    m["resid_m"] = m["cap_hit_m"] - m["pred"]  # + = overpaid vs market line
    over = m.nlargest(5, "resid_m")[["name", "cap_hit_m", "GSAx3", "resid_m"]]
    under = m.nsmallest(5, "resid_m")[["name", "cap_hit_m", "GSAx3", "resid_m"]]
    print("\nmost OVERpaid vs the market line (cap hit $M, trailing GSAx, overpay $M):")
    print(over.to_string(index=False))
    print("\nmost UNDERpaid vs the market line:")
    print(under.to_string(index=False))

    # --- the moneyball stat: who produced the league's positive GSAx in 2025?
    # GSAx here is MoneyPuck's flurry-adjusted metric, used consistently
    # throughout (relative comparisons are unaffected by its league-wide offset).
    g25 = gs[gs["season"] == 2025].copy()
    paid_names = set(sal["name"])
    pos = g25[g25["GSAx"] > 0]
    share_rest = pos[~pos["name"].isin(paid_names)]["GSAx"].sum() / pos["GSAx"].sum()
    pay_pos = g25[g25["name"].isin(paid_names) & (g25["GSAx"] > 0)]["GSAx"].sum()
    print(f"\n=== 2025-26: who made the saves? ===")
    print(f"share of all positive GSAx from goalies OUTSIDE top-30 pay (<$4M AAV): {share_rest:.1%}")
    print(f"top-30 paid goalies produced {pay_pos:.1f} of {pos['GSAx'].sum():.1f} positive GSAx")
    print(f"  while consuming ${sal['cap_hit_m'].sum():.1f}M of league-wide goalie cap")

    # --- figure 1: scatter
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(m["GSAx3"], m["cap_hit_m"], s=55, alpha=0.7, color="#2c3e50", zorder=3)
    xs = np.linspace(m["GSAx3"].min(), m["GSAx3"].max(), 100)
    ax.plot(xs, intercept + slope * xs, color="#c0392b", lw=2, ls="--",
            label=f"market line (${slope:.2f}M per trailing GSAx)")
    for _, r in m.iterrows():
        if r["name"] in ("Igor Shesterkin", "Dustin Wolf", "Tristan Jarry",
                         "Jeremy Swayman", "Logan Thompson", "Sergei Bobrovsky",
                         "Connor Hellebuyck", "Andrei Vasilevskiy"):
            ax.annotate(r["name"].split()[-1], (r["GSAx3"], r["cap_hit_m"]),
                        fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("Trailing 3-year GSAx (2023–2025, MoneyPuck)")
    ax.set_ylabel("2026-27 cap hit ($M)")
    ax.set_title("The goalie market pays for the past — which barely predicts the future",
                 fontsize=12, pad=10)
    ax.legend(fontsize=9)
    ax.text(0.02, 0.98,
            "Trailing-3yr GSAx predicts next-season GSAx at r = 0.18.\n"
            f"Teams pay ~${slope:.2f}M per goal of past GSAx — pricing noise.",
            transform=ax.transAxes, va="top", fontsize=9, color="#555",
            bbox=dict(boxstyle="round", fc="white", ec="#ccc", alpha=0.9))
    fig.tight_layout()
    fig.savefig(FIG / "02_market_scatter.png", dpi=150)

    # --- figure 2: value gap bars
    sel = pd.concat([over.head(4), under.head(4)]).sort_values("resid_m")
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#27ae60" if v < 0 else "#c0392b" for v in sel["resid_m"]]
    bars = ax.barh(sel["name"], sel["resid_m"], color=colors)
    ax.axvline(0, color="black", lw=1)
    ax.set_xlabel("Over(+) / under(−) paid vs the market line ($M AAV)")
    ax.set_title("Biggest goalie contracts vs what the market line says they're worth",
                 fontsize=12, pad=10)
    fig.tight_layout()
    fig.savefig(FIG / "03_value_gap.png", dpi=150)
    print("\nwrote figures/02_market_scatter.png, figures/03_value_gap.png")
    print("salary source:", SOURCE)


if __name__ == "__main__":
    main()
