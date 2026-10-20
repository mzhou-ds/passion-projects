"""What the between-person signal is actually made of.

PhenoAge's linear predictor xb is a sum of per-marker terms, so its variance
across people decomposes exactly: share_i = cov(term_i, xb) / var(xb).
Group the terms into what a clinician would call state (things that move
with this month's infection, iron status, or glucose control) versus the
slow background (age itself). This is the companion to noise.py: noise.py
asks how much of one person's number is weather; this asks how much of the
spread between people is weather too.
"""
import json
import os

import numpy as np
import pandas as pd

from phenoage import COEF

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "output")

GROUPS = {
    "age": "Chronological age (the anchor)",
    "glucose": "State: glucose control",
    "crp": "State: inflammation (CRP, WBC, lymphocyte %)",
    "wbc": "State: inflammation (CRP, WBC, lymphocyte %)",
    "lymph": "State: inflammation (CRP, WBC, lymphocyte %)",
    "rdw": "State: red-cell / iron status (RDW, MCV)",
    "mcv": "State: red-cell / iron status (RDW, MCV)",
    "albumin": "Slow background (albumin, creatinine, ALP)",
    "creatinine": "Slow background (albumin, creatinine, ALP)",
    "alp": "Slow background (albumin, creatinine, ALP)",
}


def main():
    df = pd.read_parquet(os.path.join(DATA, "nhanes_pheno.parquet"))
    terms = {
        "age": COEF["age"] * df["age"],
        "albumin": COEF["albumin"] * df["albumin"],
        "creatinine": COEF["creatinine"] * df["creatinine"],
        "glucose": COEF["glucose"] * df["glucose"],
        "crp": COEF["ln_crp"] * np.log(df["crp_mgdl"].clip(lower=0.01)),
        "lymph": COEF["lymph_pct"] * df["lymph_pct"],
        "mcv": COEF["mcv"] * df["mcv"],
        "rdw": COEF["rdw"] * df["rdw"],
        "alp": COEF["alp"] * df["alp"],
        "wbc": COEF["wbc"] * df["wbc"],
    }
    T = pd.DataFrame(terms)
    xb = T.sum(axis=1)
    var_xb = xb.var()
    per_marker = {m: float(np.cov(T[m], xb, ddof=1)[0, 1] / var_xb) for m in T}
    groups = {}
    for m, share in per_marker.items():
        groups[GROUPS[m]] = groups.get(GROUPS[m], 0.0) + share
    state_share = sum(v for k, v in groups.items() if k.startswith("State"))
    out = {
        "xb_variance_shares": dict(sorted(per_marker.items(),
                                          key=lambda kv: -kv[1])),
        "xb_group_shares": dict(sorted(groups.items(), key=lambda kv: -kv[1])),
        "state_share_of_xb_variance": float(state_share),
        "marker_accel_corr": {
            m: float(df[m2].corr(df["accel"]))
            for m, m2 in [("albumin", "albumin"), ("creatinine", "creatinine"),
                          ("glucose", "glucose"), ("crp", "crp_mgl"),
                          ("lymph_pct", "lymph_pct"), ("mcv", "mcv"),
                          ("rdw", "rdw"), ("alp", "alp"), ("wbc", "wbc")]},
    }
    rpath = os.path.join(OUT, "results.json")
    merged = json.load(open(rpath)) if os.path.exists(rpath) else {}
    merged["signal"] = out
    json.dump(merged, open(rpath, "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
