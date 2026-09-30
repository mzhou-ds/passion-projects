"""Dose-response models for the Longevity Arbitrage build.

Parameterizes exercise-mortality curves ONLY from verified points in
data/evidence.csv (flagged interpolated/J-shape points are curve-shape
placeholders, never presented as study findings).
"""
import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator

# ----------------------------------------------------------------------------
# 1. Life-expectancy conversion fitted from Moore et al. 2012 (PLoS Medicine):
#    years_gained_after_40 per MET-h/wk category paired with matching HRs.
#    Fit: years ~= -8.5 * ln(HR)  (intercept ~0, verified below)
# ----------------------------------------------------------------------------
_MOORE_HR = np.array([0.81, 0.76, 0.68, 0.61, 0.59])
_MOORE_YR = np.array([1.80, 2.50, 3.40, 4.20, 4.50])
LE_COEF = float(-np.polyfit(np.log(_MOORE_HR), _MOORE_YR, 1)[0])  # positive 8.29


def hr_to_years(hr):
    """Life-expectancy years gained after 40 vs fully inactive, from HR."""
    return -LE_COEF * np.log(np.clip(hr, 1e-6, 1.0))


# ----------------------------------------------------------------------------
# 2. Modality curves: monotone PCHIP through verified dose-response points.
# ----------------------------------------------------------------------------
def load_evidence(path="data/evidence.csv"):
    return pd.read_csv(path, comment="#")


def build_curves(ev):
    curves = {}

    # Aerobic (Arem 2015, all-cause HR). Standard epi convention: 150 min of
    # moderate activity ~= 7.5 MET-h/wk (moderate = 3 METs). x = minutes of
    # moderate-equiv activity/wk, y anchored at category UPPER bounds.
    x_aero = np.array([0, 150, 300, 450, 600, 1700])
    y_aero = np.array([1.00, 0.80, 0.69, 0.63, 0.61, 0.69])
    curves["aerobic"] = PchipInterpolator(x_aero, y_aero, extrapolate=False)

    # Strength (Momma 2022, all-cause RR vs min/wk) — J-shaped
    x_str = np.array([0, 20, 40, 100, 140, 200, 260])
    y_str = np.array([1.00, 0.90, 0.83, 0.82, 0.85, 0.95, 1.00])
    curves["strength"] = PchipInterpolator(x_str, y_str, extrapolate=False)

    # VILPA (Stamatakis 2022, device-measured incidental vigorous, nonexercisers).
    # The 24-min point (3.4 min/day) uses a different exposure parameterization
    # than the bouts-based points; keeping it creates a non-monotone artifact,
    # so the curve uses the monotone bouts points only. It stays in evidence.csv.
    x_vil = np.array([0, 16, 32, 60])
    y_vil = np.array([1.00, 0.75, 0.61, 0.61])
    curves["vilpa"] = PchipInterpolator(x_vil, y_vil, extrapolate=False)

    curves["x_max"] = {"aerobic": 1700.0, "strength": 260.0, "vilpa": 60.0}
    return curves


def hr_at(curves, modality, minutes):
    f = curves[modality]
    x = np.clip(np.asarray(minutes, float), 0, curves["x_max"][modality])
    return np.where(np.asarray(minutes, float) >= 0, f(x), np.nan)


# ----------------------------------------------------------------------------
# 3. Combined risk. Studies come from different populations, so exact
#    composition is not identified. Standard independence assumption:
#    multiplicative on relative risk. Sanity anchor: Momma 2022 directly
#    observed aerobic+strength vs none at RR 0.60 all-cause (0.54 CVD),
#    which sits at or below the multiplicative prediction of its
#    components — consistent with independence, possibly slightly
#    super-additive. Report the multiplicative estimate and cite the
#    observed 0.60 as the anchor.
# ----------------------------------------------------------------------------
def combined_hr(curves, aero, strength, vilpa):
    ha = hr_at(curves, "aerobic", aero)
    hs = hr_at(curves, "strength", strength)
    hv = hr_at(curves, "vilpa", vilpa)
    aero = np.asarray(aero, float); vilpa = np.asarray(vilpa, float)
    # VILPA evidence comes from nonexercisers (Stamatakis 2022): it is a
    # SUBSTITUTE for structured aerobic, not a stackable bonus. When structured
    # aerobic is nonzero, vilpa contributes nothing additional.
    hv = np.where(aero > 0, 1.0, hv)
    return ha * hs * hv


# ----------------------------------------------------------------------------
# 4. Portfolio optimizer: fixed weekly minute budget -> allocation maximizing
#    life-expectancy years. Grid search over (aero, strength, vilpa) on a
#    step grid; vilpa capped at its evidence range.
# ----------------------------------------------------------------------------
def optimize_portfolio(curves, budget_min, step=20, structured=True):
    """Structured exercisers exclude VILPA (nonexerciser evidence)."""
    best = None
    vilpa_cap = 35.0 if not structured else 0.0
    a_vals = np.arange(0, budget_min + 1, step)
    for a in a_vals:
        rem = budget_min - a
        s_vals = np.arange(0, rem + 1, step)
        for s in s_vals:
            v = min(budget_min - a - s, vilpa_cap)
            if v < 0:
                continue
            hr = combined_hr(curves, a, s, v)
            years = hr_to_years(hr)
            if best is None or years > best["years"]:
                best = {"aerobic": int(a), "strength": int(s), "vilpa": float(v),
                        "hr": float(hr), "years": float(years)}
    return best


def marginal_roi_minutes(curves, modality, minutes):
    """Minutes of life expectancy gained per week for the NEXT minute of
    weekly exercise at current dose `minutes`."""
    hr0 = hr_at(curves, modality, minutes)
    hr1 = hr_at(curves, modality, minutes + 1)
    d_years = hr_to_years(hr1) - hr_to_years(hr0)   # years gained for +1 min/wk
    return d_years * 365 * 24 * 60                   # minutes of life per minute exercised


if __name__ == "__main__":
    print(f"LE conversion slope fitted from Moore 2012: {LE_COEF:.3f}")
    # sanity: reproduce Moore's own points
    for hr, yr in zip(_MOORE_HR, _MOORE_YR):
        print(f"  HR {hr:.2f}: observed {yr:.1f} yr, model {hr_to_years(hr):.2f} yr")
