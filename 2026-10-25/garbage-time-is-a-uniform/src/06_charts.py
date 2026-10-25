"""Charts for the README."""
import json
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
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def main() -> None:
    # 1. WP surface heatmap
    surf = pd.read_csv(os.path.join(DATA, "wp_surface.csv"))
    piv = surf.pivot(index="diff", columns="mins_bucket", values="wp").sort_index(ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4.6))
    im = ax.imshow(piv.values, cmap="RdYlBu", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(piv.columns)))
    ax.set_xticklabels([f"{int(b * 5)}-{int(b * 5 + 5)} min left" if b % 3 == 0 else "" for b in piv.columns])
    ax.set_yticks(range(len(piv.index)))
    ax.set_yticklabels([f"{int(d):+d}" for d in piv.index])
    ax.set_ylabel("shooter's goal differential")
    ax.set_title("Empirical win probability by score and clock\n(every shot, 2019-20 to 2024-25)")
    fig.colorbar(im, ax=ax, label="P(shooter's team wins)")
    fig.tight_layout(); fig.savefig(os.path.join(CH, "wp_surface.png"), dpi=150); plt.close(fig)

    # 2. Goal share vs shot share by bucket + conversion
    bs = pd.read_csv(os.path.join(DATA, "bucket_stats.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
    x = np.arange(len(bs))
    axes[0].bar(x - 0.2, bs.shot_share * 100, 0.4, label="share of shots")
    axes[0].bar(x + 0.2, bs.goal_share * 100, 0.4, label="share of goals")
    axes[0].set_xticks(x); axes[0].set_xticklabels(["decided", "0.2-0.4", "0.4-0.6", "0.6-0.8", "coin-flip"], rotation=20)
    axes[0].set_ylabel("%"); axes[0].legend(frameon=False)
    axes[0].set_title("A quarter of goals land in decided states")
    axes[1].bar(x, bs.conversion * 100, 0.55)
    axes[1].set_xticks(x); axes[1].set_xticklabels(["decided", "0.2-0.4", "0.4-0.6", "0.6-0.8", "coin-flip"], rotation=20)
    axes[1].set_ylabel("shooting %")
    axes[1].set_title("Conversion peaks in decided states\n(empty nets included)")
    fig.tight_layout(); fig.savefig(os.path.join(CH, "buckets.png"), dpi=150); plt.close(fig)

    # 3. Switcher test: own past vs new team as predictor of next share
    panel = pd.read_csv(os.path.join(DATA, "switcher_panel.csv"))
    sw = panel[panel.switched]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
    axes[0].scatter(sw.decided_share, sw.next_decided_share, s=18, alpha=0.7)
    axes[0].plot([0, 0.6], [0, 0.6], "k--", lw=0.8)
    axes[0].set_xlabel("his decided-goal share, old team")
    axes[0].set_ylabel("his decided-goal share, next season")
    axes[0].set_title("Predict from his own past: nothing")
    axes[1].scatter(sw.next_team_decided_share, sw.next_decided_share, s=18, alpha=0.7, color="darkorange")
    axes[1].plot([0, 0.6], [0, 0.6], "k--", lw=0.8)
    axes[1].set_xlabel("his NEW team's decided-goal share")
    axes[1].set_title("Predict from his new team: it lands")
    fig.tight_layout(); fig.savefig(os.path.join(CH, "switchers.png"), dpi=150); plt.close(fig)

    # 4. Star leverage-per-goal, extremes
    league_mean = json.load(open(os.path.join(DATA, "headline_stats.json")))["mean_leverage_all_goals"]
    stars = pd.read_csv(os.path.join(DATA, "star_profiles.csv"))
    top = pd.concat([stars.head(8), stars.tail(8)]).sort_values("leverage_per_goal")
    fig, ax = plt.subplots(figsize=(8, 5.2))
    colors = ["#c0392b" if v < 0.5 else "#2471a3" for v in top.leverage_per_goal]
    ax.barh(top.shooterName, top.leverage_per_goal, color=colors)
    ax.axvline(league_mean, color="grey", ls="--", lw=1)
    ax.text(0.54, -0.6, "league mean for goals", color="grey", fontsize=9)
    ax.set_xlabel("average leverage of his goals, 2019-20 to 2024-25 (150+ goals)")
    ax.set_title("Whose goals came in games still in doubt?")
    fig.tight_layout(); fig.savefig(os.path.join(CH, "stars.png"), dpi=150); plt.close(fig)

    # 5. SHAP bars for the uniform model
    imp = pd.read_csv(os.path.join(DATA, "shap_uniform.csv")).sort_values("mean_abs_shap")
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    ax.barh(imp.feature, imp.mean_abs_shap, color="#2471a3")
    ax.set_xlabel("mean |SHAP| — predicting next season's decided-goal share")
    ax.set_title("The uniform model: the new team is the signal")
    fig.tight_layout(); fig.savefig(os.path.join(CH, "shap_uniform.png"), dpi=150); plt.close(fig)

    print("charts written:", os.listdir(CH))


if __name__ == "__main__":
    main()
