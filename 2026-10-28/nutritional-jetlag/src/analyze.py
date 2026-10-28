"""Core analysis: how far does one person's eating clock move between two
ordinary days, what moves it, and what rides along with the move?

All headline stats use the two-day dietary weights (WTDR2D). Differencing
(day2 - day1) is the within-person design: every person is their own control.
"""
import json
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
rng = np.random.default_rng(52)


def wq(x, w, q):
    """Weighted quantile(s)."""
    o = np.argsort(x)
    x, w = np.asarray(x)[o], np.asarray(w)[o]
    cw = np.cumsum(w) - 0.5 * w
    cw /= np.sum(w)
    return np.interp(q, cw, x)


def wmean(x, w):
    return float(np.average(x, weights=w))


def boot_wmedian(df, col, n=400):
    vals = []
    a = df[col].to_numpy()
    w = df["WTDR2D"].to_numpy()
    for _ in range(n):
        idx = rng.integers(0, len(df), len(df))
        vals.append(wq(a[idx], w[idx], [0.5])[0])
    return float(np.std(vals))


def icc_two(df, col):
    """One-way random-effects ICC from exactly two measures per person,
    plus within/between SD split (unweighted, standard ANOVA form)."""
    x1, x2 = df[f"{col}_1"].to_numpy(), df[f"{col}_2"].to_numpy()
    m = (x1 + x2) / 2
    grand = m.mean()
    msb = 2 * np.sum((m - grand) ** 2) / (len(df) - 1)
    msw = np.sum((x1 - m) ** 2 + (x2 - m) ** 2) / len(df)
    icc = (msb - msw) / (msb + msw)
    within_sd = np.sqrt(msw)
    between_sd = np.sqrt(max((msb - msw) / 2, 0))
    return {"icc": float(icc), "within_sd_h": float(within_sd),
            "between_sd_h": float(between_sd),
            "reliability_2day_avg": float(2 * icc / (1 + icc))}


def main():
    pairs = pd.read_parquet(os.path.join(ROOT, "data", "person_pairs.parquet"))
    w = pairs["WTDR2D"]
    R = {"n_pairs": int(len(pairs)),
         "cycles": sorted(pairs["cycle"].unique().tolist())}

    clocks = ["first", "mid", "last", "window"]
    shift = {}
    for c in clocks:
        d = (pairs[f"{c}_h_2"] - pairs[f"{c}_h_1"]).abs()
        pairs[f"abs_shift_{c}"] = d
        pairs[f"d_{c}"] = pairs[f"{c}_h_2"] - pairs[f"{c}_h_1"]
        shift[c] = {
            "median_abs_h": float(wq(d, w, [0.5])[0]),
            "q25_abs_h": float(wq(d, w, [0.25])[0]),
            "q75_abs_h": float(wq(d, w, [0.75])[0]),
            "mean_abs_h": wmean(d, w),
            "share_gt1h": float(np.average(d > 1, weights=w)),
            "share_gt2h": float(np.average(d > 2, weights=w)),
            "share_gt3h": float(np.average(d > 3, weights=w)),
            "se_median": boot_wmedian(pairs.assign(_d=d), "_d", n=200),
        }
    R["shift"] = shift

    R["icc"] = {c: icc_two(pairs, f"{c}_h") for c in clocks}
    R["icc"]["kcal"] = icc_two(pairs, "kcal")
    R["icc"]["after20"] = icc_two(pairs, "after20")

    # typical levels (average of the two days, weighted)
    R["levels"] = {c: {"median_day": float(wq(
        pd.concat([pairs[f"{c}_h_1"], pairs[f"{c}_h_2"]]),
        pd.concat([w, w]), [0.5])[0])} for c in clocks}
    R["levels"]["kcal_mean"] = wmean((pairs["kcal_1"] + pairs["kcal_2"]) / 2, w)

    # which end moves? correlation of signed shifts + stretch vs slide
    R["ends"] = {
        "corr_first_last_shift": float(np.corrcoef(pairs["d_first"], pairs["d_last"])[0, 1]),
        "share_same_direction": float(np.average(np.sign(pairs["d_first"]) == np.sign(pairs["d_last"]), weights=w)),
        "median_abs_window_change_h": shift["window"]["median_abs_h"],
    }

    # day-pair type: the calendar component
    pt = {}
    for name, sub in pairs.groupby("pair_type"):
        pt[name] = {"n": int(len(sub)),
                    "share": float(np.average(pairs["pair_type"] == name, weights=w)),
                    "median_abs_mid_shift_h": float(wq(sub["abs_shift_mid"], sub["WTDR2D"], [0.5])[0]),
                    "median_abs_last_shift_h": float(wq(sub["abs_shift_last"], sub["WTDR2D"], [0.5])[0]),
                    "median_abs_first_shift_h": float(wq(sub["abs_shift_first"], sub["WTDR2D"], [0.5])[0])}
    R["pair_type"] = pt

    # in mixed pairs, is the weekend day the later / longer one?
    mix = pairs[pairs["pair_type"] == "mixed"].copy()
    wk_is_2 = mix["weekend_2"] == 1
    d_mid_wk = np.where(wk_is_2, mix["d_mid"], -mix["d_mid"])
    d_kcal_wk = np.where(wk_is_2, mix["kcal_2"] - mix["kcal_1"], mix["kcal_1"] - mix["kcal_2"])
    d_last_wk = np.where(wk_is_2, mix["d_last"], -mix["d_last"])
    R["weekend_day_effect"] = {
        "mid_later_h": wmean(d_mid_wk, mix["WTDR2D"]),
        "last_later_h": wmean(d_last_wk, mix["WTDR2D"]),
        "kcal_diff": wmean(d_kcal_wk, mix["WTDR2D"]),
    }

    # segments
    seg = {}
    for col, label in [("age_band", "age"), ("RIAGENDR", "sex"), ("RIDRETH1", "race"),
                       ("cycle", "cycle")]:
        tab = {}
        for name, sub in pairs.groupby(col, observed=True):
            if len(sub) < 100:
                continue
            tab[str(name)] = {"n": int(len(sub)),
                              "median_abs_mid_shift_h": float(wq(sub["abs_shift_mid"], sub["WTDR2D"], [0.5])[0]),
                              "median_abs_last_shift_h": float(wq(sub["abs_shift_last"], sub["WTDR2D"], [0.5])[0]),
                              "share_gt2h_mid": float(np.average(sub["abs_shift_mid"] > 2, weights=sub["WTDR2D"]))}
        seg[label] = tab
    R["segments"] = seg

    # within-person intake link: differenced regression (person fixed effects)
    import statsmodels.api as sm
    d = pd.DataFrame({
        "d_kcal": pairs["kcal_2"] - pairs["kcal_1"],
        "d_mid": pairs["d_mid"], "d_last": pairs["d_last"],
        "d_first": pairs["d_first"], "d_window": pairs["d_window"],
        "d_after20": pairs["after20_2"] - pairs["after20_1"],
        "mixed": (pairs["pair_type"] == "mixed").astype(int),
    })
    X = sm.add_constant(d[["d_mid", "d_window"]])
    fit = sm.WLS(d["d_kcal"], X, weights=w).fit(cov_type="HC1")
    R["intake_link"] = {
        "kcal_per_hour_later_midpoint": float(fit.params["d_mid"]),
        "se_midpoint": float(fit.bse["d_mid"]),
        "kcal_per_hour_wider_window": float(fit.params["d_window"]),
        "se_window": float(fit.bse["d_window"]),
        "r2": float(fit.rsquared),
    }
    X2 = sm.add_constant(d[["d_after20"]])
    fit2 = sm.WLS(d["d_kcal"], X2, weights=w).fit(cov_type="HC1")
    R["intake_link"]["kcal_per_10pp_after20"] = float(fit2.params["d_after20"] * 0.10)
    R["intake_link"]["se_after20_10pp"] = float(fit2.bse["d_after20"] * 0.10)

    # binned: mean delta kcal by delta midpoint bins (chart + explorer)
    bins = pd.cut(d["d_mid"], [-8, -2, -1, -0.5, 0.5, 1, 2, 8])
    binned = (d.assign(bin=bins).groupby("bin", observed=True)
                .apply(lambda s: pd.Series({
                    "n": len(s),
                    "d_kcal_mean": np.average(s["d_kcal"], weights=w.loc[s.index])}),
                    include_groups=False).reset_index())
    binned["bin"] = binned["bin"].astype(str)
    binned.to_csv(os.path.join(ROOT, "output", "delta_bins.csv"), index=False)
    R["delta_bins"] = binned.to_dict("records")

    # stranger comparison + slide-vs-stretch, among people whose ends both moved
    m1 = pairs["mid_h_1"].to_numpy()
    ii = rng.integers(0, len(pairs), 200_000)
    jj = rng.integers(0, len(pairs), 200_000)
    keep = ii != jj
    pm_mean = (pairs["mid_h_1"] + pairs["mid_h_2"]) / 2
    iqr_between = float(pm_mean.quantile(0.75) - pm_mean.quantile(0.25))
    movers = pairs[(pairs["d_first"] != 0) & (pairs["d_last"] != 0)]
    R["stranger"] = {
        "stranger_mean_abs_mid_gap_h": float(np.abs(m1[ii[keep]] - m1[jj[keep]]).mean()),
        "own_mean_abs_mid_shift_h": shift["mid"]["mean_abs_h"],
        "own_as_share_of_stranger_gap": float(shift["mid"]["mean_abs_h"] /
                                              np.abs(m1[ii[keep]] - m1[jj[keep]]).mean()),
        "between_person_iqr_mid_h": iqr_between,
        "share_own_shift_exceeds_between_iqr": float(
            np.average(pairs["abs_shift_mid"] > iqr_between, weights=w)),
        "same_direction_share_movers": float(np.average(
            np.sign(movers["d_first"]) == np.sign(movers["d_last"]),
            weights=movers["WTDR2D"])),
        "mean_d_kcal_day2_minus_day1": wmean(pairs["kcal_2"] - pairs["kcal_1"], w),
    }
    # center the binned intake link on the average day-pair change
    binned["d_kcal_rel"] = binned["d_kcal_mean"] - R["stranger"]["mean_d_kcal_day2_minus_day1"]
    binned.to_csv(os.path.join(ROOT, "output", "delta_bins.csv"), index=False)
    R["delta_bins"] = binned.to_dict("records")

    # the unnamed fourth meal: evening snack calories
    for day in (1, 2):
        pairs[f"snack_pm_{day}_share"] = pairs[f"snack_pm_kcal_{day}"] / pairs[f"kcal_{day}"]
    all_days = pd.concat([
        pairs[["snack_pm_kcal_1", "kcal_1", "after20_1", "dinner_kcal_1", "WTDR2D"]]
        .rename(columns=lambda c: c.replace("_1", "")),
        pairs[["snack_pm_kcal_2", "kcal_2", "after20_2", "dinner_kcal_2", "WTDR2D"]]
        .rename(columns=lambda c: c.replace("_2", ""))])
    R["fourth_meal"] = {
        "share_days_snack_pm_ge300": float(np.average(all_days["snack_pm_kcal"] >= 300, weights=all_days["WTDR2D"])),
        "share_days_any_snack_pm": float(np.average(all_days["snack_pm_kcal"] > 0, weights=all_days["WTDR2D"])),
        "median_snack_pm_when_present": float(wq(all_days.loc[all_days["snack_pm_kcal"] > 0, "snack_pm_kcal"],
                                                 all_days.loc[all_days["snack_pm_kcal"] > 0, "WTDR2D"], [0.5])[0]),
        "snack_share_of_after20_kcal": float(
            np.average(all_days["snack_pm_kcal"], weights=all_days["WTDR2D"]) /
            np.average(all_days["after20"] * all_days["kcal"], weights=all_days["WTDR2D"])),
    }

    pairs.to_parquet(os.path.join(ROOT, "data", "pairs_enriched.parquet"), index=False)
    with open(os.path.join(ROOT, "output", "results.json"), "w") as f:
        json.dump(R, f, indent=1)
    print(json.dumps(R, indent=1)[:6000])


if __name__ == "__main__":
    main()
