"""Join public attention (Wikipedia pageviews) with research supply (PubMed papers)
and evidence depth (ClinicalTrials.gov registered trials); score the mispricing.

Inputs:
  data/attention_summary.json, data/pageviews_monthly.csv  (script 01)
  data/pubmed_yearly.csv                                   (script 02)
  ../../2026-09-13/biohacking-evidence-audit/data/trials_summary.json
Outputs:
  data/hype_evidence.csv   one row per biohack
  data/segments.json       k-means segment profiles
"""
import json
import numpy as np
import pandas as pd

EVIDENCE_PATH = "../../2026-09-13/biohacking-evidence-audit/data/trials_summary.json"

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
    # "mouth tape" / "sleepmaxxing": ~no registered trials (pure-hype controls)
}


def main():
    attn = json.load(open("data/attention_summary.json"))
    pubmed = pd.read_csv("data/pubmed_yearly.csv")
    evidence = {r["label"]: r for r in json.load(open(EVIDENCE_PATH))}

    rows = []
    for kw, a in attn.items():
        pm = pubmed[pubmed["keyword"] == kw].set_index("year")["papers"]
        papers_total = int(pm.sum())
        papers_growth = float(pm.loc[2026] / pm.loc[2020]) if pm.loc[2020] > 0 else np.nan
        ev = evidence.get(TREND_TO_EVIDENCE.get(kw, ""))
        rows.append({
            "keyword": kw,
            "article": a["article"],
            "views_total": a["total_views"],
            "views_2026": a["mean_views_2026"],
            "views_growth": a["growth_first12_to_last12"],
            "papers_total": papers_total,
            "papers_growth": round(papers_growth, 3),
            "trials": ev["total_registered"] if ev else 0,
            "with_results": ev["with_results"] if ev else 0,
            "recruiting": ev["recruiting"] if ev else 0,
        })
    df = pd.DataFrame(rows)

    # Headline mispricing: public attention vs registered-trial evidence
    df["z_attention"] = (np.log10(df["views_2026"]) - np.log10(df["views_2026"]).mean()) \
        / np.log10(df["views_2026"]).std()
    log_ev = np.log1p(df["trials"])
    df["z_evidence"] = (log_ev - log_ev.mean()) / log_ev.std()
    df["mispricing"] = df["z_attention"] - df["z_evidence"]  # + = attention outruns evidence
    df["papers_per_million_views"] = df["papers_total"] / (df["views_total"] / 1e6)
    df["trials_per_million_views"] = df["trials"] / (df["views_total"] / 1e6)

    # Segment the market: quadrants on (attention, evidence) medians.
    # Transparent with n=15, and matches the scatter chart's median lines.
    # (k-means was tried: with 15 points it collapses to one big cluster plus
    # singletons, so quadrants are the honest segmentation.)
    med_attn = df["views_2026"].median()
    med_ev = df["trials"].median()

    def quadrant(r):
        hi_a, hi_e = r["views_2026"] >= med_attn, r["trials"] >= med_ev
        if hi_a and hi_e:
            return "Validated blockbusters"  # read a lot AND studied a lot
        if hi_a and not hi_e:
            return "Grift zone"              # read a lot, studied a little
        if not hi_a and hi_e:
            return "Sleepers"                # studied a lot, read a little
        return "Lab curiosities"             # quiet on both fronts

    df["segment"] = df.apply(quadrant, axis=1)
    df["cluster"] = pd.factorize(df["segment"])[0]
    df = df.sort_values("mispricing", ascending=False)
    df.to_csv("data/hype_evidence.csv", index=False)

    seg = {}
    for name in df["segment"].unique():
        m = df[df["segment"] == name].sort_values("mispricing", ascending=False)
        seg[name] = {
            "members": m["keyword"].tolist(),
            "mean_views_2026": round(float(m["views_2026"].mean()), 1),
            "mean_trials": round(float(m["trials"].mean()), 1),
            "mean_mispricing": round(float(m["mispricing"].mean()), 2),
        }
    with open("data/segments.json", "w") as f:
        json.dump(seg, f, indent=2)

    pd.set_option("display.width", 220)
    print(df[["keyword", "views_2026", "views_growth", "papers_total",
              "papers_growth", "trials", "mispricing", "segment"]].to_string(index=False))
    print("\nwrote data/hype_evidence.csv and data/segments.json")


if __name__ == "__main__":
    main()
