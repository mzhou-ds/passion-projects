#!/usr/bin/env python3
"""Build #71 — The Side-Effect Shelf.
Analysis: turn data/faers_summary.json into derived metrics and flat tables.
Writes output/results.json, data/compound_table.csv, data/trend_table.csv.
"""
import json
import math
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
OUT = BASE / "output"
OUT.mkdir(parents=True, exist_ok=True)

QUAL_LABELS = {"1": "physician", "2": "pharmacist", "3": "other_health_prof",
               "4": "lawyer", "5": "consumer"}

# reaction terms grouped into safety themes (MedDRA preferred terms, uppercase)
THEMES = {
    "liver": ["DRUG-INDUCED LIVER INJURY", "HEPATOTOXICITY", "HEPATITIS",
              "LIVER INJURY", "HEPATIC FAILURE", "ALANINE AMINOTRANSFERASE INCREASED",
              "ASPARTATE AMINOTRANSFERASE INCREASED", "JAUNDICE", "HEPATOCELLULAR INJURY",
              "CHOLESTASIS", "BLOOD BILIRUBIN INCREASED", "LIVER FUNCTION TEST ABNORMAL"],
    "serotonin_syndrome": ["SEROTONIN SYNDROME"],
    "kidney": ["ACUTE KIDNEY INJURY", "RENAL FAILURE", "RENAL INJURY",
               "BLOOD CREATININE INCREASED", "RENAL IMPAIRMENT"],
    "cardiac": ["MYOCARDIAL INFARCTION", "CARDIAC ARREST", "ARRHYTHMIA",
                "PALPITATIONS", "TACHYCARDIA", "BRADYCARDIA",
                "QT PROLONGATION", "ELECTROCARDIOGRAM QT PROLONGED"],
    "interaction": ["DRUG INTERACTION"],
    "ineffective": ["DRUG INEFFECTIVE"],
}


def theme_counts(reactions):
    out = {}
    for theme, terms in THEMES.items():
        out[theme] = sum(r["count"] for r in reactions if r["term"] in terms)
    return out


def main():
    summary = json.loads((DATA / "faers_summary.json").read_text())
    rows = []
    trend_rows = []
    for label, rec in summary.items():
        if label.startswith("_"):
            continue
        tot = rec["total_suspect"]
        qual = {QUAL_LABELS.get(str(r["term"]), str(r["term"])): r["count"]
                for r in rec.get("reporter_qualification", [])}
        n_qual = sum(qual.values()) or 1
        row = {
            "compound": label,
            "group": rec["group"],
            "reports_any_role": rec["total_any_role"],
            "reports_suspect": tot,
            "serious": rec["serious"],
            "serious_share": rec["serious"] / tot if tot else None,
            "deaths": rec["deaths"],
            "death_share": rec["deaths"] / tot if tot else None,
            "hospitalizations": rec["hospitalizations"],
            "hosp_share": rec["hospitalizations"] / tot if tot else None,
            "life_threatening": rec["life_threatening"],
            "disability": rec["disability"],
            "consumer_share": qual.get("consumer", 0) / n_qual,
            "physician_share": qual.get("physician", 0) / n_qual,
            "trials_registered": rec["trials_registered"],
            "pubmed_rcts": rec["pubmed_rcts"],
            "reports_per_rct": (tot / rec["pubmed_rcts"]) if rec["pubmed_rcts"] else None,
            "reports_per_trial": (tot / rec["trials_registered"]) if rec["trials_registered"] else None,
            "top_reaction": rec["top_reactions"][0]["term"] if rec.get("top_reactions") else None,
            "top_reaction_n": rec["top_reactions"][0]["count"] if rec.get("top_reactions") else None,
        }
        row.update({f"theme_{k}": v for k, v in theme_counts(rec.get("top_reactions", [])).items()})
        # direct-search themed counts (01b_targeted.py); fall back to top-15 counts
        for k in ("liver_reaction_reports", "drug_interaction_reports",
                  "serotonin_syndrome_reports"):
            row[k] = rec.get(k)
        rows.append(row)
        for y, n in rec.get("trend", {}).items():
            trend_rows.append({"compound": label, "group": rec["group"], "year": int(y), "reports": n})

    df = pd.DataFrame(rows)
    df.to_csv(DATA / "compound_table.csv", index=False)
    tdf = pd.DataFrame(trend_rows)
    if not tdf.empty:
        tdf.to_csv(DATA / "trend_table.csv", index=False)

    # shelf-level aggregates
    shelf = df[df.group == "shelf"]
    ctrl = df[df.group == "control"]
    pharma = df[df.group == "pharma"]
    results = {
        "shelf_total_reports": int(shelf.reports_suspect.sum()),
        "shelf_total_serious": int(shelf.serious.sum()),
        "shelf_total_deaths": int(shelf.deaths.sum()),
        "shelf_serious_share": float(shelf.serious.sum() / shelf.reports_suspect.sum()),
        "control_serious_share": float(ctrl.serious.sum() / ctrl.reports_suspect.sum()),
        "pharma_serious_share": float(pharma.serious.sum() / pharma.reports_suspect.sum()),
        "shelf_reports_per_rct": float(
            shelf.reports_suspect.sum() / shelf.pubmed_rcts.sum()),
        "control_reports_per_rct": float(
            ctrl.reports_suspect.sum() / ctrl.pubmed_rcts.sum()),
        "all_serotonin_syndrome_reports": summary.get("_meta", {}).get(
            "all_serotonin_syndrome_suspect_reports"),
        "compounds": df.to_dict("records"),
    }
    # methylene blue's share of every serotonin-syndrome report in FAERS
    mb = df[df.compound == "methylene blue"].iloc[0]
    results["mb_serotonin_share_of_all"] = float(
        mb["serotonin_syndrome_reports"] / results["all_serotonin_syndrome_reports"])
    results["mb_serotonin_share_of_own"] = float(
        mb["serotonin_syndrome_reports"] / mb["reports_suspect"])
    # FAERS-wide baseline, fetched 2026-11-17 (all reports by receipt year):
    # 2012: 551,378; 2015: 1,223,001; 2020: 1,421,775; 2025: 1,386,644.
    # The whole database grew 2.5x from 2012 to 2025; compound growth above
    # that is growth in the compound's own reporting, not database growth.
    results["faers_total_2012"] = 551378
    results["faers_total_2025"] = 1386644
    results["faers_growth_x_2012_2025"] = 1386644 / 551378
    if not tdf.empty:
        for comp in ["berberine", "quercetin", "methylene blue", "creatine",
                     "melatonin", "caffeine"]:
            sub = tdf[tdf.compound == comp].set_index("year")["reports"]
            if 2012 in sub.index and 2025 in sub.index:
                results[f"trend_{comp.replace(' ', '_')}_2012"] = int(sub.loc[2012])
                results[f"trend_{comp.replace(' ', '_')}_2025"] = int(sub.loc[2025])
                results[f"trend_{comp.replace(' ', '_')}_growth_x"] = float(
                    sub.loc[2025] / max(sub.loc[2012], 1))
                results[f"trend_{comp.replace(' ', '_')}_cagr"] = float(
                    (sub.loc[2025] / max(sub.loc[2012], 1)) ** (1 / 13) - 1)
    (OUT / "results.json").write_text(json.dumps(
        results, indent=2, default=str).replace(": NaN", ": null"))

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print(df[["compound", "group", "reports_suspect", "serious_share", "deaths",
              "consumer_share", "trials_registered", "pubmed_rcts",
              "reports_per_rct"]].sort_values("reports_suspect", ascending=False).to_string(index=False))
    print()
    print("shelf totals: reports", results["shelf_total_reports"],
          "serious share", round(results["shelf_serious_share"], 3),
          "deaths", results["shelf_total_deaths"])
    print("control serious share", round(results["control_serious_share"], 3),
          "| pharma serious share", round(results["pharma_serious_share"], 3))
    print("reports per RCT — shelf:", round(results["shelf_reports_per_rct"], 1),
          "control:", round(results["control_reports_per_rct"], 1))
    print()
    print("theme counts (top-15 reactions only):")
    print(df[["compound"] + [f"theme_{k}" for k in THEMES]].to_string(index=False))


if __name__ == "__main__":
    main()
