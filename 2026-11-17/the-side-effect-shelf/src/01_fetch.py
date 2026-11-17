#!/usr/bin/env python3
"""Build #71 — The Side-Effect Shelf.
Fetch 1: openFDA FAERS (drug event) — adverse-event reports naming each
biohacking-shelf molecule as the SUSPECT drug.
Fetch 2: ClinicalTrials.gov v2 — registered trials by intervention name.
Fetch 3: PubMed E-utilities — published randomized controlled trials.

All raw responses are saved under data/raw/ so the run is re-auditable.
openFDA without a key allows ~240 req/min and ~1000 req/day; this script
makes roughly 400 requests, with a 0.25s pause between them.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# (label, faers_names, trials_term, pubmed_term, group)
COMPOUNDS = [
    # --- the biohacking shelf ---
    ("berberine", ["berberine"], "Berberine", "berberine", "shelf"),
    ("methylene blue", ["methylene blue"], "Methylene Blue", "methylene blue", "shelf"),
    ("quercetin", ["quercetin"], "Quercetin", "quercetin", "shelf"),
    ("resveratrol", ["resveratrol"], "Resveratrol", "resveratrol", "shelf"),
    ("DHEA", ["dehydroepiandrosterone", "dhea"], "DHEA", "dehydroepiandrosterone", "shelf"),
    ("ashwagandha", ["ashwagandha"], "Ashwagandha", "ashwagandha", "shelf"),
    ("nicotinamide riboside", ["nicotinamide riboside"], "Nicotinamide Riboside",
     "nicotinamide riboside", "shelf"),
    ("NMN", ["nicotinamide mononucleotide"], "Nicotinamide Mononucleotide",
     "nicotinamide mononucleotide", "shelf"),
    ("BPC-157", ["BPC-157", "bpc 157"], "BPC 157", "BPC-157", "shelf"),
    ("spermidine", ["spermidine"], "Spermidine", "spermidine", "shelf"),
    ("urolithin A", ["urolithin a"], "Urolithin A", "urolithin A", "shelf"),
    ("fisetin", ["fisetin"], "Fisetin", "fisetin", "shelf"),
    ("pregnenolone", ["pregnenolone"], "Pregnenolone", "pregnenolone", "shelf"),
    ("lithium orotate", ["lithium orotate"], "Lithium Orotate", "lithium orotate", "shelf"),
    ("taurine", ["taurine"], "Taurine", "taurine", "shelf"),
    ("NAD+", ["nicotinamide adenine dinucleotide"], "NAD+", "nicotinamide adenine dinucleotide", "shelf"),
    # --- boring controls: widely used, "safe" reputation ---
    ("creatine", ["creatine"], "Creatine", "creatine", "control"),
    ("melatonin", ["melatonin"], "Melatonin", "melatonin", "control"),
    ("caffeine", ["caffeine"], "Caffeine", "caffeine", "control"),
    ("vitamin D", ["cholecalciferol", "vitamin d"], "Vitamin D", "vitamin D", "control"),
    ("magnesium", ["magnesium"], "Magnesium", "magnesium", "control"),
    # --- pharma benchmarks: prescription drugs, defined patient populations ---
    ("semaglutide", ["semaglutide"], "Semaglutide", "semaglutide", "pharma"),
    ("metformin", ["metformin"], "Metformin", "metformin", "pharma"),
    ("sirolimus", ["sirolimus", "rapamycin"], "Sirolimus", "sirolimus", "pharma"),
]

TREND_YEARS = list(range(2012, 2027))
TREND_MIN_TOTAL = 300  # only trend compounds with enough reports to be meaningful


def get_json(url, tries=4):
    """openFDA returns HTTP 404 with a NOT_FOUND body when a search matches
    nothing — that is a zero, not an error. 500s/403s are transient."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "passion-projects-build/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"meta": {"results": {"total": 0}}, "results": []}
            last = e
            time.sleep(2 * (i + 1))
        except Exception as e:  # openFDA 500s/403s are transient; back off and retry
            last = e
            time.sleep(2 * (i + 1))
    raise last


def fda_total(search):
    url = ("https://api.fda.gov/drug/event.json?search="
           + urllib.parse.quote(search) + "&limit=1")
    d = get_json(url)
    return d["meta"]["results"]["total"]


def fda_count(search, field, limit=15):
    url = ("https://api.fda.gov/drug/event.json?search="
           + urllib.parse.quote(search)
           + "&count=" + urllib.parse.quote(field)
           + f"&limit={limit}")
    d = get_json(url)
    return d.get("results", [])


def trials_count(term):
    """Count registered trials whose intervention name matches, via
    filter.advanced AREA[InterventionName]. Paginates (pageSize=1000)."""
    total = 0
    token = None
    while True:
        params = {"filter.advanced": f"AREA[InterventionName]{term}",
                  "pageSize": 1000, "format": "json"}
        if token:
            params["pageToken"] = token
        url = "https://clinicaltrials.gov/api/v2/studies?" + urllib.parse.urlencode(params)
        d = get_json(url)
        total += len(d.get("studies", []))
        token = d.get("nextPageToken")
        if not token:
            return total


def pubmed_rct_count(term):
    q = f"{term}[Title/Abstract] AND randomized controlled trial[pt]"
    url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term="
           + urllib.parse.quote(q) + "&retmode=json&retmax=0")
    d = get_json(url)
    return int(d["esearchresult"]["count"])


def main():
    summary = {}
    for label, names, trials_term, pubmed_term, group in COMPOUNDS:
        slug = label.lower().replace(" ", "_").replace("+", "plus")
        raw_path = RAW / f"{slug}.json"
        if raw_path.exists():
            print(f"{label:25s} (resumed from {raw_path.name})", flush=True)
            summary[label] = json.loads(raw_path.read_text())
            continue
        q_any = " OR ".join(f'patient.drug.medicinalproduct:"{n}"' for n in names)
        q_sus = f"({q_any}) AND patient.drug.drugcharacterization:1"
        rec = {"label": label, "group": group, "faers_names": names}
        rec["total_any_role"] = fda_total(q_any)
        time.sleep(0.25)
        rec["total_suspect"] = fda_total(q_sus)
        time.sleep(0.25)
        for key, extra in [
            ("serious", "AND serious:1"),
            ("deaths", "AND seriousnessdeath:1"),
            ("hospitalizations", "AND seriousnesshospitalization:1"),
            ("life_threatening", "AND seriousnesslifethreatening:1"),
            ("disability", "AND seriousnessdisabling:1"),
        ]:
            rec[key] = fda_total(f"{q_sus} {extra}")
            time.sleep(0.25)
        rec["top_reactions"] = fda_count(q_sus, "patient.reaction.reactionmeddrapt.exact", 15)
        time.sleep(0.25)
        rec["reporter_qualification"] = fda_count(q_sus, "primarysource.qualification", 10)
        time.sleep(0.25)
        # year trend, only for compounds with enough reports
        rec["trend"] = {}
        if rec["total_suspect"] >= TREND_MIN_TOTAL:
            for y in TREND_YEARS:
                rec["trend"][str(y)] = fda_total(
                    f"{q_sus} AND receiptdate:[{y}0101 TO {y}1231]")
                time.sleep(0.25)
        # evidence axis
        rec["trials_registered"] = trials_count(trials_term)
        time.sleep(0.25)
        rec["pubmed_rcts"] = pubmed_rct_count(pubmed_term)
        time.sleep(0.25)
        summary[label] = rec
        (RAW / f"{slug}.json").write_text(json.dumps(rec, indent=2))
        print(f"{label:25s} suspect={rec['total_suspect']:7d} serious={rec['serious']:7d} "
              f"deaths={rec['deaths']:5d} trials={rec['trials_registered']:5d} "
              f"rcts={rec['pubmed_rcts']:5d}", flush=True)

    (BASE / "data" / "faers_summary.json").write_text(json.dumps(summary, indent=2))
    print("saved data/faers_summary.json")


if __name__ == "__main__":
    main()
