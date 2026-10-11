"""Yearly PubMed counts per molecule via NCBI E-utilities."""
import requests, time, csv, pathlib
TERMS = {"semaglutide":"semaglutide","tirzepatide":"tirzepatide","liraglutide":"liraglutide","dulaglutide":"dulaglutide","exenatide":"exenatide","retatrutide":"retatrutide","metformin_benchmark":"metformin","creatine_benchmark":"creatine"}
OUT = pathlib.Path(__file__).resolve().parents[1]/"data"; OUT.mkdir(parents=True, exist_ok=True)
rows=[]
for label, term in TERMS.items():
    for year in range(2010, 2027):
        url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params={"db":"pubmed","term":f'"{term}"[tiab] AND {year}[dp]',"retmode":"json","retmax":0}
        r=requests.get(url, params=params, timeout=30, headers={"User-Agent":"musing-with-mike research"})
        cnt = r.json()["esearchresult"]["count"] if r.status_code==200 else ""
        rows.append({"term":label,"year":year,"pubmed_count":cnt}); print(label, year, cnt, flush=True)
        time.sleep(0.4)
with open(OUT/"pubmed_yearly.csv","w",newline="") as f:
    w=csv.DictWriter(f, fieldnames=["term","year","pubmed_count"]); w.writeheader(); w.writerows(rows)
