# The Wall Has a Fingerprint — 185,000 marathons and the math of blowing up

**Musing with Mike · daily build #13 · 2026-09-20 · topic: fitness**

Everyone who has run a marathon knows the wall. Almost nobody can see it coming.
This project says you can: from 158,674 Berlin Marathon finishes (2016–2019) and
26,630 Boston Marathon finishes (2016), with timing mats every 5k, I cluster
pacing into five archetypes, train a model that predicts who blows up from
their 25k splits, and price the most expensive mistake in endurance sports —
going out too fast.

**Try it:** open [`explorer.html`](explorer.html) — enter your 5k/10k/15k/20k/25k
splits and get your archetype, predicted finish, and bonk probability.

## Findings

**1. There are five kinds of marathoners, and only 35% are metronomes.**
K-means on normalized pacing profiles (each 5k vs your own average pace):
*Metronome* (35.2%) — flat the whole way. *The Fade* (33.7%) — gentle late
slowdown. *The Wall* (15.4%) — out 9% hot, pay 20% late. *The Crash* (10.7%) —
out 16% hot, detonate. *The Collapse* (5.0%) — out 18% hot, finish 33% slow.
Median finishes: Metronome 3:49 → Fade 4:07 → Wall 4:20 → Collapse 4:44 →
Crash 5:13. The fastest starters finish last. See `charts/01_archetypes.png`.

**2. The wall has a fingerprint, and it shows up at 20k.**
A bonk = running the last 12.2k at least 12% slower than the first 30k.
32% of Berlin finishers bonk (3.8% of sub-3 runners, 55% of 4:30+ runners).
An XGBoost trained on 2016–2018 and tested on 2019 predicts bonks from
25k splits with AUC 0.819. SHAP says the #1 early tell is your **20–25k pace** —
the damage is visible a full 10k before the wall. Top-risk decile: 80% bonk.
Bottom decile: 3%. See `charts/02_shap_bonk.png`.

**3. The tax on optimism is 5–9 minutes, at every ability level.**
Match runners by 10–20k pace (same engine), then compare hot starters
(first 5k ≥5% faster than their 10–20k pace) vs even starters. Hot starters
finish 5–9 minutes slower — for 2:50 runners and 5:30 runners alike.
The cruel part: the slower the runner, the more likely the hot start
(3% of the fastest group, 61% of the slowest). See `charts/03_tax_on_optimism.png`.

**4. Boston's qualified field paces worse than Berlin's open field — the course is a trap.**
Boston 2016 bonk rate: **49.7%** vs Berlin's 32.0%. Only 17.5% of Bostonians
are metronomes vs 35.2% in Berlin. Why: Boston starts steeply downhill
(everyone's first 5k lies to them), then the Newton hills hit at 28–34k —
exactly where glycogen runs out. Qualification selects for fitness, not for
pacing discipline, and the course punishes exactly that. See `charts/05_boston_vs_berlin.png`.

**5. The BQ standard is mispriced by age and sex.**
Only **36.1%** of Boston 2016 finishers beat their own qualifying standard on
race day. But the bar isn't evenly set: women 55–59 re-clear it 53.9% of the
time vs 30.3% for men the same age; women 60–64, 56.1% vs 33.0%. Older women's
standards are soft relative to the field — the arbitrage is real, and the
downhill "qualifier mill" races prove the market knows it: runners who
qualified at REVEL Mt Charleston ran Boston **20% slower** than their
qualifying time (MarathonInvestigation, 2017). See `charts/04_boston_beat_bq.png`.

## Data

- **Berlin Marathon 2016–2019** (158,674 finishers after cleaning): 5k/10k/…/40k
  cumulative splits, sex, nationality. Compiled by AndrewMillerOnline from
  official timing results ([marathon-results](https://github.com/AndrewMillerOnline/marathon-results)).
  Caveat from the compiler: gathered from across the web, accuracy not guaranteed.
- **Boston Marathon 2016** (26,479 finishers): 5k–40k splits, age, sex, from
  official B.A.A. results via rojour's
  [boston_results](https://github.com/rojour/boston_results) scrape.
  Race-day conditions: ~70°F at the Hopkinton start, high 61°F in Boston —
  well above ideal marathon weather (runner reports via
  [letsrun](https://www.letsrun.com/forum/flat_read.php?thread=7207209);
  [Boston Discovery Guide](https://www.boston-discovery-guide.com/boston-marathon-weather.html)).
- **BQ standards**: BAA qualifying standards in effect for 2016 (e.g. M18–34
  3:05, W18–34 3:35), embedded in `src/04_boston_bq.py`.
- **Qualifier-arbitrage table**: [MarathonInvestigation, "2017 Boston Marathon
  Results – First Look at The Data"](https://www.marathoninvestigation.com/2017/04/boston-2017-quick-look-numbers.html).

## Method

1. `src/01_clean.py` — parse times, derive per-5k segment paces and
   relative-to-average pacing profiles. → `output/berlin_clean.pkl`, `output/boston_clean.pkl`
2. `src/02_archetypes.py` — k-means (k=5) on relative pacing profiles; silhouette
   checked k=4–6; clusters hand-labeled from centroid shapes. → `charts/01_archetypes.png`
3. `src/03_wall_model.py` — XGBoost classifier on **absolute** early paces only
   (relative paces leak: their denominator includes the late segments being
   predicted — caught an AUC 0.992 leak and fixed it), train 2016–18 / test 2019;
   SHAP explanations; matched "tax on optimism" comparison. → `charts/02_shap_bonk.png`,
   `charts/03_tax_on_optimism.png`
4. `src/04_boston_bq.py` — BQ-standard lookup by age/sex; Boston-vs-Berlin
   archetype assignment via Berlin centroids. → `charts/04_boston_beat_bq.png`,
   `charts/05_boston_vs_berlin.png`
5. `src/05_explorer.py` — logistic-regression bonk model + archetype decay factors
   baked into a self-contained `explorer.html`.

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python src/01_clean.py
.venv/bin/python src/02_archetypes.py
.venv/bin/python src/03_wall_model.py
.venv/bin/python src/04_boston_bq.py
.venv/bin/python src/05_explorer.py
```

Raw CSVs are vendored in `data/` (Berlin 2016–2019, Boston 2016).
