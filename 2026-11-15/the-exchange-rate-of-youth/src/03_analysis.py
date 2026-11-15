"""03_analysis.py — the exchange rate between age and bodyweight in strength.

Question: how many kilos of bodyweight does it take to buy back one year of
aging? Experts know strength falls with age and rises with bodyweight. Nobody
has put a number on the trade, or shown how it differs by lift, by sex, or
across the masters years.

Method
------
* Cross-sectional model, per sex: log(total) ~ spline(age) + log(BW) +
  spline(age) x log(BW), ridge regression. Partial derivatives taken
  numerically give the exchange rate E(age, BW) = (d logT/d age)/(d logT/d BW)
  in kg of bodyweight per year of age. Same model per lift.
* Masters cliff: piecewise-linear search for the knot age where the age slope
  steepens most (model predictions at fixed BW).
* Longitudinal check: lifters with >=6 meets spanning >=10 years; per-lifter
  OLS slope of log(total) on age. Cross-sectional curves flatter aging if
  weak lifters quit, so the within-lifter slope is the honest decline.
* Diminishing returns: the bodyweight where the marginal return to another
  kilo falls below 0.3%/kg, by age — the weight where gaining mass stops
  paying, and whether that weight falls as lifters age.

Outputs: data/analysis.json, data/*.csv tables.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler

HERE = Path(__file__).resolve().parent.parent
DATA = HERE / "data"
RNG = np.random.default_rng(7)

LIFTS = {"TotalKg": "total", "Best3SquatKg": "squat",
         "Best3BenchKg": "bench", "Best3DeadliftKg": "deadlift"}


def load():
    d = pd.read_csv(DATA / "clean_lifts.csv", parse_dates=["Date"])
    d["logBW"] = np.log(d["BodyweightKg"])
    return d


def design(age, logbw):
    """Spline basis for age + logBW + their interactions (age basis x logBW)."""
    st = SplineTransformer(n_knots=9, degree=3, include_bias=False)
    a = st.fit_transform(age.reshape(-1, 1))
    X = np.column_stack([a, logbw, a * (logbw - logbw.mean())[:, None]])
    return X, st


def fit_model(d, ycol):
    """Fit log(y) ~ spline(age) + logBW + interactions; return model + transformer."""
    y = np.log(d[ycol].values)
    age = d["Age"].values.astype(float)
    logbw = d["logBW"].values
    st = SplineTransformer(n_knots=9, degree=3, include_bias=False)
    a = st.fit_transform(age.reshape(-1, 1))
    lbw_c = logbw - logbw.mean()
    X = np.column_stack([a, logbw, a * lbw_c[:, None]])
    model = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 12)))
    model.fit(X, y)
    r2 = cross_val_score(model, X, y, cv=3, scoring="r2").mean()
    return model, st, logbw.mean(), r2


def predict(model, st, lbw_mean, ages, bws):
    ages = np.asarray(ages, dtype=float)
    bws = np.asarray(bws, dtype=float)
    logbw = np.log(bws)
    a = st.transform(ages.reshape(-1, 1))
    X = np.column_stack([a, logbw, a * (logbw - lbw_mean)[:, None]])
    return np.exp(model.predict(X))


def exchange_rate(model, st, lbw_mean, age, bw):
    """kg of bodyweight that offsets one year of aging, at (age, bw)."""
    base = predict(model, st, lbw_mean, [age], [bw])[0]
    d_age = (predict(model, st, lbw_mean, [age + 0.5], [bw])[0]
             - predict(model, st, lbw_mean, [age - 0.5], [bw])[0]) / base
    d_bw = (predict(model, st, lbw_mean, [age], [bw + 1.0])[0]
            - predict(model, st, lbw_mean, [age], [bw - 1.0])[0]) / (2 * base)
    return -d_age / d_bw, d_age, d_bw  # kg/yr, %/yr, %/kg


def main():
    d = load()
    out = {"sample": {"rows": int(len(d)), "lifters": int(d["Name"].nunique()),
                      "men": int((d["Sex"] == "M").sum()),
                      "women": int((d["Sex"] == "F").sum())}}
    ref_bw = {"M": 90.0, "F": 65.0}

    # ---- 1. Exchange-rate curves, per sex and per lift -------------------
    curves, rates = [], []
    for sex in ["M", "F"]:
        ds = d[d["Sex"] == sex]
        for ycol, lname in LIFTS.items():
            model, st, lbw_mean, r2 = fit_model(ds, ycol)
            out.setdefault("model_r2", {})[f"{sex}_{lname}"] = round(float(r2), 3)
            for age in range(20, 76, 5):
                for bw in ([70, 90, 110] if sex == "M" else [55, 65, 80]):
                    E, d_age, d_bw = exchange_rate(model, st, lbw_mean, age, bw)
                    rates.append({"sex": sex, "lift": lname, "age": age, "bw": bw,
                                  "kg_per_year": round(float(E), 2),
                                  "pct_per_year": round(float(d_age * 100), 2),
                                  "pct_per_kg": round(float(d_bw * 100), 3)})
            ages = np.arange(18, 76)
            pred = predict(model, st, lbw_mean, ages,
                           np.full_like(ages, ref_bw[sex], dtype=float))
            for a, p in zip(ages, pred):
                curves.append({"sex": sex, "lift": lname, "age": int(a),
                               "pred_kg": round(float(p), 1)})
    pd.DataFrame(rates).to_csv(DATA / "exchange_rates.csv", index=False)
    pd.DataFrame(curves).to_csv(DATA / "age_curves.csv", index=False)

    # headline exchange rates at reference bodyweight
    r = pd.DataFrame(rates)
    head = {}
    for sex in ["M", "F"]:
        for lname in ["total", "squat", "bench", "deadlift"]:
            sub = r[(r.sex == sex) & (r.lift == lname) & (r.bw == ref_bw[sex])]
            head[f"{sex}_{lname}"] = {int(row.age): row.kg_per_year
                                      for row in sub.itertuples()}
    out["exchange_rate_kg_per_year"] = head

    # ---- 2. Masters cliff: piecewise-linear knot search ------------------
    cliffs = {}
    for sex in ["M", "F"]:
        ds = d[d["Sex"] == sex]
        model, st, lbw_mean, _ = fit_model(ds, "TotalKg")
        ages = np.arange(20, 76)
        pred = np.log(predict(model, st, lbw_mean, ages,
                              np.full_like(ages, ref_bw[sex], dtype=float)))
        best = None
        for knot in range(35, 66):
            x1 = np.minimum(ages - 20, knot - 20)
            x2 = np.maximum(ages - knot, 0)
            X = np.column_stack([np.ones_like(ages, dtype=float), x1, x2])
            beta, res, *_ = np.linalg.lstsq(X, pred, rcond=None)
            sse = float(((X @ beta - pred) ** 2).sum())
            if best is None or sse < best[0]:
                best = (sse, knot, beta)
        _, knot, beta = best
        cliffs[sex] = {"knot_age": int(knot),
                       "slope_before_pct_per_year": round(float(beta[1] * 100), 2),
                       "slope_after_pct_per_year": round(float((beta[1] + beta[2]) * 100), 2)}
    out["masters_cliff"] = cliffs

    # ---- 3. Decade cost at fixed bodyweight ------------------------------
    decade = []
    for sex in ["M", "F"]:
        ds = d[d["Sex"] == sex]
        model, st, lbw_mean, _ = fit_model(ds, "TotalKg")
        for a0 in [25, 35, 45, 55]:
            p0 = predict(model, st, lbw_mean, [a0], [ref_bw[sex]])[0]
            p1 = predict(model, st, lbw_mean, [a0 + 10], [ref_bw[sex]])[0]
            decade.append({"sex": sex, "decade_start": a0,
                           "pct_lost_per_decade": round(float((p1 / p0 - 1) * 100), 1)})
    pd.DataFrame(decade).to_csv(DATA / "decade_cost.csv", index=False)
    out["decade_cost_pct"] = {f"{row.sex}_{row.decade_start}": row.pct_lost_per_decade
                              for row in pd.DataFrame(decade).itertuples()}

    # ---- 4. Longitudinal: within-lifter decline --------------------------
    long_rows = []
    g = d.sort_values("Date").groupby(["Name", "Sex"])
    for (name, sex), grp in g:
        if len(grp) >= 6 and grp["Age"].max() - grp["Age"].min() >= 10:
            x = grp["Age"].values.astype(float)
            y = np.log(grp["TotalKg"].values)
            slope = np.polyfit(x, y, 1)[0]
            long_rows.append({"sex": sex, "age_first": float(x.min()),
                              "age_last": float(x.max()),
                              "n_meets": len(grp),
                              "slope_pct_per_year": float(slope * 100)})
    long_df = pd.DataFrame(long_rows)
    long_df.to_csv(DATA / "longitudinal.csv", index=False)
    long_sum = {}
    for sex in ["M", "F"]:
        sub = long_df[long_df.sex == sex]
        long_sum[sex] = {
            "lifters": int(len(sub)),
            "median_slope_pct_per_year": round(float(sub["slope_pct_per_year"].median()), 2),
            "median_slope_20s_start": round(float(
                sub[sub.age_first < 30]["slope_pct_per_year"].median()), 2)
            if (sub.age_first < 30).any() else None,
            "median_slope_40s_start": round(float(
                sub[(sub.age_first >= 40) & (sub.age_first < 50)]["slope_pct_per_year"].median()), 2)
            if ((sub.age_first >= 40) & (sub.age_first < 50)).any() else None,
        }
    out["longitudinal"] = long_sum

    # ---- 5. Diminishing returns: where does another kilo stop paying? ----
    dim = []
    for sex in ["M", "F"]:
        ds = d[d["Sex"] == sex]
        model, st, lbw_mean, _ = fit_model(ds, "TotalKg")
        bw_grid = np.arange(50, 161) if sex == "M" else np.arange(40, 121)
        for age in [25, 40, 55]:
            rets = []
            for bw in bw_grid:
                _, _, d_bw = exchange_rate(model, st, lbw_mean, age, float(bw))
                rets.append(d_bw * 100)
            rets = np.array(rets)
            below = bw_grid[rets < 0.3]
            dim.append({"sex": sex, "age": age,
                        "bw_where_marginal_below_0.3pct": int(below[0]) if len(below) else None,
                        "marginal_at_90kg" if sex == "M" else "marginal_at_65kg":
                            round(float(rets[list(bw_grid).index(ref_bw[sex])]), 3)})
    pd.DataFrame(dim).to_csv(DATA / "diminishing_returns.csv", index=False)
    out["diminishing_returns"] = dim

    # ---- 6. GBM check: do age and bodyweight dominate? -------------------
    imp = {}
    for sex in ["M", "F"]:
        ds = d[d["Sex"] == sex].copy()
        ds["AgeBand"] = ds["Age"]
        X = ds[["Age", "BodyweightKg"]].values
        y = np.log(ds["TotalKg"].values)
        m = HistGradientBoostingRegressor(random_state=7, max_iter=300)
        m.fit(X, y)
        pi = permutation_importance(m, X[:20000], y[:20000], n_repeats=3,
                                    random_state=7)
        imp[sex] = {"r2": round(float(m.score(X, y)), 3),
                    "age_importance": round(float(pi.importances_mean[0]), 4),
                    "bw_importance": round(float(pi.importances_mean[1]), 4)}
    out["gbm_check"] = imp

    (DATA / "analysis.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
