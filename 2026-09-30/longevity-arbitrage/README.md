# The Longevity Arbitrage — pricing an hour of exercise like an investor

**Musing with Mike · daily build #22 · 2026-09-30 · topic: fitness**

Everyone treats exercise like a virtue. Investors would treat it like a portfolio: every minute is capital, and capital should go where the return is highest. So I priced it.

Five peer-reviewed dose-response studies, one model: smooth curves through the published hazard ratios, a life-expectancy conversion fitted from Moore et al. 2012 (reproduces their own numbers within 0.25 years), and a grid-search optimizer that allocates a fixed weekly budget across modalities. Then an interactive calculator so you can price your own week.

**Try it:** open [`calculator.html`](calculator.html) — enter your current exercise, set your budget, and it tells you where the next hours should go and what each 30-minute block buys.

## Findings

**1. The VILPA arbitrage: 35 minutes beats 10 hours.**
UK Biobank, device-measured, people who did zero structured exercise (Stamatakis 2022): three short vigorous bursts a day — stairs, fast walking uphill, ~4.5 min/day total — cut all-cause mortality 39% (HR 0.61). That's the same risk reduction as 600+ minutes a week of structured aerobic. Per minute, its return is ~12x the first minute of conventional cardio. A 2025 follow-up: one minute of vigorous ≈ 53 minutes of light activity. The highest-ROI asset in the entire dataset is free and takes no gym.

**2. Your first hour of exercise should be strength, not cardio.**
At a 60-min/week budget, the optimal portfolio is 40 minutes of lifting + 20 of cardio — HR 0.80, +1.8 years. Strength's first 40 minutes (RR 0.83, Momma 2022) pays out faster than cardio's first hour. Nobody's podcast told you that.

**3. Strength has a ceiling, and past it you're paying to lose.**
The dose-response is J-shaped: ~40 min/week is the sweet spot, the benefit holds to ~140, then it curves back up. Marginal return at 140 min is negative. More lifting past that point is just expensive cardio.

**4. The efficient frontier is simple: lift to 40, then run.**
Across budgets from 60 to 420 min/week, the optimizer never puts more than ~40 minutes in strength — every marginal minute after that goes to aerobic. A 3-hour budget: 140 aerobic + 40 strength → HR 0.67, +3.3 years. The combined aerobic+strength portfolio cuts risk ~40% (multiplicative estimate HR 0.51; Momma observed 0.60 directly — either way, better than either alone).

**5. Cardio's 4th weekly hour is worth a fifth of the 1st.**
Marginal return on aerobic minutes: 7,100 min of life per minute at dose zero → 5,100 at 150 min → 3,300 at 300 → 1,400 at 450. Going from zero to meeting guidelines (150 min) buys ~1.9 years. Quintupling it to 750 buys ~2 more. Diminishing returns bite harder than the fitness industry admits.

**6. The sitting tax is real, and TV doesn't get a pass.**
Over 8 hours of sitting + no exercise: HR 1.59 — worse than the upside of most exercise. 60–75 min/day of moderate activity neutralizes it (Ekelund 2016, n≈1M). But 5+ hours of TV a day keeps you at 1.16 even at maximum activity. The couch is not priced in.

## Method

- `data/evidence.csv` — every number, sourced, with study/dose/metric. Verified points vs curve-shape placeholders are labeled.
- `src/model.py` — PCHIP dose-response curves through verified points; life-expectancy conversion `years = -8.29·ln(HR)` fitted from Moore 2012; multiplicative risk combination (independence assumption); grid-search portfolio optimizer. VILPA is modeled as a *substitute* for structured aerobic (its evidence comes from nonexercisers), not a stackable bonus.
- `src/analyze.py` — reproduces all charts and key numbers. `pip install -r requirements.txt && python src/analyze.py`.
- `output/curve_tables.json`, `output/frontier.json` — machine-readable curves and the efficient frontier for the calculator.

## Caveats, stated flatly

Observational cohorts, so healthy-user bias is in the mix — fit people differ from unfit people in ways studies can't fully adjust away. Hazard ratios from different studies on different populations don't compose perfectly; the multiplicative stacking is the standard independence assumption, and Momma's directly-observed 0.60 says it's in the right neighborhood. Relative risks are population averages, not your personal number. The direction is the finding; the decimals are decoration.

## Sources

- Arem H et al., *JAMA Internal Medicine* 2015 — 661,137 adults, leisure-time activity dose-response.
- Momma H et al., *British Journal of Sports Medicine* 2022 — 16-cohort meta-analysis, resistance training.
- Stamatakis E et al., *Nature Medicine* 2022 — device-measured VILPA, 25,241 nonexercisers (UK Biobank).
- Stamatakis/Ahmadi, *Nature Communications* 2025 — vigorous-vs-light equivalence.
- Ekelund U et al., *The Lancet* 2016 — physical activity, sitting time, ~1M adults.
- Mandsager et al., *JAMA Network Open* 2018; Kodama et al., *JAMA* 2009 — cardiorespiratory fitness.
- Moore SC et al., *PLoS Medicine* 2012 — life-expectancy gains by activity dose.
- WHO 2020 physical activity guidelines.
