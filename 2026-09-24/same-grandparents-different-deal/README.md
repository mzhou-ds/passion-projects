# Same Grandparents, Different Deal

**What Canada and the United States each offer a Chinese immigrant family — priced in real data.**

Build #17 · *Musing with Mike* · September 24, 2026

One family tree, two immigration products. The US sells a **lottery ticket** (the H-1B raffle) stapled to a Bay Area salary band. Canada sells a **points test** (Express Entry) with a secret francophone discount. Both converge on the same punchline: the kids do better than the parents — much better.

Interactive site: [`site/index.html`](site/index.html) — includes a working CRS points calculator ("Would *you* clear the bar?") graded against real September 2026 cutoffs.

## The findings

### Pillar 1 — Two immigration products
- **H-1B lottery (FY2021–26):** selection rates ran 45% → 43% → 26% → 24% → 28% → 35%. FY2026: 120,141 selected from 345,737 entries.
- **The price tag:** median offered wages on certified FY2025-Q4 LCAs for software roles at Bay Area worksites — Meta $229,501 · Google $225,965 · Salesforce $242,754 · Apple $203,794 · Amazon $207,400 (DOL OFLC disclosure data).
- **Express Entry invitations (2015–2026):** India 355,035 vs China 51,925. #4 is **Cameroon (40,585)** — the French-language lane, where 2026 cutoffs ran **382–420** against 514–523 for Canadian Experience Class draws. Language isn't a tiebreaker; it's a cheaper door.
- **Where invites land:** the 901–1100 CRS hump is the Provincial Nominee Program (600 bonus points); general/CEC draws clear at 451–600.

### Pillar 2 — Customer outcomes
- **US (ACS 2020–2024):** Asian-alone median household income **$116,503 vs $80,734** (+44%). Bachelor's+ 57.7% vs 35.7%. Poverty 9.9% vs 12.5%. Unemployment 4.4% vs 5.2%. 58.2% in management/business/science/arts occupations vs 42.6%.
- **Canada (2021 Census, income ref. year 2020):** Chinese median total income $32,800 vs $43,200 non-visible-minority (−24%). Ages 25–54: $46,400 vs $54,400 (−15%).
- **The second-generation flip:** 1st-gen Chinese Canadians (25–54) earn $42,400 — but the **2nd generation earns $64,500, ~10% *above* non-visible-minority peers** ($58,800). 3rd+ gen: parity ($54,400 vs $54,000).
- **The education discount:** among 25–54s with a bachelor's or higher, Chinese Canadians' median is $58,400 vs $74,500 — a $16k credential haircut.
- **Low income (LIM-AT):** Chinese 17.5% overall → 21.0% (1st gen) → 9.0% (2nd) → **5.7% (3rd+)**, half the national rate.
- **Convergence:** average employment income, Chinese vs non-visible-minority: gap narrowed from $4,360 (2006) to $2,230 (2021), nominal.

### Pillar 3 — The bamboo ceiling that wasn't
- Canada NOC data (ages 25–54): management-occupation share — Chinese 16.4% vs 13.6% non-visible-minority overall; 1st gen 16.6% vs 16.4% (parity); 2nd gen 15.8% vs 16.0% (parity). The all-ages gap is an age artifact (2nd gen skews young). The penalty is in pay-per-credential, not titles.

### Pillar 4 — Two Chinatowns
- **US metros:** Asian median HH income beats the metro average everywhere — San Jose $207k vs $162k, SF $161k vs $136k, Seattle $150k vs $115k.
- **Canada CMAs:** Toronto — Chinese 25–54 median $48,800 vs $50,000 metro (near parity, 11% of 15+ pop). Vancouver — $44,400 vs $50,800 (18.9% of 15+ pop).
- **What survives:** Chinese mother tongue — 1st gen 88% (Mandarin 51%, Cantonese 36%) → 2nd gen 45% (Cantonese 26.5% > Mandarin 18.3% — the Hong Kong wave holds on tighter) → 3rd+ gen ~4%.

## Data & reproduction

All analysis runs from this folder. Raw downloads are git-ignored (several GB); filtered extracts are committed.

| Source | Files | Notes |
|---|---|---|
| US Census Bureau, ACS 2020–2024 5-yr (via Census Reporter API) | `data/us_indicators.json`, `data/us_metro.json`, `data/raw/reporter_*.json` | Asian-alone (B-tables `*D`) vs total population |
| Statistics Canada, 2021 Census full tables | `data/statcan_*_filtered.csv` | 98-10-0331-01 (income), 98-10-0325-01 (mother tongue), 98-10-0330-01 (occupation), 98-10-0642-01 (income by year), 98-10-0332-01 (low income). Income ref. year 2020 |
| IRCC Open Data (monthly) | `data/ircc_summary.json`, `data/raw/ircc/` + `data/raw/ircc_ODP-EE_*.csv` | Invited candidates by citizenship/score band/CMA; admissions by citizenship/occupation |
| USCIS (via BAL / Congress reporting) | hardcoded in `make_charts.py` | FY2021–26 registration & selection counts |
| US DOL OFLC, LCA disclosure FY2025 Q4 | `data/lca_tech_wages.json` | Certified software roles, Bay Area worksites |

### Reproduce

```bash
cd 2026-09-24/same-grandparents-different-deal
python3 -m pip install pandas matplotlib openpyxl   # one-time

# 1. Fetch US data (Census Reporter; ~50 small JSON pulls, no key needed)
python3 fetch_census.py            # pins acs2024_5yr; JSONs land in data/raw/

# 2. Fetch StatCan full-table zips (~2.9 GB total; git-ignored)
#    https://www150.statcan.gc.ca/n1/tbl/csv/{98100325,98100326,98100330,98100331,98100332,98100642}-eng.zip

# 3. Stream-filter to compact CSVs (no 7 GB extraction; reads inside the zips)
python3 prep_statcan.py            # income table
python3 prep_statcan2.py          # mother tongue, low income, income-by-year, occupation

# 4. Fetch IRCC open data
#    https://www.ircc.canada.ca/opendata-donneesouvertes/data/ODP-EE_{candidates-ITA_score,Candidates-CITZ,Candidates-CMA,admissions-CITZ,admissions-Occ}.csv

# 5. LCA wages (FY2025 Q4 xlsx from dol.gov OFLC disclosure page)
python3 analyze_lca.py

# 6. Analysis + charts
python3 analyze_us.py             # -> data/us_indicators.json
python3 make_charts.py            # -> charts/*.png

# 7. Open site/index.html in a browser
```

Caveats: Canada income reference year is 2020 (pandemic); US ACS 5-yr spans 2020–2024. Cross-border dollar comparisons are directional, not PPP-adjusted. CRS calculator is a simplified single-applicant model — indicative only.
