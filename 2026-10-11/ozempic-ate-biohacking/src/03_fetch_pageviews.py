"""Monthly Wikipedia pageviews via Wikimedia REST API."""
import requests, csv, pathlib, urllib.parse
ARTICLES = ["Ozempic","Wegovy","Mounjaro","Zepbound","Semaglutide","Tirzepatide","Rybelsus","Trulicity"]
OUT = pathlib.Path(__file__).resolve().parents[1]/"data"; OUT.mkdir(parents=True, exist_ok=True)
rows=[]
for art in ARTICLES:
    url=f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{urllib.parse.quote(art,safe='')}/monthly/2019010100/2026100100"
    r=requests.get(url, timeout=30, headers={"User-Agent":"musing-with-mike research (daily build)"})
    if r.status_code!=200:
        print(art, r.status_code); continue
    for it in r.json().get("items", []):
        rows.append({"article":art,"month":it["timestamp"][:6],"views":it["views"]})
    print(art, "ok", flush=True)
with open(OUT/"pageviews_monthly.csv","w",newline="") as f:
    w=csv.DictWriter(f, fieldnames=["article","month","views"]); w.writeheader(); w.writerows(rows)
