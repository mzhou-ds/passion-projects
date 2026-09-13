"""
Part 1: The Clinical Evidence Audit
Pulls every registered clinical trial matching popular "biohacks" from the
ClinicalTrials.gov API v2 (run date: 2026-09-13) and summarizes the state of
evidence: trial counts, interventional share, phases, statuses, enrollment,
results availability, and first-posted trend.
"""
import json
import time
from pathlib import Path
from urllib.parse import quote

import requests

BASE = "https://clinicaltrials.gov/api/v2/studies"
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

# (label, search term) — terms chosen to capture the biohack without
# drowning in unrelated trials
TERMS = [
    ("Cold water immersion / cold plunge", "cold water immersion"),
    ("Sauna / heat therapy", "sauna"),
    ("Red light therapy", "photobiomodulation"),
    ("Intermittent fasting", "intermittent fasting"),
    ("Time-restricted eating", "time restricted eating"),
    ("NMN", "nicotinamide mononucleotide"),
    ("Metformin for aging/longevity", "metformin aging"),
    ("Creatine", "creatine supplementation"),
    ("Mindfulness meditation", "mindfulness meditation"),
    ("Breathwork", "breathwork"),
    ("Light therapy for circadian rhythm", "light therapy circadian"),
    ("Ketogenic diet", "ketogenic diet"),
    ("Ashwagandha", "ashwagandha"),
    ("Magnesium supplementation", "magnesium supplementation"),
    ("Zone 2 / aerobic exercise", "zone 2 exercise"),
]

FIELDS = ",".join(
    [
        "NCTId",
        "OverallStatus",
        "StudyType",
        "Phases",
        "StartDate",
        "EnrollmentCount",
        "HasResults",
        "FirstPosted",
    ]
)


def fetch_term(term):
    """Return (total_count, list of study dicts)."""
    studies = []
    url = f"{BASE}?query.term={quote(term)}&pageSize=1000&countTotal=true"
    total = None
    while url:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        payload = r.json()
        if total is None:
            total = payload.get("totalCount")
        studies.extend(payload.get("studies", []))
        token = payload.get("nextPageToken")
        url = (
            f"{BASE}?query.term={quote(term)}&pageSize=1000&countTotal=true"
            f"&pageToken={token}"
            if token
            else None
        )
        time.sleep(0.5)
    return total, studies


def summarize(label, term, total, studies):
    def get(s, *keys, default=None):
        d = s
        for k in keys:
            d = (d or {}).get(k)
            if d is None:
                return default
        return d

    rows = []
    for s in studies:
        rows.append(
            {
                "nct": get(s, "protocolSection", "identificationModule", "nctId"),
                "status": get(s, "protocolSection", "statusModule", "overallStatus"),
                "study_type": get(s, "protocolSection", "designModule", "studyType"),
                "phases": get(s, "protocolSection", "designModule", "phases") or [],
                "start": get(s, "protocolSection", "statusModule", "startDateStruct", "date"),
                "enrollment": get(s, "protocolSection", "designModule", "enrollmentInfo", "count"),
                "has_results": s.get("resultsSection") is not None,
                "first_posted": get(s, "protocolSection", "statusModule", "studyFirstPostDateStruct", "date"),
            }
        )
    interventional = [r for r in rows if r["study_type"] == "INTERVENTIONAL"]
    return {
        "label": label,
        "term": term,
        "total_registered": total,
        "records_retrieved": len(rows),
        "interventional": len(interventional),
        "completed": sum(1 for r in rows if r["status"] == "COMPLETED"),
        "recruiting": sum(
            1 for r in rows if r["status"] in ("RECRUITING", "NOT_YET_RECRUITING")
        ),
        "with_results": sum(1 for r in rows if r["has_results"]),
        "median_enrollment": median(
            [r["enrollment"] for r in rows if isinstance(r["enrollment"], int)]
        ),
        "by_start_year": year_counts([r["start"] for r in rows]),
        "phase_counts": phase_counts(rows),
    }


def median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def year_counts(dates):
    counts = {}
    for d in dates:
        if d and len(d) >= 4 and d[:4].isdigit():
            counts[d[:4]] = counts.get(d[:4], 0) + 1
    return dict(sorted(counts.items()))


def phase_counts(rows):
    counts = {}
    for r in rows:
        phases = r["phases"] or ["N/A"]
        for p in phases:
            counts[p] = counts.get(p, 0) + 1
    return counts


def main():
    summary = []
    for label, term in TERMS:
        print(f"Fetching: {label} ...", flush=True)
        total, studies = fetch_term(term)
        s = summarize(label, term, total, studies)
        summary.append(s)
        print(
            f"  total={total} retrieved={s['records_retrieved']} "
            f"interventional={s['interventional']} completed={s['completed']}"
        )
    (OUT / "trials_summary.json").write_text(json.dumps(summary, indent=2))
    print("Wrote", OUT / "trials_summary.json")


if __name__ == "__main__":
    main()
