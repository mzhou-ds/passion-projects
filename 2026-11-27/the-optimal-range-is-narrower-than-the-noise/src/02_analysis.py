"""02_analysis.py — Can one blood draw place you in the "optimal" band?

For each marker in the longevity panel:
  * CVa (analytical) = 0.5 * CVi (Fraser's desirable imprecision).
  * CV_total = sqrt(CVi^2 + CVa^2): total noise on a single result.
  * RCV95 = 2.77 * CV_total: how far two serial results must differ to be a real change.
  * Index of individuality II = CVi / CVg (II < 0.6: population ranges are weak for you).
  * Noise-to-band ratio = CV_total / band half-width (two-sided) or / 20% margin (one-sided).
    Ratio > 1 means the noise on one draw is wider than the margin the verdict rests on.
  * Misclassification by Monte Carlo (lognormal, n=500k, fixed seed):
      - two-sided band: true value at the band's geometric midpoint -> P(measured outside band)
      - one-sided threshold: true value 20% below the threshold -> P(measured above threshold)
  * Repeats needed: smallest n so the mean of n draws is classified correctly with >=95%
    probability in the same scenario (analytic on the log scale, verified by simulation).
  * Coin-flip zone (one-sided): true values where P(correct) is 25-75%.

Also: vitamin D sensitivity case using the long-term CVi of 14.9% (PLCO, 5 years)
instead of the short-term EFLM meta value of 6.8%.
And the panel-level stat: P(at least one of the 14 misclassified) for a person who is
dead-center optimal on every marker (independence assumption, stated in README).

Outputs: output/results.json, output/results_table.csv, findings.txt
"""
import json
import math
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261127
N_SIM = 500_000
rng = np.random.default_rng(SEED)


def sigma_ln(cv_pct: float) -> float:
    """Lognormal sigma for a CV given in percent."""
    cv = cv_pct / 100.0
    return math.sqrt(math.log(1 + cv * cv))


def repeats_needed(sigma: float, log_margin: float, target: float = 0.95) -> int:
    """Smallest n so the mean of n draws lands inside the margin with prob >= target,
    for a true value at the centre of the margin (log scale)."""
    z = norm.ppf((1 + target) / 2)  # 1.96 for 95%
    n = math.ceil((z * sigma / log_margin) ** 2)
    return max(n, 1)


def simulate_misclass(sigma: float, true_val: float, lo, hi, n: int = N_SIM) -> float:
    draws = rng.lognormal(mean=math.log(true_val), sigma=sigma, size=n)
    outside = np.zeros(n, dtype=bool)
    if lo is not None:
        outside |= draws < lo
    if hi is not None:
        outside |= draws > hi
    return float(outside.mean())


def main():
    markers = pd.read_csv(ROOT / "data" / "markers.csv", comment="#")
    results = []
    for _, m in markers.iterrows():
        cvi = float(m["cvi_pct"])
        cvg = float(m["cvg_pct"])
        cva = 0.5 * cvi  # Fraser desirable imprecision
        cv_total = math.sqrt(cvi**2 + cva**2)
        rcv = 2.77 * cv_total
        ii = cvi / cvg
        sig = sigma_ln(cv_total)

        if m["opt_type"] == "range":
            lo, hi = float(m["opt_lo"]), float(m["opt_hi"])
            mid = math.sqrt(lo * hi)  # geometric midpoint
            half_width_pct = (math.sqrt(hi / lo) - 1) * 100  # half-width vs midpoint, %
            log_margin = math.log(hi / mid)
            true_val, scenario = mid, "true value at band midpoint"
            band_desc = f"{lo:g}-{hi:g} {m['unit']}"
        else:
            lo, hi = None, float(m["opt_hi"])
            true_val = 0.8 * hi
            half_width_pct = 20.0  # verdict margin: 20% below the threshold
            log_margin = math.log(1 / 0.8)
            scenario = "true value 20% below threshold"
            band_desc = f"<{hi:g} {m['unit']}"

        noise_to_band = cv_total / half_width_pct
        p_mis = simulate_misclass(sig, true_val, lo, hi)
        n_rep = repeats_needed(sig, log_margin)
        # verify the analytic repeats number by simulation for the same scenario
        p_rep = simulate_misclass(sig / math.sqrt(n_rep), true_val, lo, hi)

        # coin-flip zone (one-sided only): true values with P(correct) in [25%, 75%]
        if lo is None:
            z75 = norm.ppf(0.75)
            cf_lo = hi * math.exp(-z75 * sig)
            cf_hi = hi * math.exp(z75 * sig)
            coin_flip = f"{cf_lo:.2f}-{cf_hi:.2f} {m['unit']}"
        else:
            coin_flip = None

        results.append({
            "marker": m["marker"],
            "unit": m["unit"],
            "cvi_pct": cvi,
            "cvg_pct": cvg,
            "cvi_source": m["cvi_source"],
            "cva_pct": round(cva, 2),
            "cv_total_pct": round(cv_total, 2),
            "rcv95_pct": round(rcv, 1),
            "index_of_individuality": round(ii, 2),
            "lab_ref": (f"{m['lab_ref_lo']:g}-{m['lab_ref_hi']:g}" if pd.notna(m["lab_ref_lo"])
                        else f"<{m['lab_ref_hi']:g}"),
            "optimal_band": band_desc,
            "band_half_width_pct": round(half_width_pct, 1),
            "noise_to_band_ratio": round(noise_to_band, 2),
            "scenario": scenario,
            "p_misclassified_pct": round(100 * p_mis, 1),
            "repeats_needed_95pct": n_rep,
            "p_misclassified_with_repeats_pct": round(100 * p_rep, 1),
            "coin_flip_zone": coin_flip,
        })

    df = pd.DataFrame(results).sort_values("p_misclassified_pct", ascending=False)
    df.to_csv(ROOT / "output" / "results_table.csv", index=False)

    # --- vitamin D sensitivity: long-term CVi 14.9% (PLCO, 5 years) ---
    row = df[df["marker"] == "Vitamin D 25(OH)D"].iloc[0]
    cvi_lt = 14.9
    cvt_lt = math.sqrt(cvi_lt**2 + (0.5 * cvi_lt) ** 2)
    sig_lt = sigma_ln(cvt_lt)
    mid = math.sqrt(40 * 60)
    p_lt = simulate_misclass(sig_lt, mid, 40, 60)
    n_lt = repeats_needed(sig_lt, math.log(60 / mid))
    vitd_sensitivity = {
        "cvi_long_term_pct": cvi_lt,
        "cv_total_long_term_pct": round(cvt_lt, 2),
        "rcv95_long_term_pct": round(2.77 * cvt_lt, 1),
        "noise_to_band_ratio_long_term": round(cvt_lt / 20.0, 2),
        "p_misclassified_long_term_pct": round(100 * p_lt, 1),
        "repeats_needed_long_term": n_lt,
    }

    # --- panel-level stat ---
    p_all_ok = float(np.prod(1 - df["p_misclassified_pct"] / 100))
    panel = {
        "n_markers": len(df),
        "p_at_least_one_misclassified_pct": round(100 * (1 - p_all_ok), 1),
        "assumption": ("independent misclassification across markers; person dead-center "
                       "optimal on every marker (midpoint, or 20% below threshold)"),
    }

    summary = {
        "n_markers": len(df),
        "seed": SEED,
        "n_sim": N_SIM,
        "assumptions": {
            "cva": "desirable analytical imprecision = 0.5 * CVi (Fraser)",
            "distribution": "lognormal measurement error around the true value",
            "two_sided_scenario": "true value at the geometric midpoint of the optimal band",
            "one_sided_scenario": "true value 20% below the optimal threshold",
        },
        "vitamin_d_long_term_sensitivity": vitd_sensitivity,
        "panel": panel,
        "markers": df.to_dict("records"),
    }
    with open(ROOT / "output" / "results.json", "w") as f:
        json.dump(summary, f, indent=2)

    lines = ["KEY NUMBERS (see output/results.json for the full table)", ""]
    for _, r in df.iterrows():
        lines.append(
            f"{r['marker']:28s} CVi={r['cvi_pct']:5.1f}%  CVtot={r['cv_total_pct']:5.1f}%  "
            f"RCV={r['rcv95_pct']:5.1f}%  II={r['index_of_individuality']:.2f}  "
            f"noise/band={r['noise_to_band_ratio']:4.2f}  misclass={r['p_misclassified_pct']:4.1f}%  "
            f"repeats={r['repeats_needed_95pct']}"
        )
    lines += ["",
              f"Vitamin D long-term sensitivity: {vitd_sensitivity}",
              f"Panel: {panel}"]
    (ROOT / "findings.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
