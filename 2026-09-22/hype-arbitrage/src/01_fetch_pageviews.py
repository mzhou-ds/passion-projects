"""Fetch monthly Wikipedia pageviews (en.wikipedia, 2020-01 -> 2026-08) for 15 biohacks.

Source: Wikimedia Pageviews REST API (no auth, stable, documented).
Each biohack maps to its Wikipedia article; pageviews proxy public attention.
September 2026 is dropped (partial month).

Output: data/pageviews_monthly.csv (long), data/attention_summary.json
"""
import json
import time
import requests
import pandas as pd

# biohack -> Wikipedia article
ARTICLES = {
    "cold plunge": "Ice_bath",
    "sauna": "Sauna",
    "red light therapy": "Low-level_laser_therapy",
    "intermittent fasting": "Intermittent_fasting",
    "creatine": "Creatine",
    "NMN": "Nicotinamide_mononucleotide",
    "magnesium": "Magnesium_in_biology",
    "ashwagandha": "Ashwagandha",
    "breathwork": "Breathwork",
    "meditation": "Meditation",
    "zone 2": "Aerobic_exercise",
    "keto": "Ketogenic_diet",
    "metformin": "Metformin",
    "light therapy": "Light_therapy",
    "mouth tape": "Mouth_taping",
    # "sleepmaxxing" has no Wikipedia article at all (checked 2026-09-22):
    # the term is too new/fringe for an article -- itself a finding.
}
START, END = "20200101", "20260801"  # full months only
OUT_MONTHLY = "data/pageviews_monthly.csv"
OUT_SUMMARY = "data/attention_summary.json"


def fetch(article):
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           f"en.wikipedia/all-access/user/{article}/monthly/{START}/{END}")
    r = requests.get(url, headers={"User-Agent": "musing-with-mike-research/1.0"},
                     timeout=30)
    r.raise_for_status()
    items = r.json()["items"]
    return pd.DataFrame(
        {"date": [i["timestamp"][:6] for i in items],
         "views": [i["views"] for i in items]})


def main():
    frames = []
    for i, (kw, art) in enumerate(ARTICLES.items()):
        for attempt in range(4):
            try:
                df = fetch(art)
                break
            except Exception as e:
                print(f"  [{kw}] retry {attempt+1}: {type(e).__name__}")
                time.sleep(10 * (attempt + 1))
        else:
            raise RuntimeError(f"failed to fetch {kw}")
        df["keyword"] = kw
        df["article"] = art.replace("_", " ")
        frames.append(df)
        print(f"[{i+1:2d}/15] {kw:22s} months={len(df)} "
              f"total_views={df['views'].sum():,}", flush=True)
        time.sleep(1.2)

    monthly = pd.concat(frames, ignore_index=True)
    monthly.to_csv(OUT_MONTHLY, index=False)

    summary = {}
    for kw in ARTICLES:
        s = monthly[monthly["keyword"] == kw].set_index("date")["views"].sort_index()
        m2020 = s.loc["202001":"202012"].mean()
        m2026 = s.loc["202601":"202608"].mean()
        # growth: last 12 available months vs first 12 (handles short-history
        # articles like Mouth taping, created ~2023)
        first12, last12 = s.iloc[:12].mean(), s.iloc[-12:].mean()
        summary[kw] = {
            "article": ARTICLES[kw].replace("_", " "),
            "total_views": int(s.sum()),
            "mean_views_2020": round(float(m2020), 1) if len(s.loc["202001":"202012"]) else None,
            "mean_views_2026": round(float(m2026), 1),
            "growth_first12_to_last12": round(float(last12 / first12), 3),
            "growth_2020_to_2026": round(float(m2026 / m2020), 3) if m2020 and m2020 > 0 else None,
            "peak_month": s.idxmax(),
            "peak_views": int(s.max()),
        }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2)
    print("wrote", OUT_MONTHLY, "and", OUT_SUMMARY)


if __name__ == "__main__":
    main()
