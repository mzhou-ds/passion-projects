"""Fetch PubMed publication counts per year (2020-2026) for each biohack.

Source: NCBI E-utilities esearch (no key; <=3 req/s respected with 0.4s sleeps).
Counts only (retmax=0). Queries are quoted phrases; see PUBMED_QUERIES.

Output: data/pubmed_yearly.csv  (keyword, year, papers)
"""
import csv
import time
import urllib.parse
import requests

PUBMED_QUERIES = {
    "cold plunge": '("cold plunge" OR "cold water immersion")',
    "sauna": "sauna",
    "red light therapy": '("red light therapy" OR photobiomodulation)',
    "intermittent fasting": '"intermittent fasting"',
    "creatine": "creatine supplementation",
    "NMN": '("nicotinamide mononucleotide" OR NMN)',
    "magnesium": '"magnesium supplementation"',
    "ashwagandha": "ashwagandha",
    "breathwork": "breathwork",
    "meditation": '("mindfulness meditation" OR meditation)',
    "zone 2": '"zone 2" exercise training',
    "keto": '"ketogenic diet"',
    "metformin": "metformin",
    "light therapy": '"light therapy" circadian',
    "mouth tape": '"mouth taping"',
    "sleepmaxxing": "sleepmaxxing",
}
YEARS = list(range(2020, 2027))
OUT = "data/pubmed_yearly.csv"
BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"


def count(query, year):
    params = {
        "db": "pubmed",
        "term": f"{query} AND {year}[pdat]",
        "datetype": "pdat",
        "retmode": "json",
        "retmax": "0",
    }
    for attempt in range(4):
        try:
            r = requests.get(BASE, params=params, timeout=30,
                             headers={"User-Agent": "musing-with-mike-research/1.0"})
            r.raise_for_status()
            return int(r.json()["esearchresult"]["count"])
        except Exception as e:
            print(f"  retry {attempt+1} [{query} {year}]: {type(e).__name__}")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"failed: {query} {year}")


def main():
    rows = []
    for i, (kw, q) in enumerate(PUBMED_QUERIES.items()):
        for y in YEARS:
            n = count(q, y)
            rows.append({"keyword": kw, "year": y, "papers": n,
                         "query": q})
            time.sleep(0.4)  # stay under 3 req/s
        total = sum(r["papers"] for r in rows if r["keyword"] == kw)
        print(f"[{i+1:2d}/16] {kw:22s} papers 2020-2026: {total}", flush=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["keyword", "year", "papers", "query"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
