# Working notes — Build #63

## Novelty case, stated before building
Everyone "knows" Cloudflare runs the internet. After the Nov 18, 2025 outage
took down X, ChatGPT and Spotify, the story was that a fifth of the web runs
through one company. But that is a traffic/CDN story. Nobody had published a
fresh, reproducible measurement of the DNS layer: who actually answers the
nameserver queries for the top 1,000 sites, and what happens if one of them
dies. DNS is the front door, and the front door has different landlords than
the hallway. The bet was that the ranking would invert the folk wisdom, and it
did: Cloudflare is nearly absent from the top 100.

## Data collection notes
- Tranco top-1m list downloaded 2026-11-09, top 1,000 taken.
- UDP/53 is blocked on this host (dig returns REFUSED), so NS records were
  fetched over DNS-over-HTTPS (dns.google primary, cloudflare-dns.com
  fallback), 10 workers, two slow retry passes. 990/1000 resolved.
- HTTP header probes for the top 300: 188/300 reachable. Fail rate roughly
  uniform across DNS providers, so CDN shares are not badly biased by operator.
- 10 domains unresolved: 3 are Tranco artifacts (w2rt6byl5nf1opmc-a.com,
  www.gov.uk, resolver.arpa); 7 real domains failed DoH after 3 attempts.
- One earlier exec session died mid-write during the HTTP retry; the retry
  had already persisted, verified by re-reading raw.json (errors 143 -> 112).
- /tmp is wiped between turns on this host: venv and Tranco zip live in the
  project dir / ~/workspace, not /tmp.

## Classifier v2 lessons
- Google Cloud DNS uses both ns-cloud-*.googledomains.com and
  ns1-4.googledomains.com; match the whole zone.
- Akamai's DNS zones are akam.net, akamaitech.net, akamaistream.net,
  akamaiedge.net, akagtm.org, akadns.net. One pattern misses half of Akamai.
- Same-company zones across TLDs (roblox.com -> roblox.net/.us/.co.uk) count
  as self-hosted; etld1 needs a small public-suffix list (co.uk, co.kr...).
- "Mixed" NS sets are mostly deliberate secondary DNS (GitHub: NS1 + Route
  53; LinkedIn/Bing: NS1 + Azure; Spotify: NS1 + Google Cloud DNS), not noise.
