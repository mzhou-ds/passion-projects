# Data sources

All data pulled 2026-09-22. Everything is reproducible with the scripts in `src/`.

## 1. Wikipedia pageviews — public attention (the "hype" side)
- **Source:** Wikimedia Pageviews REST API (`wikimedia.org/api/rest_v1/`), no auth.
  Monthly per-article views, en.wikipedia, all-access, 2020-01 → 2026-08
  (September 2026 dropped — partial month).
- **Method:** 15 biohacks mapped to their Wikipedia articles
  (e.g. cold plunge → "Ice bath", NMN → "Nicotinamide mononucleotide",
  zone 2 → "Aerobic exercise"); raw monthly view counts, directly comparable
  across terms since it's one corpus. See `src/01_fetch_pageviews.py`.
- **Outputs:** `data/pageviews_monthly.csv`, `data/attention_summary.json`.
- **Why not Google Trends:** tried first — the shared egress IP is rate-limited
  by Google (HTTP 429 on the explore endpoint, no retry per policy), and the
  GDELT API host is unreachable from this network. Pageviews are arguably the
  better proxy anyway: documented, stable, and absolute (not normalized).
- **Caveats:** Wikipedia skews informational — TikTok-native fads under-register
  relative to their cultural footprint. "Mouth taping" article was created in
  2023 (36 months of data); "sleepmaxxing" has no article at all. Metformin's
  37k monthly views are mostly diabetes patients, not biohackers — its
  mispricing rank is inflated by that. "Magnesium in biology" and
  "Aerobic exercise" capture broader readership than the supplement / zone-2
  niches alone.

## 2. PubMed — research attention (the "supply" side)
- **Source:** NCBI E-utilities `esearch.fcgi` (no key, ≤3 req/s respected).
  Quoted-phrase queries per biohack, counts only (`retmax=0`), per publication
  year 2020–2026. See `src/02_fetch_pubmed.py` for exact queries.
- **Outputs:** `data/pubmed_yearly.csv`.
- **Caveats:** phrase queries are approximations; "metformin" sweeps in the
  entire diabetes literature (19,127 papers — the query is intentionally broad
  there); 2026 is a partial year.

## 3. ClinicalTrials.gov — evidence depth
- **Source:** registered-trial counts from the companion build
  [`2026-09-13/biohacking-evidence-audit`](../../2026-09-13/biohacking-evidence-audit/),
  which queried the ClinicalTrials.gov API v2 for 15 biohack terms.
- **Mapping:** 14 of 16 Trends keywords map to an audited term
  (see `TREND_TO_EVIDENCE` in `src/03_merge_evidence.py`). "Mouth tape" and
  "sleepmaxxing" have ~zero registered trials — pure-hype controls.
- **Caveats:** keyword-based counts are upper bounds; registration ≠ publication
  (see the audit's README).

## 4. Derived
- **Mispricing score:** `z(log attention) − z(log(1 + trials))` — positive means
  public attention outruns the registered-trial record.
- **Segments:** quadrants split on median attention × median trial volume
  (k-means was tried first; with n=15 it collapses to one big cluster plus
  singletons, so quadrants are the honest segmentation).
- **Outputs:** `data/hype_evidence.csv`, `data/segments.json`, `charts/*.png`.
