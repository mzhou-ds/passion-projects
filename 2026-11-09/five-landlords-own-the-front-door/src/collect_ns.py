"""NS records for Tranco top-1000 via DNS-over-HTTPS (UDP/53 is blocked on this host).

Primary: Google DNS JSON API (https://dns.google/resolve), fallback: Cloudflare DoH JSON.
Rate: 10 workers, ~1000 queries total. Preserves the provider classifier from collect.py.
"""
import csv, json, sys, time, zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import requests

sys.path.insert(0, "src")
from collect import classify_ns, PROVIDER_PATTERNS  # noqa: E402

TOP_N = 1000
WORKERS = 10

def query_ns(session, dom):
    for base in ("https://dns.google/resolve", "https://cloudflare-dns.com/dns-query"):
        try:
            r = session.get(base, params={"name": dom, "type": "NS"},
                            headers={"accept": "application/dns-json"}, timeout=15)
            j = r.json()
            if j.get("Status") == 0 and j.get("Answer"):
                return sorted(a["data"].rstrip(".").lower() for a in j["Answer"]
                              if a.get("type") == 2)
            if j.get("Status") == 3:  # NXDOMAIN
                return []
        except Exception:
            continue
    return None

def main():
    zf = zipfile.ZipFile("data/tranco-top1m.zip")
    domains = []
    with zf.open(zf.namelist()[0]) as f:
        reader = csv.reader(line.decode() for line in f)
        for rank, dom in reader:
            if int(rank) > TOP_N:
                break
            domains.append((int(rank), dom.strip()))

    sess = requests.Session()
    sess.headers.update({"User-Agent": "MusingWithMike-research/1.0 (academic measurement)"})

    def one(item):
        rank, dom = item
        nss = query_ns(sess, dom)
        if nss is None:
            return {"rank": rank, "domain": dom, "ns": [], "providers": [],
                    "provider": None, "mixed": False, "error": "DoHFailed"}
        provs = [classify_ns(ns) or "other" for ns in nss]
        main = max(set(provs), key=provs.count) if provs else None
        return {"rank": rank, "domain": dom, "ns": nss, "providers": provs,
                "provider": main, "mixed": len(set(provs)) > 1, "error": None}

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        rows = list(ex.map(one, domains))
    print(f"NS via DoH done in {time.time()-t0:.0f}s; errors: {sum(1 for r in rows if r['error'])}")
    print(f"empty NS (NXDOMAIN/no NS): {sum(1 for r in rows if not r['ns'] and not r['error'])}")

    raw = json.load(open("data/raw.json"))
    raw["ns"] = rows
    raw["ns_method"] = "DNS-over-HTTPS (dns.google primary, cloudflare-dns.com fallback); UDP/53 blocked on host"
    json.dump(raw, open("data/raw.json", "w"), indent=1)
    print("updated data/raw.json")

if __name__ == "__main__":
    main()
