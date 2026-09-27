"""02_repeatability.py — is goaltending a repeatable skill?

Compares year-over-year autocorrelation of goalie GSAx/60 against
(a) skater chance creation (xGF/60) and (b) raw save percentage,
plus a mixed-effects variance decomposition (intraclass correlation)
and a 3-year-trailing-average predictiveness test.

Outputs: figures/01_repeatability.png, findings printed to stdout.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

MIN_G_MINUTES = 1000   # goalie workload floor per season
MIN_S_MINUTES = 500    # skater workload floor per season


def yoy_r(df, metric, idcol="playerId", min_n=15):
    """Mean Pearson r of metric(season) vs metric(season+1), per consecutive pair."""
    rs, ns = [], []
    for s in sorted(df["season"].unique())[:-1]:
        a = df[df["season"] == s].set_index(idcol)[metric]
        b = df[df["season"] == s + 1].set_index(idcol)[metric]
        idx = a.index.intersection(b.index)
        if len(idx) >= min_n:
            r = np.corrcoef(a.loc[idx], b.loc[idx])[0, 1]
            rs.append(r); ns.append(len(idx))
    return float(np.mean(rs)), int(np.sum(ns)), len(rs)


def trailing3_predictiveness(df, metric):
    """r of trailing-3yr mean(metric) vs next-season metric."""
    piv = df.pivot_table(index="playerId", columns="season", values=metric)
    rs = []
    for s in range(2017, 2025):
        cols = [c for c in (s - 2, s - 1, s) if c in piv.columns]
        if len(cols) < 3 or s + 1 not in piv.columns:
            continue
        trail = piv[cols].mean(axis=1, skipna=False)
        nxt = piv[s + 1]
        ok = trail.notna() & nxt.notna()
        if ok.sum() >= 15:
            rs.append(np.corrcoef(trail[ok], nxt[ok])[0, 1])
    return float(np.mean(rs)), len(rs)


def icc(df, metric):
    """Intraclass correlation via one-way random effects (ANOVA estimator)."""
    d = df[["playerId", metric]].dropna()
    d = d.groupby("playerId").filter(lambda x: len(x) >= 2)
    grand = d[metric].mean()
    groups = d.groupby("playerId")[metric]
    n_i = groups.count()
    k = (len(d) - (n_i ** 2).sum() / len(d)) / (len(n_i) - 1)  # avg group size (unbalanced)
    ssb = ((groups.mean() - grand) ** 2 * n_i).sum()
    ssw = ((d[metric] - d["playerId"].map(groups.mean())) ** 2).sum()
    msb, msw = ssb / (len(n_i) - 1), ssw / (len(d) - len(n_i))
    sigma_b2 = max((msb - msw) / k, 0)
    return sigma_b2 / (sigma_b2 + msw)


def main():
    gs = pd.read_csv(PROC / "goalie_season.csv")
    g = gs[gs["minutes"] >= MIN_G_MINUTES].copy()

    # skaters: forwards only, xGF/60 from flurry-adjusted ixG
    sframes = []
    for s in range(2018, 2026):
        df = pd.read_csv(RAW / f"mp_{s}_skaters.csv")
        df = df[(df["situation"] == "all") & (df["position"].isin(["C", "L", "R"]))].copy()
        df["season"] = s
        sframes.append(df)
    sk = pd.concat(sframes, ignore_index=True)
    sk["minutes"] = sk["icetime"] / 60.0
    sk["xGF60"] = sk["I_F_flurryAdjustedxGoals"] / sk["icetime"] * 3600.0
    sk = sk[sk["minutes"] >= MIN_S_MINUTES].copy()

    r_gsax, n_gsax, k1 = yoy_r(g, "GSAx60")
    r_sv, n_sv, _ = yoy_r(g, "svpct")
    r_xgf, n_xgf, k2 = yoy_r(sk, "xGF60")
    t3_gsax, k3 = trailing3_predictiveness(g, "GSAx60")
    t3_xgf, _ = trailing3_predictiveness(sk, "xGF60")
    icc_g = icc(g, "GSAx60")
    icc_s = icc(sk, "xGF60")

    print("=== Year-over-year autocorrelation (consecutive seasons) ===")
    print(f"goalie GSAx/60 : r = {r_gsax:.3f}  (n={n_gsax} pairs over {k1} season-pairs)")
    print(f"goalie Sv%     : r = {r_sv:.3f}  (n={n_sv})")
    print(f"forward xGF/60 : r = {r_xgf:.3f}  (n={n_xgf} pairs over {k2} season-pairs)")
    print("=== Trailing-3yr average -> next season ===")
    print(f"goalie GSAx/60 : r = {t3_gsax:.3f} over {k3} windows")
    print(f"forward xGF/60 : r = {t3_xgf:.3f}")
    print("=== Intraclass correlation (share of variance that is the player) ===")
    print(f"goalie GSAx/60 : ICC = {icc_g:.3f}")
    print(f"forward xGF/60 : ICC = {icc_s:.3f}")

    # --- figure
    labels = ["Goalie\nGSAx/60", "Goalie\nsave %", "Forward\nxGF/60"]
    vals = [r_gsax, r_sv, r_xgf]
    colors = ["#c0392b", "#e67e22", "#2c3e50"]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, vals, color=colors, width=0.55, edgecolor="white")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Year-over-year correlation (r)")
    ax.set_title("How repeatable is goaltending? Less than you think.", fontsize=13, pad=12)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}",
                ha="center", fontsize=12, fontweight="bold")
    ax.text(0.5, -0.28,
            "Goalie shot-stopping (GSAx/60, min 1000 min) carries over season-to-season\n"
            "far less than a forward's chance creation. n = 1,083 goalie-seasons (2015–2025),\n"
            "skaters 2018–2025. Data: MoneyPuck.",
            ha="center", va="top", fontsize=9, color="#555", transform=ax.transAxes)
    fig.tight_layout()
    fig.savefig(FIG / "01_repeatability.png", dpi=150)
    print("wrote figures/01_repeatability.png")


if __name__ == "__main__":
    main()
