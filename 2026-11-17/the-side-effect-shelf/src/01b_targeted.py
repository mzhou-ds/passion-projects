#!/usr/bin/env python3
"""Build #71 — targeted follow-ups.
1. What share of ALL serotonin-syndrome reports in FAERS name methylene blue?
2. Per-compound counts for liver-injury reactions, drug interactions,
   and serotonin syndrome (top-15 lists miss these when they rank below 15).
Appends into data/faers_summary.json and the per-compound raw files.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"

LIVER_TERMS = ["DRUG-INDUCED LIVER INJURY", "HEPATOTOXICITY", "HEPATITIS",
               "LIVER INJURY", "HEPATIC FAILURE", "HEPATOCELLULAR INJURY",
               "CHOLESTASIS", "JAUNDICE"]
SHELF = ["berberine", "methylene blue", "quercetin", "resveratrol", "DHEA",
         "ashwagandha", "pregnenolone", "taurine", "creatine", "lithium orotate",
         "BPC-157", "nicotinamide riboside"]


def get_json(url, tries=4):
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
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last


def total(search):
    url = ("https://api.fda.gov/drug/event.json?search="
           + urllib.parse.quote(search) + "&limit=1")
    return get_json(url)["meta"]["results"]["total"]


def main():
    summary = json.loads((BASE / "data" / "faers_summary.json").read_text())

    # 1. all serotonin-syndrome reports, any suspect drug
    all_ss = total('patient.reaction.reactionmeddrapt:"SEROTONIN SYNDROME" '
                   'AND patient.drug.drugcharacterization:1')
    print("all serotonin-syndrome suspect reports:", all_ss)

    # 2. per-compound themed counts
    for label in SHELF:
        rec = summary[label]
        names = rec["faers_names"]
        q_any = " OR ".join(f'patient.drug.medicinalproduct:"{n}"' for n in names)
        q_sus = f"({q_any}) AND patient.drug.drugcharacterization:1"
        liver_q = " OR ".join(f'patient.reaction.reactionmeddrapt:"{t}"' for t in LIVER_TERMS)
        rec["liver_reaction_reports"] = total(f"{q_sus} AND ({liver_q})")
        time.sleep(0.3)
        rec["drug_interaction_reports"] = total(
            f'{q_sus} AND patient.reaction.reactionmeddrapt:"DRUG INTERACTION"')
        time.sleep(0.3)
        rec["serotonin_syndrome_reports"] = total(
            f'{q_sus} AND patient.reaction.reactionmeddrapt:"SEROTONIN SYNDROME"')
        time.sleep(0.3)
        slug = label.lower().replace(" ", "_").replace("+", "plus")
        (RAW / f"{slug}.json").write_text(json.dumps(rec, indent=2))
        print(f"{label:22s} liver={rec['liver_reaction_reports']:4d} "
              f"interaction={rec['drug_interaction_reports']:4d} "
              f"serotonin={rec['serotonin_syndrome_reports']:4d}", flush=True)

    summary["_meta"] = {"all_serotonin_syndrome_suspect_reports": all_ss}
    (BASE / "data" / "faers_summary.json").write_text(json.dumps(summary, indent=2))
    print("done")


if __name__ == "__main__":
    main()
