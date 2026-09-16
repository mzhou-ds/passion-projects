# Sources

Every number in this project is traceable to a published source. Datasets marked
"transcribed" were copied from the cited report/paper into CSV with per-row
citations; the Cantril panel was downloaded in full.

## Primary datasets

1. **AEI Survey Center on American Life — "The State of American Friendship:
   Change, Challenges, and Loss" (Daniel A. Cox, June 2021).**
   American Perspectives Survey, May 2021 (N = 2,019 US adults); 1990 figures from
   Gallup comparison surveys. → `data/aei_friendship.csv` (transcribed).
   Report PDF: https://aei.org/wp-content/uploads/2021/07/The-State-of-American-Friendship.pdf
   Companion essay: https://www.aei.org/commentary/american-men-suffer-a-friendship-recession/

2. **Meta–Gallup Global State of Social Connections (fieldwork 2022).**
   Nationally representative surveys in 142 countries/territories, adults 15+.
   Loneliness: "very or fairly lonely" — 24% global, 27% ages 19–29, 17% ages 65+.
   → `data/gallup_loneliness_by_age.csv` (transcribed).
   https://news.gallup.com/opinion/gallup/512618/almost-quarter-world-feels-lonely.aspx

3. **World Happiness Report 2025, Chapter 5 — "Connecting with others:
   How social connections improve the happiness of young adults"
   (Rui Pei & Jamil Zaki, Stanford).**
   19% of young adults globally had no one to count on for social support in 2023
   (+39% vs 2006, Gallup World Poll); Global Flourishing Study (22 countries/regions):
   17% of young adults report no close relationships; Japan >30% isolated;
   Nigeria/Egypt/Philippines <10%. → `data/whr2025_young_adults.csv` (transcribed).
   PDF: http://gallup.com/file/analytics/658439/Downloads/World%20Happiness%20Report_2025_Chap5.pdf

4. **Our World in Data / Wellbeing Research Centre (2026) — "Self-reported life
   satisfaction" [dataset]; original data: World Happiness Report / Gallup World Poll.**
   Country-year Cantril ladder panel, 2011–2025. → `data/cantril_ladder_owid.csv`
   (downloaded in full by `fetch_data.py`).
   https://ourworldindata.org/grapher/happiness-cantril-ladder

5. **Holt-Lunstad, Smith & Layton (2010), "Social Relationships and Mortality Risk:
   A Meta-analytic Review," PLoS Medicine 7(7): e1000316.**
   148 studies, 308,849 participants, avg. follow-up 7.5 years. Overall OR = 1.50
   (95% CI 1.42–1.59); complex social integration OR = 1.91; living alone OR = 1.19.
   → `data/mortality_effect_sizes.csv` (transcribed).
   https://doi.org/10.1371/journal.pmed.1000316

6. **Pantell et al. (2013), American Journal of Public Health — NHANES social
   network index and mortality.** Social isolation HR 1.62 (men) / 1.75 (women);
   smoking HR 1.72 / 1.86; hypertension HR 1.16 / 1.32. → `data/mortality_effect_sizes.csv`.
   https://www.medscape.com/viewarticle/811133

## Supporting literature (cited in essay/app, not re-analyzed)

- Dunbar, R.I.M. (1992). "Neocortex size as a constraint on group size in primates."
  *Journal of Human Evolution.* (Dunbar's number; layered social networks 5–15–50–150.)
- Roberts, S.G.B. & Dunbar, R.I.M. (2011). "The costs of family and friends."
  *Journal of Personality.* (Social time budgets; tie decay without contact.)
- Waldinger, R. & Schulz, M. (2023). *The Good Life.* (Harvard Study of Adult
  Development: 85+ years, 724 men + families — relationships predict health/happiness
  in old age better than cholesterol or wealth.)
- U.S. Surgeon General (2023). *Our Epidemic of Loneliness and Isolation* —
  advisory framing loneliness as a public-health crisis.
- BLS American Time Use Survey — socializing time benchmarks referenced in the app.

## Caveats

- The 1990↔2021 AEI comparison spans a change in survey mode (Gallup phone in 1990
  vs. online panel in 2021); the direction of the trend is well supported, the exact
  magnitude is debated (see e.g. scienceblog.com coverage, Aug 2026).
- Transcribed toplines inherit rounding from the published reports; middle bands in
  chart 02 are derived from reported totals and labeled as such.
- The Friendship Budget app is an illustrative model, not an empirical estimate of
  optimal social time.
