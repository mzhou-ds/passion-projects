# The 49th Parallel

**A data story of Canada, America, and the Chinese Canadians in between.**
*Musing with Mike · Build Nº 8 · 2026-09-15*

Canada and the United States share the world's longest undefended border, a
language, and a Netflix catalogue. From space they look like one country with
a line drawn through the trees. The data says otherwise — and the third story
here, the Chinese Canadian one, is the one I grew up inside.

**Interactive version:** open `site/index.html` in a browser — it includes all
charts plus *The Vocabulary Border Test*, an 8-question quiz that grades how
Canadian your vocabulary is.

## What I built

Four data investigations, each from a primary source, all reproducible:

| # | Question | Data | Script |
|---|----------|------|--------|
| 1 | How far apart are Canada and the US, really? | World Bank WDI API (1990–2024) | `analyze.py` §1 |
| 2 | Who owns hockey? | NHL official records API — all 5,997 draft picks, 2000–2025 | `analyze.py` §2 |
| 3 | Do Canadian words look Canadian in print? | Google Books Ngram Viewer, US vs British corpora (1960–2019) | `analyze.py` §3 |
| 4 | How did Chinese Canadians go from 17k to 1.7M? | StatCan 2021 Census + census tables | `analyze.py` §4 |

Reproduce everything: `python3 fetch_data.py && python3 analyze.py`.

## Findings

**1. The outcomes gap is wide and widening.** Canadians live **3.2 years
longer** than Americans (81.6 vs 78.4, 2023) while spending far less of their
economy on health (**11.3%** vs **16.7%** of GDP). The US homicide rate
(**5.8**/100k) runs ~3× Canada's (**2.0**). Canada is less unequal (Gini 31.5
vs 41.8) and more immigrant per capita (**21.3%** vs **15.4%** foreign-born).
The GDP-per-capita crown goes south ($86k vs $55k) — America is richer and
sicker; Canada is poorer and longer-lived.

**2. Canada's grip on hockey loosened, then tightened.** Canadians were ~56%
of draft picks around 2008, slid to ~29% by 2019 (the US development
program's peak), and rebounded to ~39% in 2025. But at the **top** of the
draft Canada never left: Canadians take most first-round picks most years,
including #1 overall in 2025 (Matthew Schaefer). Fun details: Alberta
(pop. 4.8M) produced 11 picks in 2025 — 4th of any province/state — and
Haoxi Wang (33rd overall) became one of the first Chinese-born players ever
drafted.

**3. Canadian vocabulary is invisible in print — and what is visible reads as
British.** In the Google Books corpus, *beanie* beats *toque* and *restroom*
beats *washroom* in **both** the American and British corpora. But the words
Canadians actually say skew hard toward the British corpus: *cheque* 5.9×,
*eh* 4.5×, *washroom* 3.3×, *toque* 2.9× more common in British than American
books. Meanwhile *restroom* has surged in the **British** corpus since the
1990s — American words are colonizing even British print, while spoken
Canadian holds the line. (Methodology note: the Ngram Viewer's corpus IDs
are undocumented; I verified 27=British / 28=American empirically using
*cheque*, *lorry*, and *petrol* as calibration words. The docs-as-folk-wisdom
had them backwards.)

**4. The fastest demographic turnaround in Canadian history.** Chinese
Canadians: **17,312 people in 1901 → 1.7 million in 2021** (4.6% of Canada).
The flat century was policy: head tax (1885), pogrom (1907), Exclusion Act
(1923–47 — in 1931 there were 1,240 Chinese men per 100 Chinese women). The
hockey stick after is the 1967 points system plus the pre-handover Hong Kong
wave (166,487 arrivals, 1988–93). Today: 97.7% live in big cities, ~70% in
just Toronto and Vancouver; Richmond BC is **54.3% Chinese**, the highest
share of any municipality in Canada; **28.4% were born in Canada**; 61.8% of
25–54 year-olds hold a bachelor's or higher. The community went from banned
to plurality in two generations.

## The personal bit

I grew up in Alberta saying *toque* and *washroom* and *eh* without knowing
they were border markers — you only learn your words are Canadian when you
leave and someone laughs. Moving to San Francisco made the comparison
unavoidable: the two countries rhyme, but the outcomes don't. This build is
my attempt to put numbers on the feeling of living on both sides of the
49th — and to document the community that raised me, which went from the
Exclusion Act to Richmond in a single lifetime.

## Sources

- World Bank World Development Indicators API v2 (no key): life expectancy
  `SP.DYN.LE00.IN`, health expenditure `SH.XPD.CHEX.GD.ZS`, intentional
  homicides `VC.IHR.PSRC.P5`, Gini `SI.POV.GINI`, migrant stock `SM.POP.TOTL`,
  GDP per capita `NY.GDP.PCAP.CD`.
- NHL records API (`records.nhl.com/site/api/draft`), draft years 2000–2025;
  birth country per pick. Cross-checked against Wikipedia's draft nationality
  tables (2000: 35.2% vs API 32.8%; 2025: 37.9% vs 39.3%) — small
  classification differences, same trend.
- Google Books Ngram Viewer JSON endpoint, corpora 27/28 (2019), smoothing 3.
- StatCan, *Portrait of the Chinese Populations in Canada* (89-657-X2026001,
  2026); StatCan 2021 Census; census tables via Wikipedia "Chinese Canadians".
  Full citations in `data/diaspora_sources.md`.

## Layout

```
forty-ninth-parallel/
├── fetch_data.py        # downloads all raw data (World Bank, NHL, Ngrams)
├── analyze.py           # analysis + chart generation
├── README.md            # this file
├── data/
│   ├── raw/             # cached API responses (46 files)
│   ├── findings.json    # headline numbers
│   ├── diaspora_history.csv / diaspora_cma.csv
│   └── diaspora_sources.md
├── charts/              # 8 PNG figures
└── site/
    └── index.html       # interactive data story + vocabulary quiz
```
