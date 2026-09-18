"""Part 2b: NHL skater aging curves via the DELTA METHOD.

For players with consecutive qualifying seasons, the year-over-year change in
individual 5v5 scoring rate isolates aging from survivorship bias (a pure
cross-section compares 35-year-old stars to 23-year-old depth players).
Curve: factor(age) = prod of mean log-deltas, normalized to peak = 1.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAW = "data/raw"

def main():
    bd = pd.read_csv("data/processed/skater_birthdates.csv")
    bd["birthDate"] = pd.to_datetime(bd["birthDate"])
    frames = []
    for s in range(2018, 2026):
        d = pd.read_csv(f"{RAW}/mp_{s}_skaters.csv",
                        usecols=["playerId", "season", "name", "position",
                                 "situation", "icetime", "I_F_points",
                                 "I_F_xGoals"])
        d = d[d["situation"] == "5on5"]
        d["season_label"] = s
        frames.append(d)
    sk = pd.concat(frames, ignore_index=True)
    sk = sk.merge(bd, on="playerId", how="inner")
    sk["age"] = (sk["season_label"] + 1) - sk["birthDate"].dt.year \
        + (sk["birthDate"].dt.month > 2).astype(int) * -1 + 0.5
    sk["age_int"] = sk["age"].round().astype(int)
    sk = sk[sk["icetime"] >= 2000].copy()
    hrs = sk["icetime"] / 3600.0
    sk["P60"] = sk["I_F_points"] / hrs
    sk["xG60"] = sk["I_F_xGoals"] / hrs
    sk["isD"] = (sk["position"] == "D").astype(int)

    out_rows = []
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, pos, label, min_n, start_age, win in zip(
            axes, [0, 1], ["Forwards", "Defense"], [20, 30], [20, 22], [3, 5]):
        sub = sk[sk["isD"] == pos].sort_values(["playerId", "season_label"])
        for metric, color in [("P60", "C0"), ("xG60", "C1")]:
            deltas = []
            for pid, g in sub.groupby("playerId"):
                g = g.sort_values("season_label")
                for i in range(1, len(g)):
                    a, b = g.iloc[i - 1], g.iloc[i]
                    if b["season_label"] - a["season_label"] == 1 and \
                       a[metric] > 0 and b[metric] > 0:
                        deltas.append((b["age_int"], np.log(b[metric] / a[metric])))
            dd = pd.DataFrame(deltas, columns=["age", "dlog"]).dropna()
            m = dd.groupby("age")["dlog"].agg(["mean", "count"]).reset_index()
            m = m[(m["age"] >= start_age) & (m["age"] <= 38) & (m["count"] >= min_n)]
            m = m.sort_values("age")
            m["smooth"] = m["mean"].rolling(win, center=True, min_periods=1).mean()
            ages = np.arange(start_age, 39)
            sm = dict(zip(m["age"], m["smooth"]))
            last = 0.0
            curve = [1.0]
            for a in ages[1:]:
                last = sm.get(a, last)
                curve.append(curve[-1] * np.exp(last))
            curve = np.array(curve)
            peak = curve.max()
            ax.plot(ages, curve / peak, "o-", ms=4, color=color, label=metric)
            pk = ages[curve.argmax()]
            i35 = list(ages).index(35)
            print(f"{label} {metric}: n_pairs={len(dd)}, peak~{pk}, "
                  f"age35={curve[i35]/peak:.2f} of peak")
            for a, v in zip(ages, curve / peak):
                out_rows.append({"pos": label[0], "age": int(a),
                                 "metric": metric, "factor": round(float(v), 4)})
        # extend to 19 and 39 by edge values for lookup safety
        ax.set_title(label)
        ax.set_xlabel("age")
        ax.legend()
    axes[0].set_ylabel("rate relative to peak (delta method)")
    fig.suptitle("NHL aging curves: year-over-year change in 5v5 scoring rate (2018-19 to 2025-26)")
    fig.tight_layout()
    fig.savefig("figures/02_age_curves.png", dpi=130)
    df = pd.DataFrame(out_rows)
    # pad 19/39 with edge values for lookup safety
    pad = []
    for (pos, metric), g in df.groupby(["pos", "metric"]):
        lo, hi = g["age"].min(), g["age"].max()
        for a in range(19, lo):
            pad.append({"pos": pos, "age": a, "metric": metric,
                        "factor": g[g.age == lo]["factor"].iloc[0]})
        pad.append({"pos": pos, "age": 39, "metric": metric,
                    "factor": g[g.age == hi]["factor"].iloc[0]})
    df = pd.concat([df, pd.DataFrame(pad)], ignore_index=True)
    df.to_csv("data/processed/age_curve.csv", index=False)
    print("saved figures/02_age_curves.png, data/processed/age_curve.csv")

if __name__ == "__main__":
    main()
