# Sweat Is Not Sweat — your job's exercise doesn't count, and neither does your step count's alibi

**Musing with Mike · daily build #33 · 2026-10-09 · topic: fitness**

Every fitness product on earth counts minutes. Runkeeper, Apple Watch, your employer's wellness portal — they all treat a minute of hauling boxes and a minute of chosen exercise as the same currency. The body doesn't. This build asks 5,365 working-age Americans (NHANES 2015–2018, measured HbA1c and BMI, activity self-reported by domain) a simple question: does sweat pay the same when it's your job?

Short answer: no. Leisure exercise pays. Work activity, at any dose I could measure, pays nothing detectable. And who gets which kind of sweat turns out to be an income story — which makes it a market story.

**Try it:** open [`explorer.html`](explorer.html) — enter your age, income band, leisure minutes, work minutes, and sitting hours. It returns your model-predicted probability of fair/poor health and where your leisure exercise ranks inside your income group.

## Findings

**1. The paradox, priced.** Per 600 MET-minutes/week of leisure exercise (roughly: meet the guidelines), adjusted odds fall for every outcome: diabetes OR 0.91 (p=0.0001), obesity 0.92, fair/poor health 0.88, dysglycemia 0.97. Stack four guideline-units (2,400 MET-min) and diabetes odds are ~0.67. The same dose at work: OR 0.99–1.01 on all four outcomes — for obesity it's 1.007, a hair *worse* than nothing (p=0.035). The raw curves say it louder: dysglycemia prevalence falls 38.6% → 18.6% across leisure bins and just wobbles (33% → 27%, non-monotone) across work bins. A warehouse shift is not a workout. See `charts/01_paradox_forest.png`, `charts/03_dose_response.png`.

**2. Sweat is allocated by income, not by need.** Share meeting exercise guidelines through leisure: 25.0% of low-income adults (<1.3× poverty) vs 45.8% of high-income (>3.5×). Median leisure dose: 0 vs 480 MET-min/week. By education it's starker: 24.1% (high school or less) vs 52.0% (college+). Meanwhile occupational activity peaks in the *middle* income band (median 362 MET-min/week vs 0 at the top). The people whose jobs already move them are the people least likely to get the kind of movement that pays. See `charts/02_inequality.png`.

**3. Rich people sit the most — and buy their way out of it.** High-income adults report the most sitting (7.1 h/day vs 5.5 for low-income). Sitting is expensive: each extra 2 h/day carries OR 1.13 for obesity and 1.11 for fair/poor health. But the top band pairs the chair with the highest leisure dose. The sitting tax is real; it's just regressive. The person who can't buy the offset pays it.

**4. The model can hear leisure. It can't hear work.** XGBoost on fair/poor health (AUC 0.74): SHAP ranks income first (0.50), then BMI, education, age — and leisure exercise fifth (0.25), three times the signal of work activity (0.08). Binned SHAP means: leisure's contribution falls steadily from +0.19 at zero dose to −0.52 at 2,400+ MET-min; work's contribution hovers at zero at every dose. See `charts/04_shap.png`.

**5. Giving poor adults rich adults' exercise habits barely moves diabetes.** Counterfactual: swap low-income adults' leisure distribution for the high-income one (matched on age and sex, 20 draws). Predicted diabetes prevalence: 17.0% → 16.1% — about a 5% relative cut, not a gap-closer. Income itself is the #1 SHAP feature for a reason. Exercise access is a real lever; it is not *the* lever, and any wellness pitch that says otherwise is selling something.

**6. The weekend warrior gets no penalty slip.** Among the 1,800 guideline-meeters, only 12% compress their exercise into ≤2 days. Their adjusted odds vs spread-out exercisers: dysglycemia 1.01, obesity 0.92, fair/poor health 1.24 — none significant, confidence intervals wide enough to include modest effects either way. Two honest readings: compressed exercise is not obviously punished, and this dataset can't acquit it completely. Your Saturday long run is probably fine. See `charts/05_weekend_warrior.png`.

**7. The income gradient survives inside the "model minority."** Non-Hispanic Asian adults (n=715): 39.2% meet guidelines overall — but 26.6% in the low-income band vs 46.4% in the high-income band, nearly the same spread as everyone else. They also report the lowest fair/poor health (12.3%) of any group, which says as much about how health gets *reported* across cultures as how it's lived. Money buys chosen exercise in every group I sliced. There is no cultural exemption.

## The market read

The fitness industry sells leisure exercise to the segment that already has it: high-income, college-educated, chair-bound by day, compensated by choice. The population with the worst receipts — physical job, no chosen exercise, no offset for sitting — is barely a customer. No gym chain prices for the warehouse worker's actual problem, which isn't motivation; it's that his body already spent its adaptation budget at work and got nothing bankable for it. Whoever builds recovery, sleep, and ten chosen minutes for that segment is selling into the emptiest shelf in fitness.

## Method

- `src/analyze.py` — one reproducible pipeline: downloads the CDC XPT files, cleans GPAQ activity per WHO convention (vigorous = 8 METs, moderate = 4; >16 h/day reported activity excluded as implausible), pools NHANES 2015–16 + 2017–18, adults 20–65 with exam + lab + activity data (analytic n = 5,365 of 8,596 age-eligible).
- Adjusted odds ratios: binomial GLMs (statsmodels, HC1 robust SEs) controlling age, sex, race/ethnicity, education, family income-to-poverty ratio, and cycle. Headline dysglycemia result re-run survey-weighted as a sensitivity check: leisure OR 0.945 (p=0.003), work 0.997 — same story. Population shares and dose-response curves use pooled MEC weights (WTMEC2YR/2).
- XGBoost (400 trees, depth 3) + SHAP (TreeExplainer) on a stratified 70/30 split for the fair/poor-health model.
- Counterfactual: quantile-matched leisure-distribution swap within sex × age-band strata, 20 Monte Carlo draws (SD across draws 0.0005 — the estimate is stable; its assumptions are the caveat, not its arithmetic).
- `data/nhanes_pooled.csv` — the derived analytic dataset. `output/results.json` — every number above. `output/explorer_model.json` — the explorer's fitted model.

Reproduce: `pip install -r requirements.txt && python src/analyze.py`.

## Caveats, stated flatly

Cross-sectional and self-reported: sick people exercise less, so part of leisure's "effect" is selection running backwards — the dose-response shape and the work/leisure asymmetry are harder to explain away than any single odds ratio, but causality is not proven here. GPAQ self-report overstates activity; occupational activity in particular gets reported in heroic doses. The paradox literature (Holtermann and successors, mostly European cohorts with mortality endpoints) finds the same asymmetry prospectively, which is why I trust the direction more than the decimals. Self-rated health is a reporting behavior as much as a health state — see finding 7.

## Sources

- CDC/NCHS NHANES 2015–2016 and 2017–2018 public data files (DEMO, PAQ, BMX, HSQ, DIQ, GHB, HDL): https://wwwn.cdc.gov/nchs/nhanes/
- WHO Global Physical Activity Questionnaire (GPAQ) analysis conventions (MET assignments, plausibility screens).
- Holtermann A et al., the "physical activity paradox" literature (e.g., *European Heart Journal* 2018; *British Journal of Sports Medicine* 2018) — leisure vs occupational activity and mortality.
- Hamer M et al. 2017 and Dos Santos et al. 2022 — weekend-warrior pattern vs mortality/morbidity (the prospective backdrop for finding 6).
