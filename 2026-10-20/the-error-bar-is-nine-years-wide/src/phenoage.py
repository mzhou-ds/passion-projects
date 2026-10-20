"""Levine et al. (2018) phenotypic age ('PhenoAge') from nine routine labs.

Coefficients are the published Gompertz proportional-hazards fit on
NHANES III. Inputs and units:
  albumin g/L, creatinine umol/L, glucose mmol/L, CRP mg/dL (log),
  lymphocyte %, MCV fL, RDW %, alkaline phosphatase U/L,
  WBC 1000 cells/uL, chronological age years.
"""
import numpy as np

COEF = {
    "intercept": -19.907,
    "albumin": -0.0336,
    "creatinine": 0.0095,
    "glucose": 0.1953,
    "ln_crp": 0.0954,
    "lymph_pct": -0.0120,
    "mcv": 0.0268,
    "rdw": 0.3306,
    "alp": 0.00188,
    "wbc": 0.0554,
    "age": 0.0804,
}
GAMMA = 0.0076927


def linear_predictor(albumin, creatinine, glucose, crp_mgdl, lymph_pct,
                     mcv, rdw, alp, wbc, age):
    return (COEF["intercept"]
            + COEF["albumin"] * albumin
            + COEF["creatinine"] * creatinine
            + COEF["glucose"] * glucose
            + COEF["ln_crp"] * np.log(np.clip(crp_mgdl, 0.01, None))
            + COEF["lymph_pct"] * lymph_pct
            + COEF["mcv"] * mcv
            + COEF["rdw"] * rdw
            + COEF["alp"] * alp
            + COEF["wbc"] * wbc
            + COEF["age"] * age)


def phenoage(albumin, creatinine, glucose, crp_mgdl, lymph_pct,
             mcv, rdw, alp, wbc, age):
    xb = linear_predictor(albumin, creatinine, glucose, crp_mgdl,
                          lymph_pct, mcv, rdw, alp, wbc, age)
    mort = 1.0 - np.exp(-np.exp(xb) * (np.exp(120 * GAMMA) - 1.0) / GAMMA)
    mort = np.clip(mort, 1e-6, 1 - 1e-6)
    return 141.50225 + np.log(-0.00553 * np.log(1.0 - mort)) / 0.090165
