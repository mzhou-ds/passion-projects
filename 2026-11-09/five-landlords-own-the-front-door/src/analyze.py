"""Operator-level analysis of DNS + CDN concentration across the Tranco top 1000.

Classifier v2 (operator of the NS zone, not the product name):
  - Google Cloud DNS + google.com + zdns.google roll up into 'Google'
  - Akamai covers akam.net / akamaitech.net / akamaistream.net / akamaiedge.net
  - NS under the site's own domain = 'Self-hosted'
  - Remaining NS zones are grouped by their parent domain ('Other: <zone>')
"""
import json, re
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False})

PATTERNS = [
    ("Cloudflare",      r"\.cloudflare\.com$"),
    ("AWS Route 53",    r"\.awsdns-\d+\.(com|net|org|co\.uk)$"),
    ("Google",          r"\.googledomains\.com$|\.google\.com$|\.zdns\.google$"),
    ("Akamai",          r"\.akam\.net$|\.akamaitech\.net$|\.akamaistream\.net$|\.akamaiedge\.net$|\.akagtm\.org$|\.akadns\.net$"),
    ("Azure DNS",      r"\.dns-tm\.com$|\.edgedns-tm\.info$"),
    ("NS1",             r"\.nsone\.net$"),
    ("Azure DNS",      r"\.azure-dns\.(com|net|org|info)$"),
    ("GoDaddy",         r"\.domaincontrol\.com$"),
    ("Namecheap",       r"\.registrar-servers\.com$"),
    ("Alibaba Cloud",   r"\.alidns\.com$|\.hichina\.com$|\.aliyun\.com$"),
    ("Tencent Cloud",   r"\.dnspod\.net$"),
    ("Oracle Dyn",      r"\.dynect\.net$"),
    ("UltraDNS",        r"\.ultradns\.(com|net|org|info|biz)$"),
    ("DNS Made Easy",   r"\.dnsmadeeasy\.com$"),
    ("ClouDNS",         r"\.cloudns\.(net|org|com|club|pro)$"),
    ("DNSimple",        r"\.dnsimple\.com$|\.dnsimple-edge\.(net|org)$"),
    ("Gandi",           r"\.gandi\.net$"),
    ("OVHcloud",        r"\.ovh\.(net|ca)$"),
    ("Hetzner",         r"\.hetzner\.com$|\.your-server\.de$"),
    ("DigitalOcean",    r"\.digitalocean\.com$"),
    ("Vercel",          r"\.vercel-dns\.com$"),
    ("Netlify",         r"\.netlify\.com$"),
    ("Wix",             r"\.wixdns\.net$"),
    ("Shopify",         r"\.shopify\.com$"),
    ("Yandex",          r"\.yandex\.net$"),
    ("RU-CENTER",       r"\.nic\.ru$"),
    ("Sucuri",          r"\.sucuri\.net$"),
    ("Constellix",      r"\.constellix\.com$"),
    ("Baidu Cloud",     r"\.bdydns\.com$"),
    ("NameSilo",        r"\.namesilo\.com$"),
]

PUBLIC_SUFFIXES = {"co.uk", "co.kr", "com.au", "co.jp", "com.br", "co.nz", "co.za",
                   "com.cn", "org.uk", "net.uk", "co.in", "com.mx", "co.id", "com.tr",
                   "com.tw", "org.au", "co.il", "com.ar", "com.pl", "co.th"}

def etld1(host):
    host = host.rstrip(".").lower()
    for suf in PUBLIC_SUFFIXES:
        if host.endswith("." + suf):
            rest = host[: -len(suf) - 1].split(".")
            return rest[-1] + "." + suf
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host

def classify_ns(ns, site):
    ns = ns.lower()
    for name, pat in PATTERNS:
        if re.search(pat, ns):
            return name
    if etld1(ns) == etld1(site):
        return "Self-hosted"
    # same company, different TLD (roblox.com -> roblox.net / roblox.co.uk)
    if etld1(ns).split(".")[0] == etld1(site).split(".")[0]:
        return "Self-hosted"
    return f"Other: {etld1(ns)}"

def domain_operator(row):
    ops = [classify_ns(ns, row["domain"]) for ns in row["ns"]]
    if not ops:
        return None, ops
    main = Counter(ops).most_common(1)[0][0]
    return main, ops

def main():
    raw = json.load(open("data/raw.json"))
    ns_rows = [r for r in raw["ns"] if not r["error"] and r["ns"]]
    print(f"NS resolved: {len(ns_rows)}/1000")

    # ---- operator rollup ----
    ops = {}
    for r in ns_rows:
        op, _ = domain_operator(r)
        ops[r["domain"]] = op
    counts = Counter(ops.values())
    n = len(ops)
    print("\nOperator shares (top 1000):")
    for op, c in counts.most_common(20):
        print(f"  {op}: {c} ({c/n:.1%})")

    # collapse 'Other: X' into long tail
    def top_op(op):
        return op if not op.startswith("Other:") else "Other (long tail)"
    top_counts = Counter(top_op(o) for o in ops.values())
    other_zones = Counter(o for o in ops.values() if o.startswith("Other:"))
    self_hosted = sum(1 for o in ops.values() if o == "Self-hosted")
    print(f"\nDistinct 'Other' zones: {len(other_zones)}; self-hosted domains: {self_hosted}")
    print("Top other zones:", other_zones.most_common(12))

    # HHI + effective number (operator level, Other: X kept separate)
    shares = [c / n for c in counts.values()]
    hhi = sum(s * s for s in shares)
    print(f"\nHHI (operator level): {hhi:.4f}  -> effective # operators: {1/hhi:.1f}")
    top3 = sum(c for _, c in counts.most_common(3)) / n
    top5 = sum(c for _, c in counts.most_common(5)) / n
    print(f"Top-3 operators: {top3:.1%}   Top-5: {top5:.1%}")

    # ---- tier split ----
    def tier(rank):
        return "Top 100" if rank <= 100 else ("101-500" if rank <= 500 else "501-1000")
    tier_counts = defaultdict(Counter)
    tier_n = Counter()
    for r in ns_rows:
        tier_counts[tier(r["rank"])][top_op(ops[r["domain"]])] += 1
        tier_n[tier(r["rank"])] += 1
    print("\nTier split (share of tier):")
    for t in ["Top 100", "101-500", "501-1000"]:
        print(f"  {t} (n={tier_n[t]}): " +
              ", ".join(f"{op} {c/tier_n[t]:.0%}" for op, c in tier_counts[t].most_common(6)))

    # self-hosted by tier
    for t in ["Top 100", "101-500", "501-1000"]:
        sh = sum(1 for r in ns_rows if tier(r["rank"]) == t and ops[r["domain"]] == "Self-hosted")
        print(f"  Self-hosted in {t}: {sh}/{tier_n[t]} = {sh/tier_n[t]:.0%}")

    # single-operator dependence + mixed
    mixed = sum(1 for r in ns_rows if len(set(domain_operator(r)[1])) > 1)
    print(f"\nMixed-operator domains (NS split across operators): {mixed}/{n}")
    single = sum(1 for r in ns_rows if len(set(domain_operator(r)[1])) == 1)
    print(f"All NS under one operator: {single}/{n} = {single/n:.1%}")

    # ---- CDN layer (top 300, reachable only) ----
    http_ok = [r for r in raw["http"] if not r["error"]]
    print(f"\nHTTP reachable: {len(http_ok)}/300")
    cdn_counts = Counter(r["cdn"] or "None detected" for r in http_ok)
    print("CDN shares (reachable top-300):")
    for c, k in cdn_counts.most_common():
        print(f"  {c}: {k} ({k/len(http_ok):.1%})")
    any_cdn = sum(1 for r in http_ok if r["cdn"])
    print(f"Any CDN detected: {any_cdn}/{len(http_ok)} = {any_cdn/len(http_ok):.1%}")

    # DNS->CDN coupling
    cf_dns = [r for r in http_ok if ops.get(r["domain"]) == "Cloudflare"]
    cf_both = sum(1 for r in cf_dns if r["cdn"] == "Cloudflare")
    print(f"Cloudflare-DNS sites also on Cloudflare CDN: {cf_both}/{len(cf_dns)}")
    aws_dns = [r for r in http_ok if ops.get(r["domain"]) == "AWS Route 53"]
    aws_both = sum(1 for r in aws_dns if r["cdn"] == "CloudFront (AWS)")
    print(f"Route53 sites also on CloudFront: {aws_both}/{len(aws_dns)}")
    cf_cdn_total = sum(1 for r in http_ok if r["cdn"] == "Cloudflare")
    cf_cdn_not_dns = sum(1 for r in http_ok if r["cdn"] == "Cloudflare" and ops.get(r["domain"]) != "Cloudflare")
    print(f"Cloudflare CDN total: {cf_cdn_total}, of which DNS is NOT Cloudflare: {cf_cdn_not_dns}")

    # who are the top-100's landlords
    print("\nTop-100 DNS operators:")
    t100 = Counter(ops[r["domain"]] for r in ns_rows if r["rank"] <= 100)
    for op, c in t100.most_common(12):
        print(f"  {op}: {c}")

    summary = {
        "n_ns_resolved": len(ns_rows),
        "operator_counts": dict(counts.most_common()),
        "top_counts": dict(top_counts.most_common()),
        "distinct_other_zones": len(other_zones),
        "other_zones_top": other_zones.most_common(12),
        "self_hosted": self_hosted,
        "hhi": round(hhi, 4),
        "effective_operators": round(1 / hhi, 1),
        "top3_share": round(top3, 4),
        "top5_share": round(top5, 4),
        "tier_counts": {t: dict(tier_counts[t].most_common(8)) for t in tier_counts},
        "tier_n": dict(tier_n),
        "mixed_operator_domains": mixed,
        "single_operator_domains": single,
        "http_reachable": len(http_ok),
        "cdn_counts": dict(cdn_counts.most_common()),
        "any_cdn_share": round(any_cdn / len(http_ok), 4),
        "cloudflare_dns_and_cdn": [cf_both, len(cf_dns)],
        "route53_and_cloudfront": [aws_both, len(aws_dns)],
        "cloudflare_cdn_total": cf_cdn_total,
        "cloudflare_cdn_not_dns": cf_cdn_not_dns,
        "top100_operators": dict(t100.most_common(12)),
    }
    json.dump(summary, open("data/summary.json", "w"), indent=1)
    # per-domain table for the explorer
    http_map = {r["domain"]: r for r in raw["http"]}
    rows = []
    for r in sorted(ns_rows, key=lambda x: x["rank"]):
        h = http_map.get(r["domain"], {})
        rows.append({"rank": r["rank"], "domain": r["domain"],
                     "dns_operator": ops[r["domain"]],
                     "ns": r["ns"], "cdn": h.get("cdn"),
                     "http_status": h.get("status")})
    json.dump(rows, open("data/dns_by_domain.json", "w"), indent=1)
    print("\nwrote data/summary.json, data/dns_by_domain.json")

if __name__ == "__main__":
    main()
