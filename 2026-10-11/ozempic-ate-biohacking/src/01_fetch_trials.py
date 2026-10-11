"""Fetch GLP-1 trials from ClinicalTrials.gov API v2 (no key required)."""
import requests, time, json, csv, pathlib
BASE = "https://clinicaltrials.gov/api/v2/studies"
MOLECULES = ["Semaglutide","Tirzepatide","Liraglutide","Dulaglutide","Exenatide","Retatrutide","Albiglutide","Lixisenatide"]
OUT = pathlib.Path(__file__).resolve().parents[1]/"data"
OUT.mkdir(parents=True, exist_ok=True)
seen = {}
for mol in MOLECULES:
    token = None; n=0
    while True:
        params = {"query.intr": mol, "pageSize": 1000, "format": "json"}
        if token: params["pageToken"]=token
        r = requests.get(BASE, params=params, timeout=60, headers={"User-Agent":"musing-with-mike research"})
        r.raise_for_status()
        j = r.json()
        for s in j.get("studies", []):
            p = s.get("protocolSection", {})
            ident = p.get("identificationModule", {})
            nct = ident.get("nctId","")
            if not nct: continue
            if nct in seen:
                if mol not in seen[nct]["molecules"]: seen[nct]["molecules"]+= "|"+mol
                continue
            status = p.get("statusModule", {})
            design = p.get("designModule", {})
            sponsor = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
            conds = p.get("conditionsModule", {}).get("conditions", [])
            intervs = p.get("armsInterventionsModule", {}).get("interventions", [])
            outcomes = p.get("outcomesModule", {}).get("primaryOutcomes", [])
            seen[nct] = {
                "nct_id": nct, "title": ident.get("briefTitle",""),
                "molecules": mol,
                "interventions": "|".join(sorted({i.get("name","") for i in intervs})),
                "conditions": "|".join(conds),
                "status": status.get("overallStatus",""),
                "start_date": (status.get("startDateStruct") or {}).get("date",""),
                "completion_date": (status.get("completionDateStruct") or {}).get("date",""),
                "phases": "|".join(design.get("phases", [])),
                "enrollment": (design.get("enrollmentInfo") or {}).get("count",""),
                "sponsor_name": sponsor.get("name",""), "sponsor_class": sponsor.get("class",""),
                "n_primary_outcomes": len(outcomes),
                "has_results": s.get("hasResults", False),
            }
            n+=1
        token = j.get("nextPageToken")
        print(mol, "batch", n, "total unique", len(seen), flush=True)
        if not token: break
        time.sleep(0.3)
rows = list(seen.values())
with open(OUT/"trials.csv","w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"Wrote {len(rows)} unique trials")
