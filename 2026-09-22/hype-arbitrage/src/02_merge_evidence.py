"""Join Google Trends hype with ClinicalTrials.gov evidence; score the mispricing.

Inputs:
  data/trends_monthly.csv, data/trends_summary.json   (script 01)
  ../../../2026-09-13/biohacking-evidence-audit/data/trials_summary.json
Outputs:
  data/hype_evidence.csv   one row per biohack: hype, growth, trials, mispricing, segment
  data/segments.json       k-means segment profiles + member lists
"""
import json
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

EVIDENCE_PATH = "../../2026-09-13/biohacking-evidence-audit/data/trials_summary.json"

# Google Trends term -> ClinicalTrials.gov evidence label (from the 2026-09-13 audit)
TREND_TO_EVIDENCE = {
    "cold plunge": "Cold water immersion / cold plunge",
    "sauna": "Sauna / heat therapy",
    "red light therapy": "Red light therapy",
    "intermittent fasting": "Intermittent fasting",
    "creatine": "Creatine",
    "NMN": "NMN",
    "magnesium": "Magnesium supplementation",
    "ashwagandha": "Ashwagandha",
    "breathwork": "Breathwork",
    "meditation": "Mindfulness meditation",
    "zone 2": "Zone 2 / aerobic exercise",
    "keto": "Ketogenic diet",
    "metformin": "Metformin for aging/longevity",
    "light therapy": "Light therapy for circadian rhythm",
    # "mouth tape" and "sleepmaxxing" have ~no registered trials: pure-hype controls
}


def main():
    trends = json.load(open("data/trends_summary.json"))
    evidence = {r["label"]: r for r in json.load(open(EVIDENCE_PATH))}

    rows = []
    for kw, t in trends.items():
        ev = evidence.get(TREND_TO_EVIDENCE.get(kw, ""), None)
        rows.append({
            "keyword": kw,
            "hype_2026": t["mean_index_2026"],
            "hype_growth": t["growth_2020_to_2026"],
            "peak_month": t["peak_month"],
            "trials": ev["total_registered"] if ev else 0,
            "completed": ev["completed"] if ev else 0,
            "with_results": ev["with_results"] if ev else 0,
            "recruiting": ev["recruiting"] if ev else 0,
            "median_n": ev["median_enrollment"] if ev else 0,
        })
    df = pd.DataFrame(rows)

    df["results_rate"] = (df["with_results"] / df["completed"].replace(0, np.nan)).fillna(0)
    # z-scored mispricing: hype rank minus evidence rank (evidence on log scale)
    df["z_hype"] = (df["hype_2026"] - df["hype_2026"].mean()) / df["hype_2026"].std()
    log_ev = np.log1p(df["trials"])
    df["z_evidence"] = (log_ev - log_ev.mean()) / log_ev.std()
    df["mispricing"] = df["z_hype"] - df["z_evidence"]   # + = hype outruns evidence
    df["trials_per_hype_pt"] = df["trials"] / df["hype_2026"].replace(0, np.nan)

    # Segment the market: k-means on [hype level, hype growth, log evidence, results rate]
    feats = pd.DataFrame({
        "hype": df["z_hype"],
        "growth": (df["hype_growth"] - df["hype_growth"].mean()) / df["hype_growth"].std(),
        "evidence": df["z_evidence"],
        "results_rate": (df["results_rate"] - df["results_rate"].mean()) / df["results_rate"].std(),
    }).fillna(0)
    km = KMeans(n_clusters=4, n_init=20, random_state=42)
    df["cluster"] = km.fit_predict(StandardScaler().fit_transform(feats))

    # Name clusters by their centroid profile
    prof = feats.copy(); prof["cluster"] = df["cluster"].values
    cent = prof.groupby("cluster").mean()
    names = {}
    for c in cent.index:
        h, g, e, r = cent.loc[c, ["hype", "growth", "evidence", "results_rate"]]
        if h > 0.3 and e < -0.2:
            names[c] = "Grift zone"          # loud, thin evidence
        elif h > 0.3 and e >= -0.2:
            names[c] = "Validated blockbusters"  # loud AND studied
        elif h <= 0.3 and e > 0.3:
            names[c] = "Sleepers"            # studied, nobody's searching
        else:
            names[c] = "Lab curiosities"     # quiet on both fronts
    df["segment"] = df["cluster"].map(names)

    df = df.sort_values("mispricing", ascending=False)
    df.to_csv("data/hype_evidence.csv", index=False)

    seg = {}
    for c, name in names.items():
        members = df[df["cluster"] == c].sort_values("mispricing", ascending=False)
        seg[name] = {
            "members": members["keyword"].tolist(),
            "mean_hype_2026": round(float(members["hype_2026"].mean()), 2),
            "mean_trials": round(float(members["trials"].mean()), 1),
            "mean_mispricing": round(float(members["mispricing"].mean()), 2),
        }
    with open("data/segments.json", "w") as f:
        json.dump(seg, f, indent=2)

    pd.set_option("display.width", 200)
    print(df[["keyword", "hype_2026", "hype_growth", "trials", "mispricing", "segment"]]
          .to_string(index=False))
    print("\nwrote data/hype_evidence.csv and data/segments.json")


if __name__ == "__main__":
    main()
