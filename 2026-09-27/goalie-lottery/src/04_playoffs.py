"""04_playoffs.py — who decides a playoff series: the goalie or the skaters?

Uses regular-season team GSAx (goalie battle) and xGF% (skater battle) to
predict playoff series (2015–2025, excl. the 2019-20 bubble). Compares hit rates
and fits logistic models on standardized differentials.

Outputs: figures/04_series.png, printed findings.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "figures"


def mcfadden_r2(y, X):
    m = LogisticRegression(max_iter=2000).fit(X, y)
    p1 = m.predict_proba(X)[:, 1]
    ll = np.sum(np.log(np.clip(np.where(y == 1, p1, 1 - p1), 1e-12, 1)))
    p = y.mean()
    ll0 = len(y) * (p * np.log(p) + (1 - p) * np.log(1 - p))
    return 1 - ll / ll0, m


def main():
    ser = pd.read_csv(PROC / "playoff_series.csv")
    # orient every series from team1's perspective
    ser["d_gsax"] = ser["gsax1"] - ser["gsax2"]
    ser["d_xgf"] = ser["xgfpct1"] - ser["xgfpct2"]
    ser["t1win"] = (ser["winner"] == ser["team1"]).astype(int)
    print(f"series: {len(ser)}")

    hit_g = ser["better_goalie_won"].mean()
    hit_s = ser["better_skaters_won"].mean()
    print("=== hit rates (regular-season edge -> series win) ===")
    print(f"better regular-season goalie (GSAx) wins series: {hit_g:.1%}  (n={len(ser)})")
    print(f"better regular-season skaters (xGF%) wins:       {hit_s:.1%}")

    # P(team1 wins) by which battles team1 won — the clean cut
    ser["g1"] = ser["d_gsax"] > 0
    ser["s1"] = ser["d_xgf"] > 0
    piv = ser.groupby(["g1", "s1"])["t1win"].agg(["mean", "count"])
    print("\nP(team1 wins series) by battles team1 won [goalie-battle, skater-battle]:")
    print(piv)
    only_g = piv.loc[(True, False)]
    only_s = piv.loc[(False, True)]
    print(f"\nwon goalie battle ONLY -> {only_g['mean']:.1%} (n={only_g['count']})")
    print(f"won skater battle ONLY -> {only_s['mean']:.1%} (n={only_s['count']})")

    X = StandardScaler().fit_transform(ser[["d_gsax", "d_xgf"]])
    y = ser["t1win"].values
    r2_full, m_full = mcfadden_r2(y, X)
    r2_g, m_g = mcfadden_r2(y, X[:, [0]])
    r2_s, m_s = mcfadden_r2(y, X[:, [1]])
    print("\n=== logistic: P(team1 wins) ~ standardized differentials ===")
    print(f"McFadden R2  goalie-only: {r2_g:.3f} | skater-only: {r2_s:.3f} | both: {r2_full:.3f}")
    print(f"odds ratios (1 SD): GSAx x{np.exp(m_full.coef_[0][0]):.2f}, "
          f"xGF% x{np.exp(m_full.coef_[0][1]):.2f}")

    # --- the "hot goalie" check: do Cup winners ride playoff goaltending?
    pg = pd.read_csv(PROC / "playoff_team_gsax.csv")
    wins = ser.groupby(["season", "winner"]).size().reset_index(name="sw")
    champs = wins[wins["sw"] == 4][["season", "winner"]].rename(columns={"winner": "team"})
    champs = champs.merge(pg, on=["season", "team"], how="left")
    # rank each champ's playoff GSAx among that season's playoff teams
    pg["rank"] = pg.groupby("season")["po_GSAx"].rank(ascending=False)
    champs = champs.merge(pg[["season", "team", "rank"]], on=["season", "team"])
    n_playoff = pg.groupby("season")["team"].nunique()
    champs["n"] = champs["season"].map(n_playoff)
    print("\n=== Cup winners: where did their playoff goaltending rank? ===")
    for r in champs.sort_values("season").itertuples():
        print(f"  {r.season}-{str(r.season+1)[-2:]} {r.team}: playoff GSAx rank "
              f"{int(r.rank)} of {int(r.n)} ({r.po_GSAx:+.1f})")
    print(f"  median rank: {champs['rank'].median():.1f} of ~16 "
          f"| champs with top-5 playoff GSAx: {(champs['rank'] <= 5).sum()}/{len(champs)}")

    # regular-season GSAx rank of champs, for contrast
    tm = pd.read_csv(PROC / "team_season.csv")
    tm["rs_rank"] = tm.groupby("season")["team_GSAx"].rank(ascending=False)
    champs2 = champs[["season", "team"]].merge(tm[["season", "team", "rs_rank"]],
                                              on=["season", "team"])
    print(f"  median REGULAR-season GSAx rank of champs: {champs2['rs_rank'].median():.1f}")

    # --- figure: P(win) by battles won (from the pivot table above)
    order = [(True, True), (True, False), (False, True), (False, False)]
    labels = ["Won both\nbattles", "Won goalie\nbattle only",
              "Won skater\nbattle only", "Won neither\nbattle"]
    vals = [piv.loc[o, "mean"] for o in order]
    ns = [int(piv.loc[o, "count"]) for o in order]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    colors = ["#27ae60", "#2980b9", "#2c3e50", "#c0392b"]
    bars = ax.bar(labels, vals, color=colors, width=0.6, edgecolor="white")
    ax.axhline(0.5, color="gray", ls="--", lw=1)
    ax.set_ylim(0, 1)
    ax.set_ylabel("P(team wins the series)")
    ax.set_title(f"Win the crease AND the ice, or go home: {len(ser)} playoff series, 2015–2025",
                 fontsize=12, pad=10)
    for b, v, nn in zip(bars, vals, ns):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.0%}\n(n={nn})",
                ha="center", fontsize=10)
    ax.text(0.5, -0.26,
            "Battles measured on REGULAR-season numbers (team GSAx for goalies, xGF% for skaters).\n"
            "2019-20 bubble excluded. Data: MoneyPuck + NHL API.",
            ha="center", va="top", fontsize=9, color="#555", transform=ax.transAxes)
    fig.tight_layout()
    fig.savefig(FIG / "04_series.png", dpi=150)
    print("\nwrote figures/04_series.png")


if __name__ == "__main__":
    main()
