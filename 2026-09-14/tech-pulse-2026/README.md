# Tech Pulse 2026: what the industry talks about, who it cuts, and what the market pays

*Daily build 2026-09-14 · topic: tech-industry · part of [mzhou-ds/passion-projects](../..)*

Three lenses on the same industry, one story: since late 2022, tech has been
talking about AI, cutting headcount, and getting rich doing it.

## The three parts

### 1. Labor — the layoff wave that never fully broke
3,034 layoff events from Jan 2022 to Mar 2026 (layoffs.fyi data), totaling
**744,244 reported jobs cut**:

| Year | Headcount cut | Events |
|------|--------------:|-------:|
| 2022 | 163,999 | — |
| 2023 | 264,100 | — |
| 2024 | 152,922 | — |
| 2025 | 123,622 | — |
| 2026 (thru Mar) | 39,482 | — |

- **Peak month: January 2023** — 89,709 cuts in a single month (Google 12k, Microsoft, Amazon…).
- **Retail cut the most people (97k), then Hardware (95k)** — Intel alone cut 42,000
  across three events (Apr 2025: 22k; Aug 2024: 15k; Jul 2025: 5k). The chip
  industry is simultaneously the AI boom's biggest winner and a layoff leader.
- **Serial cutters:** Amazon leads with 13 separate layoff events (58k total);
  Salesforce, Google, Microsoft, and Rivian each had 10.
- **Stage predicts severity:** seed startups cut a median of **100%** (shutdowns);
  Series A 33%, Series B 25%, tapering to 10% at Post-IPO. Early-stage pain is
  existential; big-tech pain is a rounding error.
- 60.5% of events were at US-based companies.

### 2. Discourse — the AI takeover of tech's attention
499 current Hacker News front-page stories, classified by keyword rules:

- **AI/ML is the single largest topic at 18.2%** — more than Show HN (7.8%),
  Programming & CS (6.6%), and Big Tech news (5.4%) combined… nearly.
- Since 2021, the share of *all* HN stories mentioning the keyword "AI" rose
  **from 3.2% to 16.2% (2025 avg) — a 5× increase**, inflecting sharply at the
  ChatGPT launch (Nov 2022).
- "ChatGPT" as a keyword spiked to 5.3% of stories in early 2023, then faded as
  "AI" became the generic term; "LLM" climbed steadily to ~4.5%.
- github.com is the front page's home turf: 33 of 499 stories link there.

### 3. Capital — the market paid for the efficiency
Daily closes, Jan 2021 → Sep 2026 (Yahoo Finance):

| Index | Total return | Max drawdown | AI-era share of gains* |
|-------|------------:|-------------:|----------------------:|
| SMH (semiconductors) | **+419.5%** | −45.3% | 95.2% |
| XLK (tech sector) | +193.5% | −34.0% | 91.0% |
| QQQ (Nasdaq 100) | +131.1% | −35.6% | 109.6% |
| SPY (S&P 500) | +107.2% | −25.4% | 81.6% |

\* Share of total gains since Jan 2021 earned after the ChatGPT launch (Nov 2022).
QQQ's is >100%: *all* of its net gains since 2021 came after Nov 2022.

- QQQ troughed Dec 28, 2022 and recovered by Dec 2023; the S&P 500 didn't
  recover until Jan 2024. The April 2025 tariff shock is visible as a sharp
  V across every index.
- **The efficiency era:** quarterly layoff volume and QQQ returns correlate at
  −0.36 — mass cuts continued through 2024–2025 *while* tech stocks ripped.
  Headcount shrank; multiples expanded. That is the AI-restructuring trade in
  one chart (`11_efficiency_era.png`).

## Charts

| # | Chart | What it shows |
|---|-------|---------------|
| 01 | `01_layoff_wave_monthly.png` | Monthly layoff headcount + 3-mo avg, 2022–2026 |
| 02 | `02_industry_2023_vs_2025.png` | Industry mix: 2023 vs 2025 |
| 03 | `03_serial_layoffs.png` | Companies with the most separate layoff events |
| 04 | `04_stage_severity.png` | Median % cut by funding stage |
| 05 | `05_tech_vs_market.png` | QQQ/SPY/XLK/SMH/Nasdaq rebased to 100 |
| 06 | `06_qqq_drawdown.png` | Nasdaq 100 drawdown, 2021–2026 |
| 07 | `07_hn_topics.png` | HN front-page topic mix (n=499) |
| 08 | `08_hn_ai_share.png` | AI keyword share of HN stories, 2021–2025 |
| 09 | `09_hn_engagement.png` | Comments vs score by topic |
| 10 | `10_hn_domains.png` | Top linked domains on the front page |
| 11 | `11_efficiency_era.png` | Quarterly layoffs vs QQQ price |

## Data sources & methods

- **Layoffs:** layoffs.fyi via the GitHub mirror
  [tbhatti211-wq/tech-layoff-analysis](https://github.com/tbhatti211-wq/tech-layoff-analysis)
  (`data/processed/layoffs_clean.csv`; raw file vendored in `data/`). Analysis
  window 2022-01 → 2026-03, deduped on company+date. Cross-check: Crunchbase
  News' 2025 tally (~127k US-based) is consistent with our 123.6k global
  reported figure. Caveat: headcounts are announced numbers; ~24% of events
  lack a reported count, and layoffs.fyi is crowdsourced.
- **Discourse:** Hacker News Firebase API (`topstories`, n=499, fetched
  2026-09-14) + Algolia HN search API for monthly keyword counts. Topic
  classification is rule-based on titles (see `src/04_analyze_hn.py`); ~52%
  fall into "Essays & misc" — HN's front page is genuinely eclectic. Caveat:
  Algolia's `nbHits` are estimates and its 2026 monthly *totals* were unstable,
  so the time series is capped at Dec 2025; the Sep-2026 level comes from the
  front-page classifier instead.
- **Markets:** Yahoo Finance daily closes (`query1.finance.yahoo.com` chart
  API). Stooq's CSV endpoint was attempted first but now sits behind a JS
  browser-verification challenge, so it was not used.

## Reproduce

```bash
pip install -r requirements.txt
python src/01_fetch_hn.py        # HN front page snapshot (~4 min)
python src/01b_fetch_hn_ai.py    # monthly AI keyword counts (~7 min)
python src/02_analyze_layoffs.py # part 1: charts 01-04
python src/03_analyze_markets.py # part 3: charts 05-06
python src/04_analyze_hn.py      # part 2: charts 07-10
python src/05_synthesis.py       # part 4: chart 11
```

All findings numbers are computed from the data and saved to
`data/findings_{layoffs,markets,hn}.json` — nothing in the write-up above is
hand-typed.
