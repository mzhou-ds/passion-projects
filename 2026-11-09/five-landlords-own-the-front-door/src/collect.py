"""Collect DNS nameserver + HTTP CDN data for the Tranco top-1000 domains.

Sources: Tranco top-1m list (https://tranco-list.eu/top-1m.csv.zip, downloaded 2026-11-09).
DNS: NS records queried via dnspython against 1.1.1.1 / 8.8.8.8.
HTTP: response headers for the top 300 domains (CDN fingerprinting).
"""
import csv, json, re, sys, time, zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import dns.resolver
import requests

TOP_N = 1000
HTTP_N = 300
WORKERS = 20

PROVIDER_PATTERNS = [
    ("Cloudflare",      r"ns\.cloudflare\.com$"),
    ("AWS Route 53",    r"awsdns-\d+\.(com|net|org|co\.uk)$"),
    ("Google Cloud DNS",r"ns-cloud-[a-z]\d+\.googledomains\.com$"),
    ("GoDaddy",         r"domaincontrol\.com$"),
    ("Namecheap",       r"registrar-servers\.com$"),
    ("Akamai",          r"akam\.net$"),
    ("Azure DNS",      r"azure-dns\.(com|net|org|info)$"),
    ("CloudNS",         r"cloudns\.(net|org|com|club|pro)$"),
    ("DNS Made Easy",   r"dnsmadeeasy\.com$"),
    ("NS1",             r"nsone\.net$"),
    ("Oracle Dyn",      r"dynect\.net$"),
    ("UltraDNS",        r"ultradns\.(com|net|org|info|biz)$"),
    ("ClouDNS",         r"cloudns\."),
    ("DNSimple",        r"dnsimple\.com$"),
    ("NameSilo",        r"namesilo\.com$"),
    ("Hover/Tucows",    r"hover\.com$|tucows\.com$"),
    ("Squarespace",     r"squarespace\.com$|dns\d+\.p\d+\.nsone\.net$"),
    ("Wix",             r"wixdns\.net$"),
    ("Shopify",         r"shopify\.com$"),
    ("Alibaba Cloud",   r"alidns\.com$|hichina\.com$"),
    ("Tencent Cloud",   r"dnspod\.net$"),
    ("Baidu Cloud",     r"bdydns\.com$"),
    ("Yandex",          r"yandex\.net$"),
    ("OVHcloud",        r"ovh\.(net|ca)$"),
    ("Hetzner",         r"hetzner\.com$|your-server\.de$"),
    ("DigitalOcean",    r"digitalocean\.com$"),
    ("Linode/Akamai",   r"linode\.com$"),
    ("Vercel",          r"vercel-dns\.com$"),
    ("Netlify",         r"netlify\.com$"),
    ("Sucuri",          r"sucuri\.net$"),
    ("Constellix",      r"constellix\.com$"),
]

def classify_ns(host):
    host = host.rstrip(".").lower()
    for name, pat in PROVIDER_PATTERNS:
        if re.search(pat, host):
            return name
    return None

def main():
    zf = zipfile.ZipFile("data/tranco-top1m.zip")
    name = zf.namelist()[0]
    domains = []
    with zf.open(name) as f:
        reader = csv.reader(line.decode() for line in f)
        for rank, dom in reader:
            if int(rank) > TOP_N:
                break
            domains.append((int(rank), dom.strip()))

    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = ["1.1.1.1", "8.8.8.8"]
    resolver.lifetime = 6.0
    resolver.timeout = 3.0

    def query_ns(item):
        rank, dom = item
        try:
            ans = resolver.resolve(dom, "NS")
            nss = sorted(str(r).rstrip(".").lower() for r in ans)
            provs = [classify_ns(ns) or "other" for ns in nss]
            # majority provider; mixed if split
            main = max(set(provs), key=provs.count)
            mixed = len(set(provs)) > 1
            return {"rank": rank, "domain": dom, "ns": nss,
                    "providers": provs, "provider": main,
                    "mixed": mixed, "error": None}
        except Exception as e:
            return {"rank": rank, "domain": dom, "ns": [], "providers": [],
                    "provider": None, "mixed": False, "error": type(e).__name__}

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        ns_rows = list(ex.map(query_ns, domains))
    print(f"NS queries done in {time.time()-t0:.0f}s; errors: {sum(1 for r in ns_rows if r['error'])}")

    # HTTP headers for top HTTP_N domains (CDN fingerprinting)
    def cdn_from_headers(h):
        h = {k.lower(): v for k, v in h.items()}
        if "cf-ray" in h or "cf-cache-status" in h:
            return "Cloudflare"
        if "x-amz-cf-id" in h or "x-amz-cf-pop" in h:
            return "CloudFront (AWS)"
        if "x-akamai-transformed" in h or "akamai" in h.get("server", "").lower():
            return "Akamai"
        if "x-served-by" in h and "cache" in h.get("x-cache", "").lower():
            return "Fastly"
        if "x-fastly-request-id" in h:
            return "Fastly"
        if "x-vercel-id" in h or "x-vercel-cache" in h:
            return "Vercel"
        if "x-nf-request-id" in h:
            return "Netlify"
        if h.get("server", "").lower().startswith("gws"):
            return "Google"
        if "x-azure-ref" in h:
            return "Azure Front Door"
        if "x-sucuri-id" in h:
            return "Sucuri"
        return None

    sess = requests.Session()
    sess.headers.update({"User-Agent": "MusingWithMike-research/1.0 (academic measurement)"})

    def probe(item):
        rank, dom = item
        try:
            r = sess.get(f"https://{dom}", timeout=8, allow_redirects=True, stream=True)
            r.close()
            return {"rank": rank, "domain": dom, "status": r.status_code,
                    "cdn": cdn_from_headers(r.headers),
                    "server": r.headers.get("Server"),
                    "final_url": r.url, "error": None}
        except Exception as e:
            return {"rank": rank, "domain": dom, "status": None, "cdn": None,
                    "server": None, "final_url": None, "error": type(e).__name__}

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        http_rows = list(ex.map(probe, domains[:HTTP_N]))
    print(f"HTTP probes done in {time.time()-t0:.0f}s; errors: {sum(1 for r in http_rows if r['error'])}")

    out = {"date": str(date.today()), "source": "Tranco top-1m list (top 1000), downloaded 2026-11-09",
           "ns": ns_rows, "http": http_rows}
    with open("data/raw.json", "w") as f:
        json.dump(out, f, indent=1)
    print("wrote data/raw.json")

if __name__ == "__main__":
    main()
