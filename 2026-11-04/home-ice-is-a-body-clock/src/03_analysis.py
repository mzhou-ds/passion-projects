"""Model the home edge: logistic regression of home_win on team quality
(Elo) plus schedule features. Then: raw splits, a schedule-neutral
counterfactual, a schedule-adjusted 'fortress' ranking, and a transfer
check that applies the regular-season model to playoff games.

Outputs: data/findings.json and charts/*.png.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = Path(__file__).resolve().parent.parent
CH = HERE / "charts"
CH.mkdir(exist_ok=True)

NAMES = {
    "ANA": "Ducks", "BOS": "Bruins", "BUF": "Sabres", "CAR": "Hurricanes",
    "CBJ": "Blue Jackets", "CGY": "Flames", "CHI": "Blackhawks",
    "COL": "Avalanche", "DAL": "Stars", "DET": "Red Wings", "EDM": "Oilers",
    "FLA": "Panthers", "LAK": "Kings", "MIN": "Wild", "MTL": "Canadiens",
    "NJD": "Devils", "NSH": "Predators", "NYI": "Islanders", "NYR": "Rangers",
    "OTT": "Senators", "PHI": "Flyers", "PIT": "Penguins", "SEA": "Kraken",
    "SJS": "Sharks", "STL": "Blues", "TBL": "Lightning", "TOR": "Maple Leafs",
    "UTA": "Mammoth", "VAN": "Canucks", "VGK": "Golden Knights",
    "WPG": "Jets", "WSH": "Capitals", "ARI": "Coyotes",
}
plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
C_MAIN, C_ACC, C_GREY = "#1f77b4", "#d62728", "#888888"


def design(df):
    X = pd.DataFrame({
        "elo_diff_100": df["elo_diff"] / 100,
        "rest_diff": df["rest_diff"],
        "away_b2b": df["away_b2b"],
        "home_b2b": df["home_b2b"],
        # Signed timezone shift, split: eastward hours (visitor loses time)
        # and westward hours (visitor gains time). Tests the clock asymmetry.
        "tz_east": df["tz_shift"].clip(lower=0),
        "tz_west": (-df["tz_shift"]).clip(lower=0),
        "travel_k": df["travel_miles"] / 1000,
        "trip_game": df["trip_game"].clip(upper=5),
    })
    for s in [20242025, 20252026, 20262027]:
        X[f"season_{s}"] = (df["season"] == s).astype(int)
    return sm.add_constant(X, has_constant="add")


def split_rate(df, col, bins, labels):
    d = df.copy()
    d["bin"] = pd.cut(d[col], bins=bins, labels=labels)
    out = d.groupby("bin", observed=True)["home_win"].agg(["mean", "count"])
    return out


def main():
    reg = pd.read_csv(HERE / "data" / "games_features.csv", parse_dates=["date"])
    po = pd.read_csv(HERE / "data" / "playoff_features.csv", parse_dates=["date"])
    X = design(reg)
    model = sm.Logit(reg["home_win"], X).fit(disp=0)
    reg = reg.copy()
    reg["pred"] = model.predict(X)
    print(model.summary2().tables[1].to_string())

    # ---- counterfactual: schedule-neutral game --------------------------------
    neutral = X.copy()
    for c in ["rest_diff", "away_b2b", "home_b2b", "tz_east", "tz_west"]:
        neutral[c] = 0
    neutral["trip_game"] = 1
    neutral["travel_k"] = 0.5  # short hop, e.g. a New York-area trip
    neutral_pred = model.predict(neutral).mean()
    observed = reg["home_win"].mean()
    explained = (observed - neutral_pred) / (observed - 0.5)
    print(f"observed {observed:.3f}  neutral {neutral_pred:.3f}  "
          f"schedule share of edge: {explained:.0%}")

    # Per-feature marginal effects at the mean (percentage points of win prob).
    def pp_effect(col, delta):
        up = X.copy()
        up[col] = up[col] + delta
        return (model.predict(up).mean() - reg["pred"].mean()) * 100

    effects = {
        "rest_diff_1day": pp_effect("rest_diff", 1),
        "away_b2b": pp_effect("away_b2b", 1),
        "home_b2b": pp_effect("home_b2b", 1),
        "tz_east_1h": pp_effect("tz_east", 1),
        "tz_west_1h": pp_effect("tz_west", 1),
        "travel_1000mi": pp_effect("travel_k", 1),
        "trip_game_1": pp_effect("trip_game", 1),
        "elo_100": pp_effect("elo_diff_100", 1),
    }

    # ---- raw splits ------------------------------------------------------------
    rest_bins = split_rate(reg, "rest_diff", [-7, -1.5, -0.5, 0.5, 1.5, 7],
                           ["<=-2", "-1", "0", "1", ">=2"])
    tz = reg.copy()
    tz["tz_bin"] = tz["abs_tz"].astype(int).clip(upper=3)
    tz_rates = tz.groupby("tz_bin")["home_win"].agg(["mean", "count"])
    dir_rates = tz.groupby(["tz_bin", "eastward"])["home_win"].agg(["mean", "count"])
    b2b_rates = reg.groupby("away_b2b")["home_win"].agg(["mean", "count"])
    trip_rates = reg.groupby(reg["trip_game"].clip(upper=4))["home_win"].agg(["mean", "count"])
    travel_q = reg.groupby(pd.qcut(reg["travel_miles"], 4))["home_win"].agg(["mean", "count"])

    # ---- fortress: residual home edge after schedule + Elo ----------------------
    fort = (reg.groupby("home")
            .apply(lambda d: pd.Series({
                "n": len(d), "obs": d["home_win"].mean(),
                "exp": d["pred"].mean()}), include_groups=False))
    fort["resid_pp"] = (fort["obs"] - fort["exp"]) * 100
    fort["se_pp"] = np.sqrt(fort["exp"] * (1 - fort["exp"]) / fort["n"]) * 100
    fort = fort.sort_values("resid_pp")
    fort.index.name = "team"

    # ---- visitor travel burden by building --------------------------------------
    burden = (reg.groupby("home")
              .agg(mean_travel=("travel_miles", "mean"),
                   mean_abs_tz=("abs_tz", "mean"),
                   n=("home_win", "size"))
              .sort_values("mean_travel", ascending=False))

    # ---- playoff transfer ---------------------------------------------------------
    Xpo = design(po)
    po = po.copy()
    po["pred"] = model.predict(Xpo)
    po_transfer = {"pred_mean": float(po["pred"].mean()),
                   "obs_mean": float(po["home_win"].mean()), "n": len(po)}

    findings = {
        "n_regular": len(reg), "n_playoff": len(po),
        "home_win_regular": float(observed),
        "home_win_playoff": float(po["home_win"].mean()),
        "neutral_pred": float(neutral_pred),
        "schedule_share_of_edge": float(explained),
        "effects_pp": {k: float(v) for k, v in effects.items()},
        "coef": {k: float(v) for k, v in model.params.items()},
        "pvalues": {k: float(v) for k, v in model.pvalues.items()},
        "pseudo_r2": float(model.prsquared),
        "rest_split": {str(k): {"rate": float(v["mean"]), "n": int(v["count"])}
                       for k, v in rest_bins.iterrows()},
        "tz_split": {str(k): {"rate": float(v["mean"]), "n": int(v["count"])}
                     for k, v in tz_rates.iterrows()},
        "tz_dir": {f"{k[0]}_{'east' if k[1] else 'west'}":
                   {"rate": float(v["mean"]), "n": int(v["count"])}
                   for k, v in dir_rates.iterrows()},
        "away_b2b_split": {str(k): {"rate": float(v["mean"]), "n": int(v["count"])}
                           for k, v in b2b_rates.iterrows()},
        "trip_split": {str(k): {"rate": float(v["mean"]), "n": int(v["count"])}
                       for k, v in trip_rates.iterrows()},
        "fortress": {t: {"resid_pp": float(r["resid_pp"]), "se_pp": float(r["se_pp"]),
                         "n": int(r["n"]), "obs": float(r["obs"]), "exp": float(r["exp"])}
                     for t, r in fort.iterrows()},
        "burden": {t: {"mean_travel": float(r["mean_travel"]),
                       "mean_abs_tz": float(r["mean_abs_tz"]), "n": int(r["n"])}
                   for t, r in burden.iterrows()},
        "playoff_transfer": po_transfer,
    }
    (HERE / "data" / "findings.json").write_text(json.dumps(findings, indent=2))

    # ---- charts -------------------------------------------------------------------
    def bar_chart(vals, labels, counts, title, fname, color=C_MAIN, ylim=(0.42, 0.62)):
        fig, ax = plt.subplots(figsize=(8.5, 4.6))
        bars = ax.bar(labels, vals, color=color)
        ax.axhline(0.5, color=C_ACC, ls="--", lw=1.2, label="Coin flip (50%)")
        for b, v, n in zip(bars, vals, counts):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.008, f"{v:.1%}\n(n={n:,})",
                    ha="center", fontsize=9)
        ax.set_ylim(*ylim)
        ax.set_ylabel("Home team win rate")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(CH / fname)
        plt.close(fig)

    bar_chart(rest_bins["mean"].tolist(), list(rest_bins.index),
              rest_bins["count"].tolist(),
              "Home win rate by rest differential (home rest minus visitor rest)",
              "rest_diff.png")
    # Timezone DIRECTION chart: pooled shift is flat, direction is everything.
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    hrs = [1, 2, 3]
    west = [dir_rates.loc[(h, 0), "mean"] for h in hrs]
    east = [dir_rates.loc[(h, 1), "mean"] for h in hrs]
    x = np.arange(len(hrs))
    w = 0.36
    ax.bar(x - w / 2, west, w, label="Visitor flew west (gained time)", color=C_MAIN)
    ax.bar(x + w / 2, east, w, label="Visitor flew east (lost time)", color=C_ACC)
    ax.axhline(0.5, color="black", ls="--", lw=1.0)
    ax.axhline(dir_rates.loc[(0, 0), "mean"], color=C_GREY, ls=":", lw=1.2,
               label="No timezone shift")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{h} hour{'s' if h > 1 else ''}" for h in hrs])
    ax.set_ylim(0.42, 0.64)
    ax.set_ylabel("Home team win rate")
    ax.set_title("Same shift, opposite effect: flying east hurts, flying west doesn't",
                 loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(CH / "tz_direction.png")
    plt.close(fig)
    bar_chart([b2b_rates.loc[0, "mean"], b2b_rates.loc[1, "mean"]],
              ["Visitor rested", "Visitor on a back-to-back"],
              [int(b2b_rates.loc[0, "count"]), int(b2b_rates.loc[1, "count"])],
              "Home win rate when the visitor played yesterday",
              "back_to_back.png")
    bar_chart(trip_rates["mean"].tolist(),
              [f"Game {i}" if i < 4 else "Game 4+" for i in trip_rates.index],
              trip_rates["count"].tolist(),
              "Home win rate by which game of the visitor's road trip it is",
              "trip_game.png")

    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.bar(["Coin flip", "Schedule-neutral\nmodel prediction", "Observed"],
           [0.5, neutral_pred, observed], color=[C_GREY, C_MAIN, C_ACC])
    for i, v in enumerate([0.5, neutral_pred, observed]):
        ax.text(i, v + 0.008, f"{v:.1%}", ha="center", fontweight="bold")
    ax.set_ylim(0.42, 0.60)
    ax.set_ylabel("Home team win rate")
    ax.set_title("Most of the home edge is the schedule, not the building",
                 loc="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(CH / "counterfactual.png")
    plt.close(fig)

    f2 = fort.reset_index()
    fig, ax = plt.subplots(figsize=(8.5, 7.5))
    colors = [C_ACC if t == "EDM" else C_MAIN for t in f2["team"]]
    ax.barh([NAMES.get(t, t) for t in f2["team"]], f2["resid_pp"], color=colors)
    ax.axvline(0, color="black", lw=1)
    ax.set_xlabel("Residual home edge after schedule + Elo (percentage points)")
    ax.set_title("True fortresses: residual home edge (Oilers highlighted)",
                 loc="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(CH / "fortress.png")
    plt.close(fig)

    print("fortress top/bottom:")
    print(fort.tail(5)[["n", "obs", "exp", "resid_pp"]].to_string())
    print(fort.head(5)[["n", "obs", "exp", "resid_pp"]].to_string())
    print("burden top:")
    print(burden.head(5).to_string())
    print("playoff transfer:", po_transfer)


if __name__ == "__main__":
    main()
