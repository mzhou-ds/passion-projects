"""Fetch ClinicalTrials.gov v2 records for a panel of biohacking interventions.

For each search term we page through results (pageSize=100, cap 400 per term),
then keep only studies whose arms/interventions actually name the intervention
(word-boundary match on the intervention name, to drop e.g. 'creatinine
clearance' studies that a raw 'creatine' search sweeps in). Output is a slim
CSV: one row per study, with the registry's own healthy-volunteer flag,
age bounds, conditions, sponsor class, status and start year.

Source: ClinicalTrials.gov API v2 (public, no key). Fetched 2026-10-29.
"""
import csv
import json
import re
import time
from pathlib import Path

import requests

BASE = "https://clinicaltrials.gov/api/v2/studies"

# search term -> (label, category, match regex on intervention name)
PANEL = {
    "creatine": ("Creatine", "Performance", r"\bcreatine\b"),
    "cold water immersion": ("Cold water immersion", "Recovery", r"cold[- ]water immersion|cold exposure"),
    "sauna": ("Sauna", "Recovery", r"\bsauna\b"),
    "photobiomodulation": ("Photobiomodulation", "Recovery", r"photobiomodulation|low[- ]level (light|laser)"),
    "intermittent fasting": ("Intermittent fasting", "Metabolic", r"intermittent fasting"),
    "time restricted eating": ("Time-restricted eating", "Metabolic", r"time[- ]restricted (eating|feeding)"),
    "ketogenic diet": ("Ketogenic diet", "Metabolic", r"ketogenic diet|keto diet"),
    "rapamycin": ("Rapamycin", "Longevity drug", r"rapamycin|sirolimus"),
    "nicotinamide riboside": ("Nicotinamide riboside", "Longevity drug", r"nicotinamide riboside"),
    "nicotinamide mononucleotide": ("NMN", "Longevity drug", r"nicotinamide mononucleotide|\bNMN\b"),
    "ashwagandha": ("Ashwagandha", "Adaptogen", r"ashwagandha"),
    "methylene blue": ("Methylene blue", "Longevity drug", r"methylene blue"),
}

CAP_PER_TERM = 400


def parse_age(text):
    if not text:
        return None
    m = re.match(r"(\d+)", text.strip())
    return int(m.group(1)) if m else None


def fetch_term(term, label, category, pattern):
    rx = re.compile(pattern, re.IGNORECASE)
    rows, seen = [], set()
    page_token = None
    while len(rows) < CAP_PER_TERM:
        params = {"query.intr": term, "pageSize": 100, "format": "json"}
        if page_token:
            params["pageToken"] = page_token
        r = requests.get(BASE, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        for st in data.get("studies", []):
            ps = st.get("protocolSection", {})
            ident = ps.get("identificationModule", {})
            nct = ident.get("nctId")
            if not nct or nct in seen:
                continue
            arms = ps.get("armsInterventionsModule", {}).get("interventions", []) or []
            names = [a.get("name", "") for a in arms]
            if not any(rx.search(n) for n in names):
                continue  # search-term noise (e.g. creatinine, unrelated arms)
            seen.add(nct)
            elig = ps.get("eligibilityModule", {}) or {}
            design = ps.get("designModule", {}) or {}
            status = ps.get("statusModule", {}) or {}
            conds = ps.get("conditionsModule", {}).get("conditions", []) or []
            sponsor = ps.get("sponsorCollaboratorsModule", {}) or {}
            start = (status.get("startDateStruct") or {}).get("date", "")
            rows.append({
                "intervention": label, "category": category, "search_term": term,
                "nct_id": nct, "title": ident.get("briefTitle", ""),
                "overall_status": status.get("overallStatus", ""),
                "study_type": design.get("studyType", ""),
                "enrollment": (design.get("enrollmentInfo") or {}).get("count"),
                "healthy_volunteers": elig.get("healthyVolunteers"),
                "min_age": parse_age(elig.get("minimumAge")),
                "max_age": parse_age(elig.get("maximumAge")),
                "sex": elig.get("sex", ""),
                "std_ages": ";".join(elig.get("stdAges", []) or []),
                "conditions": "; ".join(conds),
                "n_conditions": len(conds),
                "sponsor_class": (sponsor.get("leadSponsor") or {}).get("class", ""),
                "start_year": start[:4] if start else "",
                "intervention_names": "; ".join(names),
            })
        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(0.2)
    return rows


def main():
    out = Path(__file__).resolve().parents[1] / "data" / "trials.csv"
    all_rows = []
    for term, (label, cat, pat) in PANEL.items():
        rows = fetch_term(term, label, cat, pat)
        print(f"{label}: kept {len(rows)} matched studies")
        all_rows.extend(rows)
        time.sleep(0.3)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)
    print(f"total {len(all_rows)} -> {out}")


if __name__ == "__main__":
    main()
