# The Canadian Discount: From 105 Cents to 64

**In 2011, Canada was richer than America per person. Now it makes 64 cents on the dollar, and the IMF says that is the new normal.**
*Musing with Mike · 2026-10-13 · Topic: culture*

Yesterday was Canadian Thanksgiving. I spent it in San Francisco, which is where I live now, doing the math on the country I grew up in. The math is not sentimental. In 2011, at the top of the oil boom with the loonie at par, Canadian GDP per person was US$52,286 against America's US$50,008. Canada was, briefly and on paper, the richer country. In 2024 the same comparison reads US$55,209 against US$86,417. Canada did not collapse. Canada grew a little. America grew a lot, the loonie fell, and Canada added people faster than it added income. The result is a discount with a specific price: 64 cents on the dollar at market exchange rates, 75 cents after you adjust for prices, and no recovery in the IMF forecast through 2030.

I am Edmonton-born and I work in San Francisco, so I live on both sides of this spread. This build prices the spread four ways: the national canyon, the province-versus-state league table, the diaspora's own pay stubs, and a calculator that prices your salary in both countries.

**Interactive version:** open `site/index.html` and type in a Canadian salary. It converts three ways: at today's exchange rate, at purchasing power parity, and at the 2011 rate, back when the loonie was at par.

## What I built

| # | Question | Data | Script |
|---|----------|------|--------|
| 1 | How wide is the canyon, and is it real or just the exchange rate? | IMF World Economic Outlook via DataMapper API: GDP per capita, current US$ and PPP, Canada and US, 2000-2030 (forecast from 2026) | `src/01_fetch.py`, `src/02_analysis.py` |
| 2 | Did the average Canadian actually get poorer, or just the currency? | World Bank constant-dollar GDP per capita and population growth via FRED, 2019-2024 decomposition | `src/02_analysis.py` |
| 3 | Where does each province rank against the states? | StatCan 36-10-0222 (provincial GDP, current prices) and 17-10-0005 (population); BEA state GDP and Census population via FRED; provinces converted at the 2024 average exchange rate | `src/02_analysis.py` |
| 4 | What moves the gap year to year? | XGBoost with SHAP against an OLS baseline, leave-one-out CV, annual drivers 2001-2024: exchange rate, WTI oil, population growth gap, house price growth gap (BIS via FRED), unemployment gap | `src/03_model.py` |
| 5 | Does the discount show up inside the diaspora? | Reused extracts from this repo's 2026-09-24 build: StatCan 2021 Census table 98-10-0331 and ACS 2023 | `src/01_fetch.py`, `src/02_analysis.py` |

Reproduce: `python3 src/01_fetch.py && python3 src/02_analysis.py && python3 src/03_model.py && python3 src/04_charts.py`. No API keys anywhere. FRED state series are fetched in parallel, because 102 sequential requests through a proxy timed out in practice.

## Findings

**1. The canyon opened in two moves, and neither has reversed.** Move one was 2014 to 2016: oil fell, the loonie went from par to 1.37 per US dollar by 2024, and the nominal ratio dropped from 105 percent of the US level to the mid-70s. Move two was slower and quieter: the PPP ratio, which strips out the exchange rate entirely, slid from 83 percent in 2010 to 77 percent in 2019 to 75 percent in 2024. The IMF forecast has the nominal ratio flat near 64 percent through 2030 and the PPP ratio still falling, to about 73 percent. A simple trend fit on the PPP ratio lands near 71 percent by 2035. Whatever this is, the official forecast does not treat it as a dip.

**2. Canada got bigger, not richer. The US got both.** From 2019 to 2024, Canada's total real GDP grew 9.4 percent. Population grew 9.5 percent. Real GDP per person: minus 0.1 percent over five years, with a peak in 2022 and a 1.8 percent slide from that peak by 2024. The US over the same five years: total up 13.3 percent, population up 3.5 percent, per person up 9.5 percent. Canada's population growth hit 2.78 percent in 2023 and 2.98 percent in 2024, roughly triple the US rate and the fastest in generations. Headline GDP growth let everyone say the economy was growing. Per person, it was running in place, and the new arrivals were running in place into the most expensive housing market in the country's history.

**3. About three quarters of the recent widening is pricing. One quarter is real.** Decomposing the 2019 to 2024 move in log points: the nominal ratio fell 0.103, the PPP ratio fell 0.027, and the residual, which is the exchange rate and relative price levels, accounts for 0.076. So most of the lived discount is the dollar price of being Canadian, not output. But the real quarter is the part that compounds, and it is the part still moving the wrong way in the forecast. The SHAP results rhyme with the decomposition. For the nominal gap, the exchange rate dominates (mean |SHAP| 0.049), oil second (0.018), mostly because oil moves the loonie. For the real PPP gap, the leaders are oil (0.0065) and the population growth gap (0.0059), and the exchange rate correctly drops to near zero. One honest note: with 24 annual observations, plain OLS beat XGBoost in leave-one-out testing on both targets (RMSE 0.013 vs 0.015 on the real gap, 0.011 vs 0.030 on the nominal). The tree model is a ranking device here, not a better forecaster, and the README treats it that way.

**4. Alberta, the richest province, would rank 40th in America.** Rank all 50 states plus DC plus the 10 provinces by 2024 GDP per person in US dollars and the table turns blunt. DC tops it at $269,820 (a capital-city artifact), New York is second at $116,402, California sixth at $102,987. Alberta is the top province at $70,581 (C$96,686) and it ranks 40th of 61, ahead of only 12 states. Saskatchewan ranks 45th. Then the floor gives out: British Columbia 54th at $55,349, Ontario 55th at $54,307, exactly one rung above Mississippi, the poorest state, at $53,016. Quebec, at $50,125, ranks below Mississippi. New Brunswick is last overall at $41,138. Ontario is the province that likes to compare itself to New York. On income per person it is in a relegation fight with Mississippi, and Quebec has already been relegated.

**5. The discount is personal, and it is mostly a first-generation, first-country effect.** Chinese Canadians aged 25 to 54 had a median total income of C$46,596 in the 2021 Census (income year 2020), about US$34,716 at that year's average exchange rate. The US Asian median earnings figure from ACS 2023 is $59,823. Toronto's Chinese 25 to 54 median: C$49,216. Vancouver's: C$44,671. The measures are not identical (total income in Canada, earnings in the US, different years), so treat the levels as directional. The internal Canadian pattern is exact, though: second-generation Chinese Canadians earn C$65,083, which is above their non-visible-minority peers at C$58,944. The kids beat the home benchmark. They still land below the American one. Same grandparents, same report cards, different side of the 49th parallel, different price.

**6. The operator read: the border is now a priced spread, and both sides can trade it.** If you hold a Canadian salary and spend any of it in US dollars (travel, tuition, a snowbird winter, US-priced anything), you took a pay cut that never showed up in your offer letter: C$100,000 converts to about $70,161 at the October 2, 2026 rate of 1.4253, against $101,143 at the 2011 average rate. If you are a US company hiring remotely, senior Canadian talent is 36 percent off at market rates and about 25 percent off at PPP, which is why the arbitrage hiring never stopped. If you are the Canadian worker, the ways to capture the spread are the same as they were in the oil days, just reversed: US remote comp, a TN visa, or a move. I made the move. The census and the IMF both have a row for that decision, and the row keeps getting wider.

## Caveats

- GDP per person is an average, not a median, and it counts oil royalties and corporate income that never touch a pay stub. The province and state table inherits that: Alberta's number is flattered by energy income, DC's by being a capital. The diaspora medians are the check on lived income, and they point the same direction.
- IMF figures for 2025 are estimates and 2026 onward are WEO forecasts. The 2024 ratios are the last hard ground; the forecast is quoted as the IMF's view, not as fact.
- Provincial GDP uses expenditure-based current-price GDP (StatCan 36-10-0222) divided by July population estimates (17-10-0005), converted at the 2024 annual average DEXCAUS rate of 1.370. A PPP conversion would lift every province several rungs; the ranking inside Canada would not change.
- The driver models run on 24 annual observations. Treat SHAP rankings as structured description. The LOOCV result (OLS wins) is reported in `data/model.json` rather than hidden.
- The diaspora comparison mixes StatCan median total income (2020) with ACS median earnings (2023). The 2026-09-24 build in this repo did the fuller harmonization, including household income (US Asian median household income $116,503), and found the same direction.

## Sources

- IMF World Economic Outlook, DataMapper API: NGDPDPC, PPPPC, LP, NGDPD, NGDP_RPCH for Canada and the US. `https://www.imf.org/external/datamapper/api/v1/...`
- FRED (Federal Reserve Bank of St. Louis), fredgraph CSV: NYGDPPCAPKDCAN / NYGDPPCAPKDUSA (World Bank GDP per capita, constant 2015 US$), SPPOPGROWCAN / SPPOPGROWUSA, DEXCAUS (CAD per USD), DCOILWTICO (WTI), QCAN628BIS / QUSN628BIS (BIS real house prices), LRUNTTTTCAM156S, UNRATE, and BEA state GDP (XXNGSP) with Census state population (XXPOP).
- Statistics Canada tables 36-10-0222-01 and 17-10-0005-01, full-table CSV downloads from www150.statcan.gc.ca.
- Diaspora: Statistics Canada 2021 Census table 98-10-0331 and US Census Bureau ACS 2023, as extracted in this repo's 2026-09-24 build (`same-grandparents-different-deal`), reused with provenance recorded in `data/diaspora.json`.

## Layout

```
the-canadian-discount/
├── src/
│   ├── 01_fetch.py      # IMF + FRED + StatCan + archived diaspora extracts
│   ├── 02_analysis.py   # ratios, 2019-2024 decomposition, league table, findings.json
│   ├── 03_model.py      # XGBoost + SHAP vs OLS, LOOCV, decomposition, projections
│   └── 04_charts.py     # all figures + site/data.js
├── data/                # imf_weo.csv, fred_core.csv, fred_states.csv,
│                        # statcan_prov_gdp.csv, statcan_prov_pop.csv, diaspora.json,
│                        # annual_panel.csv, indexed_2019.csv, league_table.csv,
│                        # model_panel.csv, findings.json, model.json
├── charts/              # canyon, bigger_not_richer, league, drivers, shap, diaspora
└── site/
    ├── index.html       # salary calculator: market FX vs PPP vs the 2011 ghost
    └── data.js          # generated by 04_charts.py
```
