"""OpenFDA adverse-event totals and top reactions per GLP-1 brand."""
import requests, json, pathlib, time
BRANDS = ["OZEMPIC","WEGOVY","MOUNJARO","ZEPBOUND","RYBELSUS","TRULICITY","VICTOZA","SAXENDA"]
OUT = pathlib.Path(__file__).resolve().parents[1]/"data"; OUT.mkdir(parents=True, exist_ok=True)
out={}
for b in BRANDS:
    entry={}
    for label, extra, count in [
        ("total", "", None),
        ("serious", "&search=patient.drug.medicinalproduct:\""+b+"\"+AND+serious:1", None),
    ]:
        pass
    # total
    base="https://api.fda.gov/drug/event.json"
    try:
        r=requests.get(base, params={"search":f'patient.drug.medicinalproduct:"{b}"',"limit":1}, timeout=30)
        entry["total_reports"]=r.json().get("meta",{}).get("results",{}).get("total","") if r.status_code==200 else ""
        r2=requests.get(base, params={"search":f'patient.drug.medicinalproduct:"{b}"',"count":"patient.reaction.reactionmeddrapt.exact","limit":15}, timeout=30)
        entry["top_reactions"]=[{"reaction":x["term"],"count":x["count"]} for x in r2.json().get("results",[])] if r2.status_code==200 else []
    except Exception as e:
        entry["error"]=str(e)
    out[b]=entry; print(b, entry.get("total_reports"), flush=True); time.sleep(0.5)
(OUT/"openfda.json").write_text(json.dumps(out, indent=2))
