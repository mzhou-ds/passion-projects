"""
Fetch biohacking-intervention trials from ClinicalTrials.gov API v2.

No API key required. Docs: https://clinicaltrials.gov/data-api/api
We query by intervention name (query.intr), page at 100/page, cap per
intervention so the big generic terms (Vitamin D, Melatonin) don't swamp
the niche longevity compounds we actually want to compare.

Output:
  data/raw_trials.jsonl   one JSON study per line, tagged with _intervention
  data/trials.csv         flat parsed table used by every downstream script
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
API = "https://clinicaltrials.gov/api/v2/studies"

# label -> query.intr string. Labels are the names a buyer sees on a bottle /
# in a longevity stack; queries are the names a trial registry sees.
INTERVENTIONS = {
    "Creatine": "Creatine Monohydrate",
    "Magnesium": "Magnesium Supplement",
    "Ashwagandha": "Ashwagandha",
    "NMN": "Nicotinamide Mononucleotide",
    "Nicotinamide riboside": "Nicotinamide Riboside",
    "Resveratrol": "Resveratrol",
    "Melatonin": "Melatonin",
    "L-Theanine": "L-Theanine",
    "Omega-3": "Omega-3 Fatty Acids",
    "Vitamin D": "Vitamin D Supplement",
    "CoQ10": "Coenzyme Q10",
    "Berberine": "Berberine",
    "Lion's mane": "Hericium erinaceus",
    "Bacopa": "Bacopa monnieri",
    "Rhodiola": "Rhodiola rosea",
    "Glycine": "Glycine Supplement",
    "Tongkat ali": "Eurycoma longifolia",
    "Apigenin": "Apigenin",
    # Longevity-drug benchmarks: same biohacking conversation, different
    # regulatory universe. They are the control group for "does anyone
    # actually report results when a regulator is watching?"
    "Metformin (benchmark)": "Metformin",
    "Sirolimus/rapamycin (benchmark)": "Sirolimus",
}
MAX_PER_INTERVENTION = 4000


def fetch_intervention(label, query):
    # NOTE: requests.Session keep-alive hangs through this egress proxy
    # (see AGENTS.md MusicBrainz lesson) — fresh requests.get per page,
    # with retry/backoff, wins.
    studies, token, total = [], None, None
    while len(studies) < MAX_PER_INTERVENTION:
        params = {
            "query.intr": query,
            "pageSize": 100,
            "format": "json",
            "countTotal": "true",
        }
        if token:
            params["pageToken"] = token
        payload = None
        for attempt in range(4):
            try:
                r = requests.get(API, params=params, timeout=60)
                r.raise_for_status()
                payload = r.json()
                break
            except Exception as e:  # proxy drops, transient 5xx
                print(f"  retry {attempt+1} {label}: {e}", flush=True)
                time.sleep(2 * (attempt + 1))
        if payload is None:
            break
        if total is None:
            total = payload.get("totalCount", 0)
        batch = payload.get("studies", [])
        studies.extend(batch)
        token = payload.get("nextPageToken")
        if not token or not batch:
            break
        time.sleep(0.3)
    return studies[:MAX_PER_INTERVENTION], (total or len(studies))


def parse(study, label):
    p = study.get("protocolSection", {})
    ident = p.get("identificationModule", {})
    status = p.get("statusModule", {})
    sponsor = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    design = p.get("designModule", {})
    design_info = design.get("designInfo", {}) or {}
    enroll = design.get("enrollmentInfo", {}) or {}
    arms = p.get("armsInterventionsModule", {}) or {}
    locs = p.get("contactsLocationsModule", {}).get("locations", []) or []
    outcomes = p.get("outcomesModule", {}) or {}

    def _date(mod, key):
        d = (status.get(key) or {}).get("date")
        return d

    phases = design.get("phases") or []
    return {
        "intervention": label,
        "nct_id": ident.get("nctId"),
        "title": ident.get("briefTitle"),
        "overall_status": status.get("overallStatus"),
        "has_results": bool(study.get("hasResults")),
        "start_date": _date(status, "startDateStruct"),
        "primary_completion_date": _date(status, "primaryCompletionDateStruct"),
        "completion_date": _date(status, "completionDateStruct"),
        "first_post_date": (status.get("studyFirstPostDateStruct") or {}).get("date"),
        "last_update_date": (status.get("lastUpdatePostDateStruct") or {}).get("date"),
        "lead_sponsor_class": sponsor.get("class"),
        "lead_sponsor_name": sponsor.get("name"),
        "study_type": design.get("studyType"),
        "phases": "|".join(phases),
        "allocation": design_info.get("allocation"),
        "intervention_model": design_info.get("interventionModel"),
        "primary_purpose": design_info.get("primaryPurpose"),
        "masking": (design_info.get("maskingInfo") or {}).get("masking"),
        "enrollment_count": enroll.get("count"),
        "enrollment_type": enroll.get("type"),
        "n_locations": len(locs),
        "n_countries": len({(l.get("country") or "") for l in locs if l.get("country")}),
        "n_primary_outcomes": len(outcomes.get("primaryOutcomes") or []),
        "is_fda_regulated_drug": (p.get("oversightModule") or {}).get("isFdaRegulatedDrug"),
        "has_dmc": (p.get("oversightModule") or {}).get("oversightHasDmc"),
        "n_interventions_listed": len(arms.get("interventions") or []),
    }


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    rows, raw_path = [], DATA / "raw_trials.jsonl"
    totals = {}
    with raw_path.open("w") as fh:
        for label, query in INTERVENTIONS.items():
            studies, total = fetch_intervention(label, query)
            totals[label] = {"registry_total": int(total), "fetched": len(studies)}
            for s in studies:
                s["_intervention"] = label
                fh.write(json.dumps(s) + "\n")
                rows.append(parse(s, label))
            print(f"{label:38s} registry={total:6d} fetched={len(studies)}", flush=True)

    df = pd.DataFrame(rows)
    # A trial testing two stack ingredients appears under both queries.
    # For the trial-level model we keep the first tag; intervention-level
    # stats in 03_* use the full (un-deduped) counts from totals instead.
    dedup = df.sort_values("intervention").drop_duplicates("nct_id", keep="first")
    dedup.to_csv(DATA / "trials.csv", index=False)
    (DATA / "registry_totals.json").write_text(json.dumps(totals, indent=2))
    print(f"\nparsed={len(df)} unique_trials={len(dedup)} -> {DATA/'trials.csv'}")


if __name__ == "__main__":
    main()
