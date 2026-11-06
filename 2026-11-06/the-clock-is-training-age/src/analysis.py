"""Analysis: when do powerlifters peak, and what clock sets the peak?

Reads data/careers.parquet + data/meets_clean.parquet (from prep.py).
Writes results.json, findings.txt and charts/*.png
"""
import json
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
CH = os.path.join(ROOT, "charts")

plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
NAVY, TEAL, RUST, GOLD, GREY = "#1f3a5f", "#2a9d8f", "#c05621", "#b7791f", "#8a8a8a"

COHORTS = ["<25", "25-34", "35-44", "45+"]
COHORT_BINS = [0, 25, 35, 45, 200]


def cohort(age):
    return pd.cut(age, bins=COHORT_BINS, labels=COHORTS)


def med_iqr(s):
    s = s.dropna()
    return {"median": float(s.median()), "q1": float(s.quantile(0.25)),
            "q3": float(s.quantile(0.75)), "n": int(len(s))}


def main():
    careers = pd.read_parquet(os.path.join(DATA, "careers.parquet"))
    meets = pd.read_parquet(os.path.join(DATA, "meets_clean.parquet"))
    careers["cohort"] = cohort(careers["age_first"])
    res = {}

    # ---------------------------------------------------------------- panel
    res["panel"] = {
        "lifters": int(len(careers)),
        "meets": int(len(meets)),
        "one_meet_share": float((careers["n_meets"] == 1).mean()),
        "one_meet_n": int((careers["n_meets"] == 1).sum()),
        "median_meets": float(careers["n_meets"].median()),
        "share_5plus_meets": float((careers["n_meets"] >= 5).mean()),
        "share_10plus_meets": float((careers["n_meets"] >= 10).mean()),
    }
    meets_dist = careers["n_meets"].value_counts().sort_index()
    res["meets_per_lifter"] = {str(k): int(v) for k, v in
                               meets_dist[meets_dist.index <= 10].items()}
    res["meets_per_lifter"]["11+"] = int((careers["n_meets"] > 10).sum())

    # ------------------------------------------------- peak sample definition
    peak = careers[careers["completed"] & (careers["n_meets"] >= 3)].copy()
    res["peak_sample_n"] = int(len(peak))
    res["peak_sample_by_sex"] = {k: int(v) for k, v in peak["Sex"].value_counts().items()}

    # ------------------------------------------------- 1. age at best vs training age at best
    for sex in ["M", "F"]:
        sub = peak[peak["Sex"] == sex]
        res[f"age_best_{sex}"] = med_iqr(sub["age_best"])
        res[f"train_age_best_{sex}"] = med_iqr(sub["train_age_best"])
    res["age_best_all"] = med_iqr(peak["age_best"])
    res["train_age_best_all"] = med_iqr(peak["train_age_best"])

    # ------------------------------------------------- 2. the clock: age at best vs age at start
    by_cohort = {}
    for c in COHORTS:
        sub = peak[peak["cohort"] == c]
        by_cohort[c] = {
            "n": int(len(sub)),
            "age_first": med_iqr(sub["age_first"]),
            "age_best": med_iqr(sub["age_best"]),
            "train_age_best": med_iqr(sub["train_age_best"]),
            "best_dots": med_iqr(sub["best_dots"]),
        }
    res["by_start_cohort"] = by_cohort
    # regression: age at best ~ age at first meet
    reg = {}
    for sex in ["M", "F", "all"]:
        sub = peak if sex == "all" else peak[peak["Sex"] == sex]
        x, y = sub["age_first"].values, sub["age_best"].values
        slope, intercept, r, p, _ = st.linregress(x, y)
        rho, prho = st.spearmanr(x, y)
        reg[sex] = {"slope": float(slope), "intercept": float(intercept),
                    "r": float(r), "p": float(p), "spearman": float(rho),
                    "spearman_p": float(prho), "n": int(len(sub))}
    res["regression_age_best_on_age_first"] = reg

    # ------------------------------------------------- 3. peak strength at matched training age
    matched = peak[(peak["train_age_best"] >= 4) & (peak["train_age_best"] <= 8)].copy()
    res["matched_n"] = int(len(matched))
    matched_dots = {}
    for sex in ["M", "F"]:
        for c in COHORTS:
            sub = matched[(matched["Sex"] == sex) & (matched["cohort"] == c)]
            matched_dots[f"{sex}_{c}"] = med_iqr(sub["best_dots"])
    res["matched_best_dots"] = matched_dots
    # late starters as % of early starters, matched training age
    ratio = {}
    for sex in ["M", "F"]:
        young = matched[(matched["Sex"] == sex) & (matched["cohort"] == "<25")]["best_dots"].median()
        late = matched[(matched["Sex"] == sex) & (matched["cohort"] == "45+")]["best_dots"].median()
        ratio[sex] = {"late_over_young_pct": float(100 * late / young),
                      "young_median": float(young), "late_median": float(late)}
    res["late_vs_young_matched"] = ratio
    # stricter: training age >= 5 (any length), and >= 8
    for lo, label in [(5, "ge5"), (8, "ge8")]:
        sub = peak[peak["train_age_best"] >= lo]
        d = {}
        for sex in ["M", "F"]:
            y = sub[(sub["Sex"] == sex) & (sub["cohort"] == "<25")]["best_dots"].median()
            l = sub[(sub["Sex"] == sex) & (sub["cohort"] == "45+")]["best_dots"].median()
            d[sex] = {"late_over_young_pct": float(100 * l / y),
                      "n_late": int(((sub["Sex"] == sex) & (sub["cohort"] == "45+")).sum())}
        res[f"late_vs_young_train_age_{label}"] = d

    # ------------------------------------------------- 4. gains curve (normalized DOTS by training year)
    multi = careers[careers["n_meets"] >= 5][["Name", "Sex", "best_dots", "age_first"]].copy()
    multi["cohort"] = cohort(multi["age_first"])
    m = meets.merge(multi, on=["Name", "Sex"], suffixes=("", "_best"))
    m["train_year_bin"] = np.floor(m["train_year"]).astype(int)
    m = m[m["train_year_bin"] <= 10]
    m["norm_dots"] = 100 * m["Dots"] / m["best_dots"]
    gains = (m.groupby(["cohort", "train_year_bin"], observed=True)["norm_dots"]
             .agg(["median", "count"]).reset_index())
    res["gains_curve"] = {
        f"{c}_{int(y)}": {"median_pct_of_best": float(v), "n": int(n)}
        for c, y, v, n in zip(gains["cohort"], gains["train_year_bin"],
                              gains["median"], gains["count"]) if n >= 30}
    # years to reach 90% / 95% of best, by cohort (median across lifters)
    reach = {}
    for c in COHORTS:
        sub = m[m["cohort"] == c]
        per = (sub.groupby(["Name", "Sex", "train_year_bin"], observed=True)["norm_dots"]
               .max().reset_index())
        first90 = per[per["norm_dots"] >= 90].groupby(["Name", "Sex"])["train_year_bin"].min()
        first95 = per[per["norm_dots"] >= 95].groupby(["Name", "Sex"])["train_year_bin"].min()
        reach[c] = {"years_to_90pct": med_iqr(first90),
                    "years_to_95pct": med_iqr(first95)}
    res["years_to_peak_share"] = reach

    # ------------------------------------------------- 5. age curve raw vs training-age-matched
    peak["age_band"] = pd.cut(peak["age_best"], bins=[0, 25, 30, 35, 40, 45, 50, 55, 60, 200],
                              labels=["<25", "25-29", "30-34", "35-39", "40-44",
                                      "45-49", "50-54", "55-59", "60+"])
    matched["age_band"] = peak.loc[matched.index, "age_band"]
    raw_curve = peak.groupby("age_band", observed=True)["best_dots"].median()
    matched_curve = matched.groupby("age_band", observed=True)["best_dots"].median()
    res["age_curve_raw"] = {str(k): float(v) for k, v in raw_curve.items()}
    res["age_curve_matched_train_age_4_8"] = {str(k): float(v) for k, v in matched_curve.items()}
    # decline from peak band to 55-59, raw vs matched
    def decline(curve):
        base = curve.get("30-34", np.nan)
        late = curve.get("55-59", np.nan)
        return float(100 * late / base) if pd.notna(base) and pd.notna(late) else None
    res["decline_to_55_59_pct_of_30s"] = {"raw": decline(raw_curve),
                                         "matched": decline(matched_curve)}

    # ------------------------------------------------- 6. comebacks after >=3y gaps
    mm = meets.sort_values(["Name", "Sex", "Date"]).copy()
    mm["prev_date"] = mm.groupby(["Name", "Sex"])["Date"].shift(1)
    mm["gap_years"] = (mm["Date"] - mm["prev_date"]).dt.days / 365.25
    returned = mm[mm["gap_years"] >= 3][["Name", "Sex", "Date"]].drop_duplicates()
    res["comeback_lifters"] = int(len(returned))
    res["comeback_share_of_lifters"] = float(len(returned) / len(careers))
    # regain: best DOTS within 2y after return vs best DOTS before the gap
    regain = []
    mm_idx = mm.set_index(["Name", "Sex"])
    for _, row in returned.iterrows():
        key = (row["Name"], row["Sex"])
        try:
            hist = mm_idx.loc[key]
        except KeyError:
            continue
        if isinstance(hist, pd.Series):
            hist = hist.to_frame().T
        before = hist[hist["Date"] < row["Date"]]["Dots"].max()
        after = hist[(hist["Date"] >= row["Date"]) &
                     (hist["Date"] <= row["Date"] + pd.Timedelta(days=730))]["Dots"].max()
        if pd.notna(before) and pd.notna(after) and before > 0:
            regain.append(100 * after / before)
    regain = pd.Series(regain)
    res["comeback_regain_pct"] = med_iqr(regain)
    res["comeback_regain_ge95_share"] = float((regain >= 95).mean()) if len(regain) else None
    res["comeback_regain_ge90_share"] = float((regain >= 90).mean()) if len(regain) else None

    # ------------------------------------------------- 7. long careers / 10-year club
    res["train_age_best_ge8_share"] = float((peak["train_age_best"] >= 8).mean())
    res["train_age_best_ge10_share"] = float((peak["train_age_best"] >= 10).mean())
    res["career_span_completed"] = med_iqr(peak["span_years"])

    # ------------------------------------------------- charts
    os.makedirs(CH, exist_ok=True)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for sex, col in [("M", NAVY), ("F", TEAL)]:
        sub = peak[peak["Sex"] == sex]
        ax[0].hist(sub["age_best"].clip(15, 75), bins=30, alpha=0.55,
                   color=col, label=f"{'Men' if sex == 'M' else 'Women'} (median {sub['age_best'].median():.0f})")
    ax[0].set_xlabel("Age at best total (years)")
    ax[0].set_ylabel("Lifters")
    ax[0].legend(frameon=False)
    ax[0].set_title("The familiar peak: age at best total")
    for sex, col in [("M", NAVY), ("F", TEAL)]:
        sub = peak[peak["Sex"] == sex]
        ax[1].hist(sub["train_age_best"].clip(0, 20), bins=30, alpha=0.55,
                   color=col, label=f"{'Men' if sex == 'M' else 'Women'} (median {sub['train_age_best'].median():.1f} y)")
    ax[1].set_xlabel("Years from first meet to best total")
    ax[1].set_ylabel("Lifters")
    ax[1].legend(frameon=False)
    ax[1].set_title("The hidden peak: training age at best total")
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "peak_age_vs_training_age.png"), bbox_inches="tight")
    plt.close(fig)

    # chart 2: the clock — age at best by starting cohort + regression
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    med = pd.DataFrame({c: {"start": by_cohort[c]["age_first"]["median"],
                            "best": by_cohort[c]["age_best"]["median"],
                            "n": by_cohort[c]["n"]} for c in COHORTS}).T
    ax[0].plot(med["start"], med["best"], "o-", color=RUST, lw=2, ms=9)
    for c in COHORTS:
        ax[0].annotate(f"{c}\n(n={int(med.loc[c, 'n']):,})",
                       (med.loc[c, "start"], med.loc[c, "best"]),
                       textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9)
    xs = np.linspace(15, 60, 10)
    ax[0].plot(xs, xs, "--", color=GREY, lw=1)
    ax[0].set_xlabel("Age at first meet (median, by starting cohort)")
    ax[0].set_ylabel("Age at best total (median)")
    ax[0].set_title("Start at 40, peak at 46 — the clock moves with you")
    ax[0].set_xlim(12, 62)
    ax[0].set_ylim(20, 60)
    sub = peak.copy()
    ax[1].hexbin(sub["age_first"], sub["age_best"], gridsize=30, cmap="Blues", mincnt=5)
    x = sub["age_first"].values
    ax[1].plot(xs, reg["all"]["slope"] * xs + reg["all"]["intercept"], color=RUST, lw=2,
               label=f"fit: slope {reg['all']['slope']:.2f}, r={reg['all']['r']:.2f}")
    ax[1].plot(xs, xs, "--", color=GREY, lw=1, label="slope 1 (pure training-age clock)")
    ax[1].set_xlabel("Age at first meet")
    ax[1].set_ylabel("Age at best total")
    ax[1].set_title(f"Every lifter (n={len(sub):,})")
    ax[1].legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "the_clock_moves_with_you.png"), bbox_inches="tight")
    plt.close(fig)

    # chart 3: gains curve
    fig, ax = plt.subplots(figsize=(9, 4.5))
    colors = {"<25": NAVY, "25-34": TEAL, "35-44": GOLD, "45+": RUST}
    for c in COHORTS:
        g = gains[gains["cohort"] == c]
        g = g[g["count"] >= 30]
        ax.plot(g["train_year_bin"], g["median"], "o-", color=colors[c], lw=2,
                label=f"started {c}")
    ax.axhline(100, color=GREY, lw=1, ls="--")
    ax.set_xlabel("Years since first meet")
    ax.set_ylabel("Median total, as % of that lifter's best")
    ax.set_title("The gains curve is the same shape at every starting age")
    ax.set_xlim(0, 10)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "gains_curve.png"), bbox_inches="tight")
    plt.close(fig)

    # chart 4: age curve raw vs matched
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bands = ["<25", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60+"]
    raw = np.array([res["age_curve_raw"].get(b, np.nan) for b in bands], dtype=float)
    mat = np.array([res["age_curve_matched_train_age_4_8"].get(b, np.nan) for b in bands], dtype=float)
    raw_n = 100 * raw / np.nanmax(raw)
    mat_n = 100 * mat / np.nanmax(mat)
    x = np.arange(len(bands))
    ax.plot(x[~np.isnan(raw_n)], raw_n[~np.isnan(raw_n)], "o-", color=NAVY, lw=2,
            label="All lifters (raw age curve)")
    ax.plot(x[~np.isnan(mat_n)], mat_n[~np.isnan(mat_n)], "s-", color=RUST, lw=2,
            label="Same training age (4–8 years in)")
    ax.set_xticks(x)
    ax.set_xticklabels(bands)
    ax.set_xlabel("Age at best total")
    ax.set_ylabel("Median best DOTS, indexed to peak band = 100")
    ax.set_title("Hold training age fixed and the age decline mostly disappears")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "age_curve_matched.png"), bbox_inches="tight")
    plt.close(fig)

    # chart 5: attrition + comebacks
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    dist = pd.Series(res["meets_per_lifter"])
    ax[0].bar(range(len(dist)), dist.values, color=NAVY)
    ax[0].set_xticks(range(len(dist)))
    ax[0].set_xticklabels(list(dist.index))
    ax[0].set_xlabel("Meets in a lifter's career")
    ax[0].set_ylabel("Lifters")
    ax[0].set_title(f"One meet and done: {100 * res['panel']['one_meet_share']:.0f}% never come back")
    ax[1].hist(regain.clip(0, 130), bins=26, color=TEAL, alpha=0.8)
    ax[1].axvline(100, color=RUST, lw=2, ls="--")
    ax[1].set_xlabel("Best total after return, as % of pre-gap best")
    ax[1].set_ylabel("Lifters who returned after a 3+ year gap")
    ax[1].set_title(f"Comebacks: median regain {regain.median():.0f}% (n={len(regain):,})")
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "attrition_and_comebacks.png"), bbox_inches="tight")
    plt.close(fig)

    with open(os.path.join(ROOT, "results.json"), "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps(res, indent=2)[:6000])
    return res


if __name__ == "__main__":
    main()
