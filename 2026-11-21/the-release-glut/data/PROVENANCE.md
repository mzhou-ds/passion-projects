# Provenance

## Sources

**Discogs API** (`https://api.discogs.com/database/search`), accessed 2026-11-21
via unauthenticated requests (User-Agent `MusingWithMike/1.0`), paced at
~1 request / 1.2s, within the public 60/min limit. No token used.
- `data/raw/discogs_counts.json` — release counts by genre x year, 2005-2026,
  for Electronic, Rock, Hip Hop, Pop (`type=release`, `per_page=1`, total read
  from `pagination.items`). Fetched by `src/01_fetch_counts.py`.
- `data/raw/sample_*.json` — stratified random samples of releases for
  electronic 2005/2015/2025 (rock/pop control samples were dropped; see
  "Sampling design").
- `data/raw/style_totals.json` — electronic style totals per year (probe,
  23 styles, 2005/2020).
- `data/format_totals.csv` — population format totals (Vinyl/File/CD/CDr/
  Cassette/DVD) for electronic, 2005/2015/2020/2021-2025, from the same API.

**Beatport Top 100** (`https://www.beatport.com/top-100`), snapshot 2026-11-21.
- `data/raw/beatport_top100_2026-11-21.csv` — rank, title, release date, BPM,
  key, length for all 100 tracks, transcribed from the page text fetched
  2026-11-21 05:09 UTC. Artist, label and genre columns are NOT in the
  fetched text and were not used; the Beatport module therefore covers only
  BPM / key / length / age. Direct curl access to beatport.com returns 403.

## Sampling design (Discogs)

Discogs search caps accessible results at 10,000 per query, and its default
ordering is popularity-graded (median `have` falls 74 -> 13 -> 7 from page 1
to page 100 of electronic/2005), so naive paging is capped and biased.
Each (genre, year) cohort is therefore partitioned into leaf cells by
recursive splitting (style -> format -> file-description -> country) until
every cell total is <= 10,000, and one uniformly random page (100 records)
is drawn per cell. A record's inclusion probability is computed exactly from
the leaf cells whose filters it matches (a record lists all its styles, formats
and descriptions, so membership is observable), giving Horvitz-Thompson
weights for population estimates. Records are deduplicated by id within a
cohort.

Style matching is hierarchy-aware: Discogs style search returns a style
OR its sub-styles (style=House returns Deep House, Electro House, ...).
Verified on 900 sampled records across five style queries: 0% lacked a
style containing the query string. So a record matches a style cell if any
of its styles contains the cell's style string (case-insensitive), with two
empirically verified exceptions where the parent does NOT return the child:
("Power Electronics", "Electro") and ("Minimal Techno", "Techno"). The
original exact-match matcher understated inclusion probabilities (weights
ran ~17% above genre totals; the Eyra Music share came out 7x too high)
and is superseded; see `src/04_analysis_samples.py`.

Dropped: rock/pop control samples. The sampler died on rock 2020 (Vinyl x
US alone exceeds the 10,000-result cap and cannot be split further at the
country stage). Genre comparison therefore rests on the population counts
only. Electronic cohorts are unaffected.
See `src/02_fetch_samples.py` and `src/04_analysis_samples.py`.

Known frame gaps (disclosed, not hidden):
- Style strata cover the electronic styles listed in `02_fetch_samples.py`
  (70 styles). Releases whose styles are all outside that list cannot be
  sampled. The list was built to cover the genre's style vocabulary; the
  residual is estimated in the analysis from secondary-style assignments.
- Splits by format / file-description / country leave a small residual
  (formats like DVD, countries outside the top-10 list). Frame totals vs
  genre totals are reported per cohort in `results_samples.json`.
- `community.have` (number of Discogs users who own a release) accumulates
  with age, so demand is compared age-normalized as collectors per year
  of age (`have / (2026.89 - (year + 0.5))`).
- Calibration: Horvitz-Thompson weight totals run ~10-15% BELOW the genre
  totals (2005: 87,416 vs 97,657; 2015: 132,540 vs 155,908; 2025: 107,188
  vs 123,719), which is the expected frame gap (residual formats, countries
  outside the top-10 list, and styles outside the 70-style list) plus
  pagination duplication. A census check on the Trip Hop 2005 cell (all 13
  pages fetched) bounds the single-cell error at ~5% and shows a random
  page's have-median within 2 of the population median. The 13 Trip Hop
  pages returned 1,271 slots but only 1,237 unique releases (duplicates and
  omissions as the ordering shifts). Shares, medians and ratios are ratio
  estimators and are robust to a common weight scaling; the weight TOTAL
  is the unreliable number and is never used as a finding. The format-mix
  shares from the samples match the independent population format totals
  within ~3 points in every cohort, which is the strongest end-to-end check
  on the weights.

## Cataloguing-lag correction

Recent years are undercounted because Discogs is user-built and releases
take time to be added. Pop is flat at ~51.6k/yr in 2005-2021, so pop's
post-2021 decline measures the lag curve directly: observed/true = 0.93
(2022), 0.88 (2023), 0.77 (2024), 0.68 (2025), 0.46 (2026, partial year).
Applying pop's lag factors to electronic gives the lag-corrected series in
`counts_by_genre_year.csv`. Rock (flat ~140k/yr 2014-2021) gives a second,
independent control (factors 0.94 / 0.92 / 0.82 / 0.76 / 0.55); the two
controls put lag-corrected electronic 2025 at 163k-183k, and they agree
within ~11%.
The correction assumes the lag curve is the same across genres; electronic's
long tail of small digital releases may be catalogued more slowly than pop's
major-label releases, in which case the corrected 2025 figure is a lower
bound. Raw and corrected numbers are always shown side by side.

## Reproduce

```
python3 src/01_fetch_counts.py   # counts (re-downloads; snapshot committed)
python3 src/02_fetch_samples.py  # stratified samples (re-downloads; snapshot committed)
python3 src/03_analysis_counts_beatport.py
python3 src/04_analysis_samples.py
python3 src/05_charts.py
```

Requires pandas, numpy, requests, matplotlib, scikit-learn, xgboost, shap.
Steps 1-2 hit the live Discogs API; the committed snapshots in `data/raw/`
are the 2026-11-21 capture used for every number in the README.
