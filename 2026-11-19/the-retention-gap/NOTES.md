# Working notes — Build #73 (culture) — 2026-11-19

## Topic
Culture (Canada vs US / Canadian-born Chinese). Next in rotation after tech-industry (#72).

## Candidate question
Does Canada's multiculturalism actually keep a heritage language alive longer
than America's melting pot? Measured as heritage-language retention among the
Chinese diaspora, by generation, Canada vs US, from each country's own census.

## Novelty case (why an expert would be surprised)
The mosaic-vs-melting-pot debate is argued in theory and op-eds; nobody I know
has priced it as a comparable measurement. The folk assumption cuts both ways
and both are wrong in interesting directions:
- The naive Canadian story says multiculturalism preserves heritage languages,
  so 2nd-gen Chinese Canadians should retain Chinese at much higher rates.
- The naive American story says the melting pot assimilates faster, so 2nd-gen
  Chinese Americans should retain less.
What nobody has measured is the actual gap, generation by generation, and the
mechanism behind it: if retention is driven by enclave density / co-ethnic
community size rather than national ideology, the "mosaic" effect may be a
Toronto/Vancouver effect, not a Canada effect — and the US may retain MORE in
its big enclave metros. That distinction (ideology vs geography) is the hidden
mechanism under a familiar stat, and it is testable: retention by generation,
split by metro concentration, in both countries.
If the data show the gap is small or reversed, that overturns the branding of
both countries at once. If the gap is large, it is the first hard number for a
century-old argument.

## Shelved briefs check
No shelved brief applies to culture: the three on file are EDGAR AI (tech),
nutritional jetlag (nutrition, since built 2026-10-28), and ClinicalTrials.gov
eligibility (biohacking). No pivot; this is a fresh design for the culture slot.

## Data plan (pending source research)
- Canada: StatCan 2021 Census, language by generation status (Chinese mother
  tongue / language spoken at home).
- US: ACS 2022 1-year via Census API, nativity x language (Chinese) cross-tab.
- Fallback if no clean cross-tab: comparable age-cohort or metro-level design.

## Results (2026-11-19, after data work)

### Novelty verdict: PASSES the bar
No one I know of has priced the mosaic-vs-melting-pot claim as a comparable
measurement. The folk assumption in both directions is wrong, and the measured
answer overturns the branding of both countries at once: the retention rates
are within a point of each other in every generation. The hidden mechanism is
the generational clock plus the city and the wave, not national ideology.
An expert in immigration or heritage languages would be surprised by (a) the
near-zero country gap, (b) the 10x third-generation cliff, and (c) Montreal
topping retention while Vancouver, the densest enclave, sits mid-pack.

### Headline numbers
- Immigrants keep the language at home: CA 82.4% (derived) vs US 81.5%.
- Native-born: CA 2nd gen 32.9% (derived) vs US native-born 32.2%.
- Canada mother tongue among Chinese visible minority: 1st gen 89.8%,
  2nd gen 42.9%, 3rd+ gen 4.4% (2,640 people nationally).
- Geography spread dwarfs the country gap: Montreal 58.4% vs Calgary 41.1%
  (CA 2nd-gen MT); New York 47.6% vs Florida 20.3% (US native-born home use).
- Enclave density does not explain it (CA r=-0.33, US r=+0.38); NY beats CA
  inside every age band, so it is place/wave, not age composition.
- Mandarin immigrates (55% of 1st-gen Chinese MT), Cantonese inherits
  (58% of 2nd-gen, 80% of 3rd+); 2nd-gen kids under 15 are 68% Mandarin.

### Data notes
- Census API now requires a key for data endpoints, so the US side uses bulk
  PUMS files (verified: LANP/NATIVITY/ANC1P metadata + csv_pus.zip, 591 MB).
- StatCan table 98-10-0617-01 is WIDE format (home-language members are
  columns); the 5.3 GB CSV was streamed, never extracted to disk.
- Raw zips deleted before commit (907 MB); parsed CSVs kept, downloads
  documented in README.
