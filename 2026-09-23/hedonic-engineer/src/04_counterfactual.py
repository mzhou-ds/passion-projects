#!/usr/bin/env python3
"""04_counterfactual.py — what-if pricing with the hedonic model.

1. Reference-profile arbitrage: same engineer, 30 countries -> predicted comp.
2. Robustness check: remote premium re-estimated within US respondents only.
3. Charts: geo arbitrage + US-only remote check.
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression

PROFILE = {  # reference engineer
    "WorkExpY": 8, "role_developer_back_end": 1, "lang_Python": 1,
    "remote_simple": "Hybrid", "ai_freq": "weekly", "Ed_simple": "bachelors",
    "Org_simple": "20-99", "Industry": "Software Development",
    "Age": "25-34 years old", "manager": 0,
}

def main():
    with open("data/hedonic_premiums.json") as f:
        H = json.load(f)
    prem = H["premiums"]
    base = np.log(H["intercept_comp"])

    # profile log-comp at reference categories (all dummies = 0, exp set below)
    prof = base + prem["exp"] * 8 + prem["exp2"] * 64 \
        + prem["role_developer_back_end"] + prem["lang_Python"] \
        + prem["remote_simple=Hybrid"] + prem["ai_freq=weekly"] \
        + prem["Industry=Software Development"]

    countries = sorted({k.split("=", 1)[1] for k in prem if k.startswith("Country_top30=")}
                       | {"United States of America"})
    rows = []
    for c in countries:
        lp = prof + (prem.get(f"Country_top30={c}", 0.0) if c != "United States of America" else 0.0)
        rows.append((c, np.exp(lp)))
    arb = pd.DataFrame(rows, columns=["country", "predicted_comp"]).sort_values("predicted_comp", ascending=False)
    arb.to_csv("data/geo_arbitrage.csv", index=False)
    short = arb["country"].str.replace("United States of America", "USA") \
        .str.replace("United Kingdom of Great Britain and Northern Ireland", "UK")
    print(arb.to_string(index=False))

    fig, ax = plt.subplots(figsize=(9, 10))
    ax.barh(short[::-1], arb["predicted_comp"][::-1], color="#2f6fde")
    ax.set_xlabel("predicted annual comp, USD")
    ax.set_title("Same engineer, different country: predicted pay\n"
                 "(8yr exp, back-end, Python, bachelor's, hybrid, software-dev)")
    for i, v in enumerate(arb["predicted_comp"][::-1]):
        ax.text(v + 1500, i, f"${v:,.0f}", va="center", fontsize=8)
    fig.tight_layout(); fig.savefig("charts/geo_arbitrage.png", dpi=110); plt.close()

    # --- robustness: remote premium within US only ---
    d = pd.read_csv("data/sample.csv")
    us = d[d["Country"] == "United States of America"]
    feats = []
    names = []
    for cat in ["ai_freq", "Ed_simple", "Org_simple", "Age"]:
        ref = {"ai_freq": "no_never", "Ed_simple": "bachelors",
               "Org_simple": "20-99", "Age": "25-34 years old"}[cat]
        for v in sorted(us[cat].dropna().unique()):
            if v == ref:
                continue
            feats.append((us[cat] == v).astype(float).values); names.append(f"{cat}={v}")
    for v in ["Hybrid", "Remote", "Flexible"]:
        feats.append((us["remote_simple"] == v).astype(float).values)
        names.append(f"remote_simple={v}")
    top_ind = us["Industry"].value_counts().head(8).index
    for ind in [i for i in top_ind if i != "Other:" and pd.notna(i)]:
        feats.append((us["Industry"] == ind).astype(float).values); names.append(f"ind={str(ind)[:20]}")
    for c in [c for c in us.columns if c.startswith(("role_", "lang_"))]:
        feats.append(us[c].astype(float).values); names.append(c)
    feats.append(us["manager"].astype(float).values); names.append("manager")
    w = us["WorkExpY"].values
    feats += [w, w ** 2]; names += ["exp", "exp2"]
    m = LinearRegression().fit(np.column_stack(feats), us["log_comp"].values)
    rp = {n: float(np.exp(c) - 1) for n, c in zip(names, m.coef_) if n.startswith("remote_simple=")}
    print(f"\nUS-only OLS (n={len(us)}, R^2={m.score(np.column_stack(feats), us['log_comp'].values):.3f}):")
    for k, v in rp.items():
        print(f"  {k:30s} {v:+.1%}")
    with open("data/us_remote_check.json", "w") as f:
        json.dump(rp, f, indent=1)

if __name__ == "__main__":
    main()
