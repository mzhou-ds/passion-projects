#!/usr/bin/env python3
"""02_hedonic.py — OLS hedonic pricing of developer labor.

log(comp) = f(experience, country, role, languages, remote, AI usage,
education, org size, industry, manager) + e

Premiums are reported as exp(coef)-1: the percentage pay difference of an
attribute vs its reference category, holding everything else constant.
"""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

REF = {"remote_simple": "In-person", "ai_freq": "no_never",
       "Ed_simple": "bachelors", "Country_top30": "United States of America",
       "Org_simple": "20-99", "Age": "25-34 years old"}

CATS = ["remote_simple", "ai_freq", "Ed_simple", "Country_top30", "Org_simple", "Age"]

def main():
    d = pd.read_csv("data/sample.csv")
    X_parts, names = [], []

    for cat in CATS:
        vals = sorted(v for v in d[cat].dropna().unique() if v != REF.get(cat))
        for v in vals:
            X_parts.append((d[cat] == v).astype(float).values)
            names.append(f"{cat}={v}")

    # industry top-10 dummies
    top_ind = d["Industry"].value_counts().head(10).index
    for ind in top_ind:
        if ind == "Other:" or pd.isna(ind):
            continue
        X_parts.append((d["Industry"] == ind).astype(float).values)
        names.append(f"Industry={ind[:28]}")

    role_cols = [c for c in d.columns if c.startswith("role_")]
    lang_cols = [c for c in d.columns if c.startswith("lang_")]
    for c in role_cols + lang_cols:
        X_parts.append(d[c].astype(float).values)
        names.append(c)
    X_parts.append(d["manager"].astype(float).values); names.append("manager")

    # experience linear + quadratic
    w = d["WorkExpY"].values
    X_parts += [w, w ** 2]; names += ["exp", "exp2"]

    X = np.column_stack(X_parts)
    y = d["log_comp"].values
    m = LinearRegression().fit(X, y)
    r2 = m.score(X, y)
    print(f"OLS hedonic R^2 = {r2:.3f}  (n={len(d)}, k={X.shape[1]})")

    coef = dict(zip(names, m.coef_))
    prem = {k: float(np.exp(v) - 1) for k, v in coef.items()}
    with open("data/hedonic_premiums.json", "w") as f:
        json.dump({"r2": r2, "n": len(d), "premiums": prem,
                   "reference": REF, "intercept_comp": float(np.exp(m.intercept_))}, f, indent=1)

    # console summary of the juiciest bits
    def show(title, prefix, topn=8):
        rows = sorted(((k, v) for k, v in prem.items() if k.startswith(prefix)),
                      key=lambda x: x[1], reverse=True)
        print(f"\n== {title} (vs {REF.get(prefix.split('=')[0], 'ref')}) ==")
        for k, v in rows[:topn] + rows[-3:]:
            print(f"  {k:55s} {v:+.1%}")

    show("REMOTE", "remote_simple")
    show("AI USAGE", "ai_freq")
    show("EDUCATION", "Ed_simple")
    show("ORG SIZE", "Org_simple")
    show("COUNTRY (geo discount vs US)", "Country_top30")
    show("AGE", "Age")

    rows = sorted(((k, v) for k, v in prem.items() if k.startswith("lang_")),
                  key=lambda x: x[1], reverse=True)
    print("\n== LANGUAGE premiums (having worked with, additive) ==")
    for k, v in rows[:10] + rows[-4:]:
        print(f"  {k:45s} {v:+.1%}")
    rows = sorted(((k, v) for k, v in prem.items() if k.startswith("role_")),
                  key=lambda x: x[1], reverse=True)
    print("\n== ROLE premiums ==")
    for k, v in rows[:10] + rows[-3:]:
        print(f"  {k:45s} {v:+.1%}")
    rows = sorted(((k, v) for k, v in prem.items() if k.startswith("Industry=")),
                  key=lambda x: x[1], reverse=True)
    print("\n== INDUSTRY premiums ==")
    for k, v in rows:
        print(f"  {k:45s} {v:+.1%}")
    print(f"\n  manager                        {prem['manager']:+.1%}")
    print(f"  +1yr experience (at 8yr)       {np.exp(coef['exp'] + 2*coef['exp2']*8) - 1:+.1%}")

if __name__ == "__main__":
    main()
