"""Draft surplus analysis: how much NHL value does each draft slot produce,
and which teams beat (or squander) their draft capital?

Inputs:  data/drafts.csv (2005-2018 picks), data/careers.csv (career NHL totals)
Outputs: figures/fig1..fig5.png and printed findings (also saved to findings.txt)

Run: python3 src/03_analysis.py   (run from the project root)
"""
import csv, math, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

plt.rcParams.update({"figure.dpi": 130, "font.size": 10, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.titlesize": 12, "axes.titleweight": "bold"})

# Franchise continuity: Atlanta -> Winnipeg (2011), Phoenix/Arizona -> Utah (2024)
FRANCHISE = {"ATL": "WPG", "PHX": "UTA", "ARI": "UTA"}

def franchise(t):
    return FRANCHISE.get(t, t)

def exp_decay(x, a, b, c):
    return a * np.exp(-b * x) + c

def main():
    drafts = pd.read_csv("data/drafts.csv")
    careers = pd.read_csv("data/careers.csv", dtype={"playerId": str})
    drafts["playerId"] = drafts["playerId"].apply(lambda x: "" if pd.isna(x) else str(int(x)))
    df = drafts.merge(careers, on="playerId", how="left", suffixes=("", "_c"))
    assert (df["gp"].notna()).sum() > 2500, "merge failed: career stats did not join"
    df["gp"] = df["gp"].fillna(0).astype(int)
    df["points"] = df["points"].fillna(0).astype(int)
    df["is_goalie"] = df["position"].str.upper() == "G"
    df["franchise"] = df["team"].map(franchise)
    print(f"total picks: {len(df)}, skaters: {(~df.is_goalie).sum()}, goalies: {df.is_goalie.sum()}")

    # ---------- 1. Expected value curves (binned means + exponential fit) ----------
    bins = [1,2,3,4,5,6,8,10,12,15,20,25,31,40,50,65,80,100,125,150,180,211,300]
    df["bin"] = pd.cut(df["overall"], bins=bins)
    grp = df.groupby("bin", observed=True).agg(
        n=("overall","size"), mid=("overall","mean"),
        mean_gp=("gp","mean"),
        mean_pts_skater=("points", lambda s: s[~df.loc[s.index,"is_goalie"]].mean()),
    ).reset_index(drop=True).dropna()

    pg, _ = curve_fit(exp_decay, grp["mid"], grp["mean_gp"], p0=(400, 0.02, 20), maxfev=20000)
    ps, _ = curve_fit(exp_decay, grp["mid"], grp["mean_pts_skater"], p0=(300, 0.02, 10), maxfev=20000)
    xs = np.linspace(1, 225, 400)
    print(f"expected GP curve: {pg[0]:.1f}*exp(-{pg[1]:.4f}*x)+{pg[2]:.1f}")
    print(f"expected PTS curve: {ps[0]:.1f}*exp(-{ps[1]:.4f}*x)+{ps[2]:.1f}")

    df["exp_gp"] = exp_decay(df["overall"], *pg)
    df["exp_pts"] = exp_decay(df["overall"], *ps)
    df["surplus_gp"] = df["gp"] - df["exp_gp"]
    df["surplus_pts"] = np.where(~df["is_goalie"], df["points"] - df["exp_pts"], np.nan)
    df.to_csv("data/draft_values.csv", index=False)

    # ---------- 2. Key numbers ----------
    findings = []
    def note(s):
        findings.append(s); print(s)

    for pk in [1, 10, 31, 100, 200]:
        note(f"Expected career value of pick #{pk}: {exp_decay(pk,*pg):.0f} GP / {exp_decay(pk,*ps):.0f} pts (skaters)")
    note(f"Picks that never played an NHL game: {(df.gp==0).mean()*100:.1f}% "
         f"(1st round: {((df.gp==0)&(df['round']==1)).sum()/(df['round']==1).sum()*100:.1f}%, "
         f"rounds 5-7: {((df.gp==0)&(df['round']>=5)).mean()*100:.1f}%)")
    note(f"Share of 1st-rounders reaching 500 GP: {((df.gp>=500)&(df['round']==1)).sum()/(df['round']==1).sum()*100:.1f}%")
    note(f"Share of 1st-rounders reaching 300 pts: {(((df.points>=300)&~df.is_goalie)&(df['round']==1)).sum()/((~df.is_goalie)&(df['round']==1)).sum()*100:.1f}%")

    # ---------- 3. Steals and busts ----------
    steals = df[~df.is_goalie & (df.overall >= 90)].nlargest(10, "surplus_pts")
    note("Biggest draft steals (skaters, picked 90+):")
    for _, r in steals.iterrows():
        note(f"  #{int(r.overall)} {r['name']} ({r['team']}, {int(r.draftYear)}): "
             f"{int(r.points)} pts vs {r.exp_pts:.0f} expected (+{r.surplus_pts:.0f})")
    busts = df[df.overall <= 15].nsmallest(10, "surplus_pts")
    note("Biggest early-pick disappointments (picked 1-15):")
    for _, r in busts.iterrows():
        note(f"  #{int(r.overall)} {r['name']} ({r['team']}, {int(r.draftYear)}): "
             f"{int(r.points)} pts / {int(r.gp)} GP vs {r.exp_pts:.0f} expected pts")

    # ---------- 4. Team drafting efficiency ----------
    tg = df.groupby("franchise").agg(picks=("overall","size"),
                                     surplus_gp=("surplus_gp","sum"),
                                     surplus_pts=("surplus_pts","sum")).reset_index()
    tg["surplus_gp_per_pick"] = tg["surplus_gp"] / tg["picks"]
    tg["surplus_pts_per_pick"] = tg["surplus_pts"] / tg["picks"]
    tg = tg.sort_values("surplus_gp", ascending=False)
    tg.to_csv("data/team_surplus.csv", index=False)
    note("Team draft surplus 2005-2018, total career games above expected (top 5):")
    for _, r in tg.head(5).iterrows():
        note(f"  {r.franchise}: +{r.surplus_gp:.0f} GP over {int(r.picks)} picks (+{r.surplus_gp_per_pick:.1f}/pick)")
    note("Bottom 5:")
    for _, r in tg.tail(5).iterrows():
        note(f"  {r.franchise}: {r.surplus_gp:+.0f} GP over {int(r.picks)} picks ({r.surplus_gp_per_pick:+.1f}/pick)")

    # Goalies by round
    gr = df.groupby("round").agg(gp_sk=("gp", lambda s: s[~df.loc[s.index,"is_goalie"]].mean()),
                                 gp_g=("gp", lambda s: s[df.loc[s.index,"is_goalie"]].mean()),
                                 n_g=("is_goalie","sum")).reset_index()
    gr.to_csv("data/goalie_by_round.csv", index=False)
    r1 = gr[gr["round"]==1].iloc[0]
    note(f"First-round goalies ({int(r1.n_g)} picked) averaged {r1.gp_g:.0f} career GP vs "
         f"{r1.gp_sk:.0f} for first-round skaters")

    # ================= FIGURES =================
    os.makedirs("figures", exist_ok=True)
    dark = "#1b2a4a"

    # fig1: expected value curve (games)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.scatter(grp["mid"], grp["mean_gp"], s=grp["n"]*0.9, alpha=0.65, color=dark, label="binned mean (size = # picks)")
    ax.plot(xs, exp_decay(xs, *pg), color="#c0392b", lw=2.5, label="exponential fit")
    for pk, lab, dx, dy in [(1, "1st overall", 62, -90), (31, "end of 1st round", 28, 38), (100, "#100", 28, 38)]:
        ax.annotate(f"{lab}\n~{exp_decay(pk,*pg):.0f} GP", xy=(pk, exp_decay(pk,*pg)),
                    xytext=(pk+dx, exp_decay(pk,*pg)+dy), fontsize=9,
                    arrowprops=dict(arrowstyle="->", color="gray"))
    ax.set_xlabel("Overall draft pick"); ax.set_ylabel("Expected career NHL games played")
    ax.set_title("The Draft Value Cliff: expected NHL games by draft slot (2005-2018)")
    ax.legend(); fig.tight_layout(); fig.savefig("figures/fig1_value_curve.png"); plt.close(fig)

    # fig2: skater points curve + steals annotated
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.scatter(grp["mid"], grp["mean_pts_skater"], s=grp["n"]*0.9, alpha=0.65, color=dark)
    ax.plot(xs, exp_decay(xs, *ps), color="#c0392b", lw=2.5, label="expected points fit")
    for _, r in steals.head(5).iterrows():
        ax.annotate(f"{r['name'].split()[-1]} (#{int(r.overall)})", xy=(r.overall, r.points),
                    xytext=(r.overall+12, r.points+15), fontsize=8,
                    arrowprops=dict(arrowstyle="->", color="gray"))
    ax.scatter(steals["overall"], steals["points"], color="#27ae60", s=40, zorder=5, label="top steals")
    ax.set_xlabel("Overall draft pick"); ax.set_ylabel("Expected career points (skaters)")
    ax.set_title("Skater points by draft slot — and the late-round steals that broke the curve")
    ax.legend(); fig.tight_layout(); fig.savefig("figures/fig2_steals.png"); plt.close(fig)

    # fig3: team surplus
    tgp = tg.sort_values("surplus_gp")
    fig, ax = plt.subplots(figsize=(8.5, 9))
    colors = ["#27ae60" if v > 0 else "#c0392b" for v in tgp["surplus_gp"]]
    ax.barh(tgp["franchise"], tgp["surplus_gp"], color=colors, alpha=0.85)
    ax.axvline(0, color="black", lw=1)
    ax.set_xlabel("Total career games above/below expected from 2005-2018 picks")
    ax.set_title("Which franchises actually beat the draft? (total surplus, 2005-2018)")
    fig.tight_layout(); fig.savefig("figures/fig3_team_surplus.png"); plt.close(fig)

    # fig4: per-pick surplus (fairer comparison)
    tpp = tg.sort_values("surplus_gp_per_pick")
    fig, ax = plt.subplots(figsize=(8.5, 9))
    colors = ["#27ae60" if v > 0 else "#c0392b" for v in tpp["surplus_gp_per_pick"]]
    ax.barh(tpp["franchise"], tpp["surplus_gp_per_pick"], color=colors, alpha=0.85)
    ax.axvline(0, color="black", lw=1)
    ax.set_xlabel("Surplus career games per draft pick")
    ax.set_title("Draft efficiency per pick (controls for teams that simply had more picks)")
    fig.tight_layout(); fig.savefig("figures/fig4_team_per_pick.png"); plt.close(fig)

    # fig5: hit rates by round
    hr = df.groupby("round").agg(hit200=("gp", lambda s: (s>=200).mean()*100),
                                 hit500=("gp", lambda s: (s>=500).mean()*100)).reset_index()
    fig, ax = plt.subplots(figsize=(8.5, 5))
    x = hr["round"]; w = 0.35
    ax.bar(x - w/2, hr["hit200"], w, label="played 200+ NHL games", color=dark, alpha=0.9)
    ax.bar(x + w/2, hr["hit500"], w, label="played 500+ NHL games", color="#c0392b", alpha=0.85)
    ax.set_xlabel("Draft round"); ax.set_ylabel("% of picks")
    ax.set_xticks(x); ax.set_title("Draft hit rates: what share of picks become real NHL players?")
    ax.legend(); fig.tight_layout(); fig.savefig("figures/fig5_hit_rates.png"); plt.close(fig)

    open("findings.txt", "w").write("\n".join(findings) + "\n")
    print("\nfigures + findings.txt written")

if __name__ == "__main__":
    main()
