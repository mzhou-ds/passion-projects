"""
PubMed publication counts per intervention via NCBI E-utilities (public,
no key; we throttle to ~3 req/s per NCBI guidance).

Two counts per intervention:
  - all PubMed records matching the term
  - records tagged as randomized controlled trials (publication type)

The ratio publications:trial-registrations is a rough 'paper trail vs
registered trail' lens — not a quality score, and the README says so.
Output: data/pubmed_counts.csv
"""
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

TERMS = {
    "Creatine": '"creatine monohydrate"',
    "Magnesium": '"magnesium supplementation"',
    "Ashwagandha": "ashwagandha",
    "NMN": '"nicotinamide mononucleotide"',
    "Nicotinamide riboside": '"nicotinamide riboside"',
    "Resveratrol": "resveratrol",
    "Melatonin": "melatonin",
    "L-Theanine": '"L-theanine"',
    "Omega-3": '"omega-3 fatty acids"',
    "Vitamin D": '"vitamin D supplementation"',
    "CoQ10": '"coenzyme Q10"',
    "Berberine": "berberine",
    "Lion's mane": '"Hericium erinaceus"',
    "Bacopa": '"Bacopa monnieri"',
    "Rhodiola": '"Rhodiola rosea"',
    "Glycine": "glycine supplementation",
    "Tongkat ali": '"Eurycoma longifolia"',
    "Apigenin": "apigenin",
    "Metformin (benchmark)": "metformin",
    "Sirolimus/rapamycin (benchmark)": "sirolimus",
}


def count(term, rct_only=False):
    q = term
    if rct_only:
        q += ' AND "Randomized Controlled Trial"[Publication Type]'
    for attempt in range(4):
        try:
            r = requests.get(
                ESEARCH,
                params={"db": "pubmed", "term": q, "retmode": "json", "retmax": 0},
                timeout=60,
            )
            r.raise_for_status()
            return int(r.json()["esearchresult"]["count"])
        except Exception as e:
            print(f"  retry {attempt+1}: {e}", flush=True)
            time.sleep(2 * (attempt + 1))
    return None


def main():
    rows = []
    for label, term in TERMS.items():
        total = count(term)
        time.sleep(0.4)
        rct = count(term, rct_only=True)
        time.sleep(0.4)
        rows.append({"intervention": label, "pubmed_total": total, "pubmed_rct": rct})
        print(f"{label:38s} pubmed={total} rct={rct}", flush=True)
    pd.DataFrame(rows).to_csv(ROOT / "data" / "pubmed_counts.csv", index=False)


if __name__ == "__main__":
    main()
