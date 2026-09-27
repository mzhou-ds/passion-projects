# The Goalie Is a Lottery Ticket

**Why the NHL's most expensive position is its most random — and what that means for the Oilers.**

Every spring, the same argument. The Oilers lose, and everyone blames the goalie. This year I priced the position instead of arguing about it. Four pieces:

1. **Repeatability.** Year-over-year correlation of GSAx/60 for 1,083 goalie-seasons (2015–2025), vs. forwards' chance creation.
2. **The contract market.** 2026-27's 30 highest-paid goalies (PuckPedia via USA Today) against their trailing-3-year GSAx.
3. **Playoffs.** 150 series reconstructed game-by-game from the NHL API: does the better regular-season goalie win?
4. **Edmonton.** What the Oilers' crease actually costs them, in standings points.

## The findings

**1. Goaltending barely carries over. Nothing else in hockey looks like this.**

A goalie's GSAx/60 correlates with next season's at r = 0.10. Save percentage: 0.14. A forward's chance creation: 0.73. Even a three-year track record predicts next year at only r = 0.18. Decompose the variance and 5% of it is the goalie — the rest is noise, workload, and the team in front of him. Forwards: 64% is the player.

Jeremy Swayman is the whole story in one career: +0.54, then −0.28, then +0.35 GSAx/60 in three straight seasons. Dustin Wolf signed for $7.5M after a +5.1 rookie year, then posted −10.2. The league keeps paying for the good year. The good year keeps not repeating.

**2. The market prices the past. The past is noise.**

2026-27 cap hits correlate with trailing-3-year GSAx at r = 0.48 — GMs absolutely pay for what a goalie just did. The market line works out to about $37K per goal of past GSAx. But past GSAx predicts future GSAx at r = 0.18, so each $1M is buying roughly five goals of *expected* future value and a pile of variance.

The bill: Shesterkin's $11.57M is $3.8M over the market line. Saros makes $7.74M on a three-year GSAx of *−43.9*. Meanwhile 48% of last season's above-expected saves came from goalies making under $4M. The top-30 paid consume $198M of league-wide goalie cap for barely half the positive GSAx.

**3. In April, the regular-season goalie edge is a coin flip.**

The team with the better regular-season goalie won the series 51.3% of the time. The team with the better skaters: 57.3%. The killer split: win the goalie battle but lose the skater battle, and you win the series 31% of the time. Win the skaters but lose the goalie battle: 58%. A logistic model on standardized differentials gives the goalie edge a McFadden R² of 0.001 — it explains literally nothing. One standard deviation of skater quality nearly doubles your series odds. One standard deviation of goaltending does nothing.

**4. The Cup still goes through a hot goalie. You just can't buy the heat.**

Seven of the last ten champions had a top-5 playoff crease. Their median *regular-season* goaltending rank was 9th. Tampa Bay's 2021 run rode a +22.6 GSAx heater; Colorado won in 2022 with the 15th-ranked playoff crease. The heat is real and it is unpredictable — which is exactly why you don't pay $11M for the guy who was hot last spring.

**5. Edmonton, specifically.**

About 3 goals of differential buys one standings point. The 2025-26 Oilers finished with 93 points and a team GSAx of −18.8 — negative every season since 2017, a decade of below-average goaltending. An average crease is worth ~6 points to them. A genuinely good starter is worth ~9.5. That's the gap between a wild card and a division seed, and it costs less than a second-pair defenseman.

As for Jarry: $5.375M through 2028, trailing-3-year GSAx of −21.7, ranking 8th of 11 in his own $5–6M pay band. Logan Thompson (+38.8) costs $475K more. The Oilers didn't buy the worst contract in the band. They bought a lottery ticket at full price.

## The takeaway

Don't buy the $8M goalie. Don't buy the $5.4M goalie either. When a position is 95% noise, the optimal strategy is the one finance figured out a century ago: diversify. Two cheap, independent crease draws halve your variance versus one expensive one — and the data says the expensive one isn't even better on average. The Cup goes to whoever gets hot. You can't pick the hot goalie in advance. So stop paying like you can.

## How it was built

- `src/01_prepare.py` — MoneyPuck goalie/team CSVs (2015–2025, regular + playoffs) → `data/processed/goalie_season.csv`, `team_season.csv`; team points from the NHL stats API. (No `requests.Session` — keep-alive hangs through this proxy; fresh `requests.get` per call.)
- `src/01b_series.py` — 150 playoff series reconstructed from NHL schedule API game scores (2019-20 bubble excluded), per-season caches in `data/processed/`.
- `src/02_repeatability.py` — YoY autocorrelation, trailing-3yr predictiveness, ANOVA intraclass correlation. → `figures/01_repeatability.png`
- `src/03_market.py` — salary join (top-30 goalie cap hits, USA Today/PuckPedia Sep 2026), market-line regression, over/underpaid residuals. → `figures/02_market_scatter.png`, `figures/03_value_gap.png`
- `src/04_playoffs.py` — series hit rates, logistic regression (McFadden R², odds ratios), Cup-winner playoff-GSAx ranks. → `figures/04_series.png`
- `src/05_oilers.py` — goals→points OLS, Oilers counterfactuals, $5–6M pay-band benchmark. → `figures/05_oilers.png`

## Sources

- MoneyPuck season summaries 2015–2025 (goalies, teams, skaters), moneypuck.com/data.htm — free for non-commercial use, credited here.
- NHL API (api-web.nhle.com schedule; api.nhle.com stats) for series scores and team points.
- Goalie cap hits: USA Today, "Who are the NHL's highest-paid players for 2026-27?" (Mike Brehm, Sep 25, 2026), figures from PuckPedia.
- GSAx = MoneyPuck flurry-adjusted goals saved above expected, all situations.
