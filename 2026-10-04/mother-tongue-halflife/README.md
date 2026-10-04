# The Mother-Tongue Half-Life

**The Chinese-language market expires in about 14 years — unless the immigration tap outruns the drain.**
*Musing with Mike · 2026-10-04 · Topic: culture*

Every business that serves the Chinese diaspora in Chinese — media, remittance, clinics, tutoring, grocery, WeChat-era anything — is selling into a market with a measurable decay constant. The first generation speaks Chinese. The second generation mostly doesn't. The third is a rounding error. The only thing refilling the top of the funnel is immigration, and you can price exactly how fast the tap has to run to keep the market flat. I ran the numbers for both countries I have citizenship feelings about.

**Interactive version:** open `site/index.html` — pick a city and a language, choose an immigration level, and watch the market expire (or not) to 2051.

## What I built

| # | Question | Data | Script |
|---|----------|------|--------|
| 1 | How fast does Chinese die, generation by generation? | StatCan 2021 Census 98-10-0325-01: mother tongue × generation status, Canada + 7 CMAs | `src/fetch_statcan_cma.py`, `src/analyze.py` §1–3 |
| 2 | What does the US market look like without a generation variable? | ACS 2023 5-year: B16001 (language at home, English proficiency), B05006 (born China/HK/Taiwan), B01003 — 13 metros + US | `src/fetch_acs.py`, `src/analyze.py` §4 |
| 3 | Which cities are the same kind of market? | KMeans (k=4, silhouette 0.54) on harmonized features for 19 cities | `src/analyze.py` §5 |
| 4 | When does each city's market actually expire? | Decay-plus-refill accounting model, 2021→2051, three immigration scenarios | `src/analyze.py` §6 |

Reproduce: `python3 src/fetch_statcan_cma.py && python3 src/fetch_acs.py && python3 src/analyze.py` (StatCan reuses the archived census cube from the 2026-09-24 build; fresh download URL is in the script header. ACS needs the ~286 MB .dat extracts — download links in `src/fetch_acs.py`; the Census API now requires a key, so this parses the public summary files instead.)

## Findings

**1. The cliff is not a slope.** Share of Chinese Canadians with a Chinese mother tongue: **91.5%** (1st gen) → **51.5%** (2nd) → **5.8%** (3rd+). Fitted as exponential decay, the language share has a **half-life of ~14 years** (0.5 generations). The first transition loses half the market; the second loses almost all of what's left (retention ratios 0.56, then 0.11). There is no gradual bilingual fade — there's one generation of real transmission and then English.

**2. Cantonese is the stickier language — and it's not close.** Transmission into the second generation: **Cantonese 80%** (36.9% → 29.6% of each generation), **Mandarin 41%** (51.1% → 20.8%). Mandarin's fitted half-life is 8.8 years; Cantonese's is 18.9. The Hong Kong wave built households that kept the language; the newer Mandarin inflow is bigger but leaks faster. In raw stock, Mandarin already won nationally (716,665 vs 582,290 in 2021) — but it won on volume, not loyalty.

**3. The kids have flipped; the stock hasn't.** Among second-generation children aged 0–14, Mandarin already beats Cantonese **67,225 to 29,620** nationally, and **2,540 to 1,070 in Edmonton** — my hometown, where second-gen adults aged 25–54 still run 3,090 Cantonese to 305 Mandarin, a 10:1 ratio. Yet in the projection, Edmonton's Mandarin stock *never* passes its Cantonese stock by 2051 under any scenario: the installed Cantonese base decays at 3.6%/yr while Edmonton's slice of Mandarin inflow can't cover Mandarin's 7.6%/yr drain. Stocks are lagging indicators. If you only look at totals, you'll read the market ten years late.

**4. Standing still requires ~66,000 people a year.** Holding Canada's 2021 Chinese-mother-tongue stock (1.35M) flat against the fitted 4.9%/yr drain takes roughly **66k net new Chinese-mother-tongue immigrants annually**. At 30k/yr (base case), the stock falls to ~545k by 2051; even at 45k/yr it falls to ~666k. Toronto drops from 546k speakers to ~220k (base), Vancouver from 414k to ~167k. This is the operator takeaway: a Chinese-language business in Canada is not riding population growth — it's harvesting a stock that current immigration does not replenish. Growth has to come from share-of-wallet, not market growth.

**5. Four kinds of diaspora market, two countries.** KMeans over density, Cantonese-ness, and first-gen intensity sorts 19 cities into: **(a)** Toronto + Vancouver — dense, Cantonese-heavy, 84% first-gen speakers; **(b)** New York, Los Angeles, San Francisco-Oakland — the US mega-hubs; **(c)** Calgary, Edmonton, Montreal, Ottawa-Gatineau, Winnipeg — mid-density prairie/heritage markets with high Cantonese share; **(d)** ten dispersed US metros (Boston to Tampa) — thin, English-dominant. Montreal is the retention outlier: **63.4%** second-generation retention and the longest half-life (18.0 yrs) of any Canadian city — plausibly because a French-speaking environment makes a third language feel less like a deviation. Winnipeg decays fastest (10.7-yr half-life).

**6. The US segment that actually needs you is 1.8 million people.** 51.5% of the 3.49M Americans who speak Chinese at home speak English less than "very well" — that's the population for whom Chinese-language service is a necessity, not a preference. It's concentrated: **New York 395k (60% of its speakers), Los Angeles 266k, San Francisco-Oakland 206k**. San Francisco-Oakland is the densest US market at **84 Chinese speakers per 1,000 residents**; nationally it's 10.5. If you're sizing a Chinese-language service, the need-based TAM is half the headline number and lives in five metros.

**7. The lapsed market is the growth market.** Canada has ~207k second-generation and ~56k third-generation Chinese Canadians whose mother tongue is *not* Chinese — nationally, 263,440 people in the "lost the language, kept the identity" segment (Toronto alone: 96k, Edmonton: 13k). They don't need service in Chinese. They buy heritage: lessons, identity content, food-as-culture, trips "home." I'm in this cell of the table. The first-gen market is expiring on a 14-year half-life; this segment is the only one that compounds.

## The personal bit

I grew up in Edmonton in the 10:1 Cantonese cohort. My parents' generation spoke it at home; my generation answered in English. The census basically has a row for my family: second generation, 49% retention in Edmonton, coin-flip odds. Mandarin passing Cantonese among Edmonton kids isn't a loss in the data — it's a changing of the guard I can hear at every dim sum place back home. Now I'm in San Francisco re-learning Chinese as an adult, which makes me a data point in finding #7: the lapsed segment, buying back in. The market for that — teaching adults like me — is the one piece of this economy that grows while everything else decays on schedule.

## Caveats

- The projection is an **accounting model, not a demographic forecast**: it applies the decay constant fitted on the 2021 cross-sectional generational shares to the whole stock, plus a constant immigration inflow. It does not model fertility, intermarriage by cohort, return migration, or policy changes (all of which move the drain rate itself — finding #3's kids are already transmitting differently).
- A "generation" is set at 27.5 years; half-lives scale linearly with that choice. Generation status in StatCan data is birthplace-based (1st = born abroad, 2nd = born in Canada to immigrant parents), so cross-sectional shares mix transmission with the age structure of each cohort.
- US data has no generation variable: retention is proxied by speakers-per-China-region-born (1.24 nationally) and English proficiency. B16001 in the table-based summary files lacks rows for Houston, San Diego, Sacramento, Las Vegas, and Honolulu — those metros are excluded rather than estimated, and San Jose is folded into San Francisco-Oakland at CBSA level.
- Mother tongue (Canada, first language learned and still understood) and language spoken at home (US) are different questions; cross-country levels are directional, decay mechanics are Canada-measured.

## Sources

- Statistics Canada, 2021 Census table 98-10-0325-01 (visible minority × generation status × mother tongue), Canada + Toronto/Vancouver/Montreal/Calgary/Edmonton/Ottawa-Gatineau/Winnipeg CMAs. Full-table zip: `https://www150.statcan.gc.ca/n1/tbl/csv/98100325-eng.zip`
- US Census Bureau, ACS 2023 5-year table-based summary files B01003/B16001/B05006 via www2.census.gov (the Census API returned "Missing Key" without a key; Census Reporter 403'd — summary files are the reproducible route. Details in `src/fetch_acs.py`.)
- Generation length (27.5 yrs) and scenario inflow levels (15k/30k/45k per year) are stated assumptions; the ~66k/yr breakeven is computed from the fitted drain, not assumed.

## Layout

```
mother-tongue-halflife/
├── src/
│   ├── fetch_statcan_cma.py   # stream-filter census cube -> compact CSV
│   ├── fetch_acs.py           # parse ACS .dat extracts -> compact JSON
│   └── analyze.py             # retention fits, clustering, projections, charts
├── data/
│   ├── statcan_cma_mothertongue.csv
│   ├── acs_chinese_language.json
│   ├── archetype_features.csv
│   └── findings.json          # every headline number in this README
├── charts/                    # 6 PNG figures
└── site/
    ├── index.html             # interactive expiration-date calculator
    └── data.js                # projection series + findings (generated)
```
