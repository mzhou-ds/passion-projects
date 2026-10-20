"""The noise budget of a single PhenoAge reading.

Idea: a blood panel is one draw from a distribution. Every analyte in the
panel has a published within-person biological variation (CVi, EFLM
Biological Variation Database) plus analytical imprecision (CVa). Perturb
each person's nine labs with lognormal noise at total CV = sqrt(CVi^2+CVa^2),
recompute PhenoAge many times, and measure:

  1. the per-person 95% interval width of the reading (the error bar a
     direct-to-consumer report does not print);
  2. which analyte's ordinary wobble contributes that width (one-at-a-time);
  3. what a pure retest looks like with zero true change: how many people
     'rejuvenate' by 2+ years, and how much the highest first readings fall
     on the second draw (regression to the mean, the engine of uncontrolled
     before/after claims);
  4. label instability: how often an 'accelerated ager' label survives a
     retest;
  5. how many repeat panels, averaged, it takes to earn a given error bar;
  6. sensitivity: halve every CVi, and double the CRP CVi, and re-run.

Outputs output/results.json (noise sections) and
output/noise_by_person.csv (per-person interval widths for the analysis
sample).
"""
import json
import os

import numpy as np
import pandas as pd

from phenoage import phenoage

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "output")
MARKERS = ["albumin", "creatinine", "glucose", "crp_mgdl", "lymph_pct",
           "mcv", "rdw", "alp", "wbc"]
RNG = np.random.default_rng(20261020)


def sigma_from_cv(cv_pct):
    cv = cv_pct / 100.0
    return np.sqrt(np.log1p(cv ** 2))


def draw(values, sigma, n_sim, rng):
    """Lognormal draws around each person's observed value."""
    return rng.lognormal(mean=np.log(np.clip(values, 1e-6, None)),
                         sigma=sigma, size=(n_sim, len(values)))


def simulate(df, cv_map, n_sim, rng, vary=None):
    """Return (n_sim, n_people) PhenoAge draws. vary=None varies all markers."""
    cols = {}
    for m in MARKERS:
        if vary is None or m in vary:
            cols[m] = draw(df[m].to_numpy(float), sigma_from_cv(cv_map[m]),
                           n_sim, rng)
        else:
            cols[m] = np.tile(df[m].to_numpy(float), (n_sim, 1))
    lymph = np.clip(cols["lymph_pct"], 1.0, 95.0)
    return phenoage(cols["albumin"], cols["creatinine"], cols["glucose"],
                    cols["crp_mgdl"], lymph, cols["mcv"], cols["rdw"],
                    cols["alp"], cols["wbc"],
                    np.tile(df["age"].to_numpy(float), (n_sim, 1)))


def main():
    df = pd.read_parquet(os.path.join(DATA, "nhanes_pheno.parquet"))
    cvtab = pd.read_csv(os.path.join(DATA, "cvi_cva.csv"))
    cvtab["total_cv_pct"] = np.sqrt(cvtab["cvi_pct"] ** 2 + cvtab["cva_pct"] ** 2)
    cv_map = dict(zip(cvtab["marker"], cvtab["total_cv_pct"]))
    labels = dict(zip(cvtab["marker"], cvtab["label"]))

    sample = df.sample(n=min(2000, len(df)), random_state=7).reset_index(drop=True)

    # ---- 1. joint noise: per-person interval -------------------------------
    sims = simulate(sample, cv_map, n_sim=600, rng=RNG)
    lo, hi = np.percentile(sims, [2.5, 97.5], axis=0)
    width = hi - lo
    sd = sims.std(axis=0)
    noise_df = pd.DataFrame({
        "age": sample["age"], "phenoage": sample["phenoage"],
        "accel": sample["accel"], "noise_sd": sd, "width95": width,
        "lo95": lo, "hi95": hi})
    noise_df.to_csv(os.path.join(OUT, "noise_by_person.csv"), index=False)

    # ---- 3/4. two independent draws = a retest with zero true change -------
    d1, d2 = sims[0], sims[1]
    base = sample["phenoage"].to_numpy()
    a1, a2 = d1 - base + sample["accel"].to_numpy(), d2 - base + sample["accel"].to_numpy()
    change = a2 - a1  # change in measured acceleration, truth fixed at accel
    q75 = np.quantile(sample["accel"], 0.75)
    top_q_1 = a1 >= np.quantile(a1, 0.75)
    retest = {
        "share_improve_2y": float((change <= -2).mean()),
        "share_worsen_2y": float((change >= 2).mean()),
        "share_abs_change_ge2y": float((np.abs(change) >= 2).mean()),
        "mean_change_top_quartile_baseline": float(change[a1 >= np.quantile(a1, 0.75)].mean()),
        "mean_change_top_decile_baseline": float(change[a1 >= np.quantile(a1, 0.90)].mean()),
        "mean_change_bottom_quartile_baseline": float(change[a1 <= np.quantile(a1, 0.25)].mean()),
        "corr_baseline_vs_change": float(np.corrcoef(a1, change)[0, 1]),
        "top_quartile_label_survival": float((a2[top_q_1] >= q75).mean()),
        "accel_rank_corr_retest": float(np.corrcoef(a1, a2)[0, 1]),
    }

    # how many people's band is so wide it cannot separate them from average
    share_band_covers_zero = float((np.abs(sample["accel"].to_numpy())
                                    <= width / 2).mean())

    # regression to the mean inside a consumer-like band: people whose true
    # acceleration sits within +/-10 y (the mostly-healthy buyers of these
    # tests), where the true spread is narrower and noise bites harder
    in_band = np.abs(sample["accel"].to_numpy()) <= 10
    a1b, a2b, chb = a1[in_band], a2[in_band], change[in_band]
    retest_band = {
        "n": int(in_band.sum()),
        "mean_change_top_quartile_baseline": float(
            chb[a1b >= np.quantile(a1b, 0.75)].mean()),
        "mean_change_top_decile_baseline": float(
            chb[a1b >= np.quantile(a1b, 0.90)].mean()),
        "mean_change_bottom_quartile_baseline": float(
            chb[a1b <= np.quantile(a1b, 0.25)].mean()),
        "share_improve_2y": float((chb <= -2).mean()),
    }

    # ---- 5. repeat panels needed -------------------------------------------
    median_width = float(np.median(width))
    repeats = {f"width_le_{t}y": int(np.ceil((median_width / t) ** 2))
               for t in (4, 2, 1)}

    # ---- 2. one-at-a-time decomposition (subsample) ------------------------
    sub = sample.sample(n=400, random_state=11).reset_index(drop=True)
    oat_var, loo_var = {}, {}
    for m in MARKERS:
        s_only = simulate(sub, cv_map, n_sim=500, rng=RNG, vary={m})
        oat_var[m] = float(np.median(s_only.var(axis=0)))
        s_rest = simulate(sub, cv_map, n_sim=500, rng=RNG,
                          vary=set(MARKERS) - {m})
        loo_var[m] = float(np.median(s_rest.var(axis=0)))
    full_sub = simulate(sub, cv_map, n_sim=500, rng=RNG)
    total_var = float(np.median(full_sub.var(axis=0)))
    oat_share = {m: v / sum(oat_var.values()) for m, v in oat_var.items()}
    loo_share = {}
    loo_contrib = {m: total_var - v for m, v in loo_var.items()}
    loo_total = sum(max(v, 0.0) for v in loo_contrib.values())
    for m in MARKERS:
        loo_share[m] = max(loo_contrib[m], 0.0) / loo_total if loo_total > 0 else 0.0
    decomposition = [{
        "marker": m, "label": labels[m], "total_cv_pct": float(cv_map[m]),
        "oat_var": oat_var[m], "oat_share": float(oat_share[m]),
        "loo_share": float(loo_share[m]),
    } for m in sorted(MARKERS, key=lambda m: -oat_share[m])]

    # ---- 6. sensitivity ------------------------------------------------------
    def width_for(cv_scale=None, marker_scale=None):
        cm = dict(cv_map)
        if cv_scale:
            cm = {k: v * cv_scale for k, v in cm.items()}
        if marker_scale:
            for k, f in marker_scale.items():
                cm[k] = cm[k] * f
        s = simulate(sample.sample(n=600, random_state=3).reset_index(drop=True),
                     cm, n_sim=400, rng=RNG)
        w = np.percentile(s, 97.5, axis=0) - np.percentile(s, 2.5, axis=0)
        return float(np.median(w))

    sensitivity = {
        "base_median_width": median_width,
        "half_all_cvi_width": width_for(cv_scale=0.5),
        "double_crp_width": width_for(marker_scale={"crp_mgdl": 2.0}),
        "half_rdw_width": width_for(marker_scale={"rdw": 0.5}),
    }

    results = {
        "n_population": int(len(df)),
        "n_noise_sample": int(len(sample)),
        "noise": {
            "median_sd_years": float(np.median(sd)),
            "median_width95_years": median_width,
            "width95_iqr": [float(np.percentile(width, 25)),
                            float(np.percentile(width, 75))],
            "share_width_gt4y": float((width > 4).mean()),
            "share_width_gt6y": float((width > 6).mean()),
            "share_width_gt8y": float((width > 8).mean()),
            "share_band_covers_zero_accel": share_band_covers_zero,
        },
        "decomposition": decomposition,
        "retest": retest,
        "retest_consumer_band": retest_band,
        "repeats_needed": repeats,
        "sensitivity": sensitivity,
    }
    rpath = os.path.join(OUT, "results.json")
    merged = {}
    if os.path.exists(rpath):
        merged = json.load(open(rpath))
    merged.update(results)
    json.dump(merged, open(rpath, "w"), indent=2)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
