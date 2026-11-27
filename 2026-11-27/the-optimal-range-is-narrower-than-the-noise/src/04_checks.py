"""04_checks.py — Sanity checks on the analysis outputs.

Checks:
  1. All 14 markers present, no NaNs, probabilities in [0, 100].
  2. RCV formula spot-check: RCV = 2.77 * sqrt(CVi^2 + (0.5*CVi)^2).
  3. Monotonicity: higher noise-to-band ratio -> higher misclassification (Spearman > 0.9).
  4. Repeats simulation check: with n repeats, simulated misclassification < 5%.
  5. Panel stat recomputed independently from the per-marker probabilities.
  6. hsCRP headline numbers recomputed analytically (normal approx on log scale).
"""
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import norm, spearmanr

BASE = Path(__file__).resolve().parent.parent
with open(BASE / "output" / "results.json") as f:
    R = json.load(f)
markers = R["markers"]
fails = []


def check(name, ok, detail=""):
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        fails.append(name)


check("14 markers", len(markers) == 14, f"got {len(markers)}")
check("no missing probabilities",
      all(0 <= m["p_misclassified_pct"] <= 100 for m in markers))
check("no missing RCV", all(m["rcv95_pct"] > 0 for m in markers))

# 2. RCV formula
bad = [m["marker"] for m in markers
       if abs(m["rcv95_pct"] - round(2.77 * math.sqrt(m["cvi_pct"]**2 + (0.5 * m["cvi_pct"])**2), 1)) > 0.05]
check("RCV formula", not bad, str(bad))

# 3. monotonicity
rho, _ = spearmanr([m["noise_to_band_ratio"] for m in markers],
                   [m["p_misclassified_pct"] for m in markers])
check("noise/band ratio tracks misclassification", rho > 0.9, f"Spearman rho={rho:.2f}")

# 4. repeats verification
bad = [m["marker"] for m in markers if m["p_misclassified_with_repeats_pct"] >= 5.0]
check("repeats give <5% misclassification", not bad, str(bad))

# 5. panel stat
p_ok = float(np.prod([1 - m["p_misclassified_pct"] / 100 for m in markers]))
panel = round(100 * (1 - p_ok), 1)
check("panel stat recomputes", panel == R["panel"]["p_at_least_one_misclassified_pct"],
      f"{panel} vs {R['panel']['p_at_least_one_misclassified_pct']}")

# 6. hsCRP analytic check (lognormal, true 0.4 vs threshold 0.5)
h = next(m for m in markers if m["marker"] == "hsCRP")
sig = math.sqrt(math.log(1 + (h["cv_total_pct"] / 100) ** 2))
p_analytic = 100 * (1 - norm.cdf(math.log(0.5 / 0.4) / sig))
check("hsCRP misclassification matches analytic value",
      abs(p_analytic - h["p_misclassified_pct"]) < 0.5,
      f"analytic {p_analytic:.1f}% vs simulated {h['p_misclassified_pct']}%")
check("hsCRP RCV > 100% (must more than double)",
      h["rcv95_pct"] > 100, f"RCV={h['rcv95_pct']}%")
check("hsCRP repeats = 28", h["repeats_needed_95pct"] == 28,
      f"got {h['repeats_needed_95pct']}")

print()
print("ALL CHECKS PASSED" if not fails else f"{len(fails)} CHECK(S) FAILED: {fails}")
raise SystemExit(1 if fails else 0)
