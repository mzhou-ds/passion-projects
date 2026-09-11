# Strength in Numbers — what 1.5 million powerlifting results teach us about getting strong

**Musing with Mike · daily build #4 · 2026-09-11 · topic: fitness**

Everyone in the gym has opinions about strength. This project replaces opinions
with 1,523,393 real competition results: every IPF-affiliate powerlifting meet
entry in the OpenPowerlifting archive (1966–2026). From it: true strength
standards, the age curve of strength, how much a squat suit is really worth,
whether scoring formulas favor heavyweights, and the quiet explosion of women's
powerlifting.

**Try it:** open [`explorer.html`](explorer.html) — enter your sex, bodyweight
and best total to see your percentile among 389,009 real competitors.

## Findings

**1. Real strength standards (225,463 raw lifters, one best total each).**
The median competitive raw total is **527.5 kg for men / 297.5 kg for women**.
A 600 kg total puts a man around the 73rd percentile; a 400 kg total puts a
woman around the 91st. The 99th percentile — genuinely elite — starts at
807.5 kg (men) and 490 kg (women). See `charts/01_standards.png`.

**2. Strength peaks earlier than you'd think — then fades slowly.**
Median bodyweight-adjusted strength (IPF Goodlift points) peaks at **age 26
for men and 24 for women**; elite (90th percentile) lifters peak a few years
later, at 29 and 26. The good news: decline is gradual. At 55, the median
competitor still holds **~84% of peak strength**. See `charts/02_age_curve.png`.

**3. Powerlifting is booming, and women are driving it.**
Unique raw competitors per year, 2010 → 2025: men **1,262 → 19,959 (~16x)**,
women **256 → 9,664 (~38x)**. Median totals rose too — men 515 → 565 kg
(+10%), women 270 → 340 kg (+26%). See `charts/03_growth.png`.

**4. The sex gap is closing.**
Women's median total as a share of men's (raw): **49.8% in 2008 → 60.2% in
2026**. Women's fields didn't just get bigger — they got much stronger.
See `charts/04_sex_gap.png`.

**5. The suit is worth ~10%.**
Comparing 29,403 lifters who have *both* a raw and a single-ply best total
(same person, paired): single-ply adds a median **+9.1% for men and +12.1%
for women**. See `charts/06_equipment.png`.

**6. Dots still favors heavyweights.**
A perfect bodyweight formula would be flat across weight classes. It isn't:
the median 140 kg man outscores the median 60 kg man by **~12%** on Dots.
Light lifters are systematically under-credited. See `charts/05_dots_bias.png`.

## Data

- **Source:** OpenPowerlifting bulk CSV, IPF-affiliate edition
  (`openipf-2026-09-05`, revision `b8b9bf6e`, published 2026-09-04).
  Downloaded from https://openpowerlifting.gitlab.io/opl-csv/bulk-csv.html.
- **License:** public domain (facts contributed to the public domain by the
  OpenPowerlifting project). Attribution: *"This project uses data from the
  OpenPowerlifting project, https://www.openpowerlifting.org."*
- **Scope note:** IPF affiliates only — strict judging, ~90% drug-tested.
  These are *competition* standards, not gym standards. The median competitor
  trains specifically for the platform.

## Methods

1. `src/download.py` — fetches the exact data revision into `data/`.
2. `src/prepare.py` — keeps full-powerlifting (`SBD`) entries with a valid
   total (1,072,723 entries), then de-duplicates to one best total per
   (name, sex) lifter, separately for Raw (225,463 lifters) and Single-ply
   (163,546 lifters), so repeat competitors don't skew the standards.
3. `src/analyze.py` — percentile tables per 5 kg bodyweight bin; median and
   90th-percentile Goodlift by integer age; yearly participation, median
   totals, and the sex gap; median Dots by bodyweight bin; paired
   raw-vs-equipped comparison for lifters with both.
4. `src/charts.py` — the six charts in `charts/`.
5. `src/explorer.py` — builds the interactive percentile lookup.

`output/` holds the derived tables (`standards.csv`, `age_curve.csv`,
`yearly.csv`, `dots_bias.csv`, `equipment.csv`, `summary.json`).
The 68 MB raw download is intentionally not committed; run the pipeline above
to reproduce everything from scratch.

## Caveats

- The age curve is **cross-sectional** (different people at each age), not a
  longitudinal study of aging — it describes the typical competitor at each
  age, not how one lifter declines.
- De-duplication is by (name, sex); a few lifters may be merged or split.
- Pre-2000 data is sparse; yearly trends before ~2005 are noisy.

## Layout

```
2026-09-11/strength-in-numbers/
├── README.md            — this file
├── explorer.html        — interactive "how strong are you?" lookup
├── charts/              — 6 PNG charts
├── output/              — derived CSV tables + summary.json
├── src/                 — download / prepare / analyze / charts / explorer
└── data/                — raw download (not committed; see src/download.py)
```
