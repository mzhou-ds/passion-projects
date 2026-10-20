"""Merge the two NHANES cycles, compute PhenoAge and age acceleration.

Age acceleration here is the standard residual definition: regress PhenoAge
on chronological age in the pooled sample (with a cycle indicator, because
assay calibration drifts between cycles) and keep the residual. A person's
acceleration is therefore 'years older or younger than the average person
their age in this sample', which is the number direct-to-consumer reports
sell as 'how much younger you are'.

Output: data/nhanes_pheno.parquet (derived analysis table, committed).
"""
import os

import numpy as np
import pandas as pd
import pyreadstat

from phenoage import phenoage

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
OUT = os.path.join(HERE, "..", "data", "nhanes_pheno.parquet")


def load(name):
    df, _ = pyreadstat.read_xport(os.path.join(RAW, name))
    return df


def cycle_frame(suffix, cycle_label):
    demo = load(f"DEMO_{suffix}.XPT")[["SEQN", "RIDAGEYR", "RIAGENDR"]]
    bio = load(f"BIOPRO_{suffix}.XPT")[["SEQN", "LBXSATSI", "LBXSAPSI", "LBXSCR"]]
    cbc = load(f"CBC_{suffix}.XPT")[["SEQN", "LBXWBCSI", "LBXLYPCT", "LBXMCVSI", "LBXRDW"]]
    crp = load(f"HSCRP_{suffix}.XPT")[["SEQN", "LBXHSCRP"]]
    glu = load(f"GLU_{suffix}.XPT")[["SEQN", "LBDGLUSI"]]
    df = (demo.merge(bio, on="SEQN").merge(cbc, on="SEQN")
              .merge(crp, on="SEQN").merge(glu, on="SEQN"))
    df["cycle"] = cycle_label
    return df


def main():
    df = pd.concat([cycle_frame("I", "2015-2016"),
                    cycle_frame("J", "2017-2018")], ignore_index=True)
    df = df.rename(columns={
        "RIDAGEYR": "age", "RIAGENDR": "sex",
        "LBXSATSI": "albumin",        # g/L
        "LBXSAPSI": "alp",            # U/L
        "LBXWBCSI": "wbc",            # 1000 cells/uL
        "LBXLYPCT": "lymph_pct",      # %
        "LBXMCVSI": "mcv",            # fL
        "LBXRDW": "rdw",              # %
        "LBXHSCRP": "crp_mgl",        # mg/L
        "LBDGLUSI": "glucose",        # mmol/L (fasting)
    })
    df["creatinine"] = df["LBXSCR"] * 88.4   # mg/dL -> umol/L
    df["crp_mgdl"] = df["crp_mgl"] / 10.0
    df = df.drop(columns=["LBXSCR"])
    n_all = len(df)
    df = df[(df["age"] >= 20)].dropna().reset_index(drop=True)
    df["phenoage"] = phenoage(df["albumin"], df["creatinine"], df["glucose"],
                              df["crp_mgdl"], df["lymph_pct"], df["mcv"],
                              df["rdw"], df["alp"], df["wbc"], df["age"])
    # residualised acceleration: PhenoAge ~ age + cycle
    X = np.column_stack([np.ones(len(df)), df["age"],
                         (df["cycle"] == "2017-2018").astype(float)])
    beta, *_ = np.linalg.lstsq(X, df["phenoage"], rcond=None)
    df["accel"] = df["phenoage"] - X @ beta
    df.attrs["regression_beta"] = beta.tolist()
    df.to_parquet(OUT, index=False)
    print(f"merged rows {n_all}; adults with all 9 labs (fasting): {len(df)}")
    print("by cycle:\n", df["cycle"].value_counts().to_string())
    print("PhenoAge~age+cycle coefficients:", np.round(beta, 4))
    print("corr(PhenoAge, age) =", round(df["phenoage"].corr(df["age"]), 3))
    print("raw PhenoAge - age: mean", round((df["phenoage"] - df["age"]).mean(), 2),
          "(level offset vs the 1988-94 training cohort; acceleration is "
          "residualised, so the offset does not affect any noise result)")
    print("accel describe:\n", df["accel"].describe().round(2).to_string())
    print("saved ->", OUT)


if __name__ == "__main__":
    main()
