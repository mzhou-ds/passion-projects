# Sources

## Biological variation (CVi, CVg)
- Ricos C, Alvarez V, Cava F, Garcia-Lario JV, Hernandez A, Jimenez CV, Minchinela J,
  Perich C, Simon M. "Current databases on biologic variation: pros, cons and progress."
  Scand J Clin Lab Invest 1999;59:491-500; database updated 2014. Full table mirrored at
  Westgard QC: https://www.westgard.com/clia-and-quality-regulation-requirements/quality-requirements/biodatabase1.html
  (raw copy saved as data/ricos_2014_bv_database_westgard.html; parsed by src/01_parse_bv.py).
- EFLM Biological Variation Database, meta-analysis estimates, https://biologicalvariation.eu/
  (accessed 2026-11-27): 25-hydroxyvitamin D3 CVi 6.8% (95% CI 1.8-12.8), CVg 37.6%.
- Bio-Rad "EFLM Biological Variation Standards" (2024), reproducing the 2021 EFLM database
  values: hsCRP CVi 58.9%, CVg 77.4%; cortisol CVi 16.1%.
- Gough A, Sitch A, Ferris E, Marshall T (2024). Within-subject variation of C-reactive
  protein and high-sensitivity CRP: a systematic review and meta-analysis. PLoS ONE 19(11):
  e0304961. Median within-subject CV 0.44 for hsCRP; EFLM pooled CVI 0.59 (95% CI 0.53-0.66).
- Cavalier E et al. (2021). Analytical Performance Specifications for 25-Hydroxyvitamin D
  Examinations. Nutrients 13(2):431. EuBIVAS CVi 5.8-7.1% over 10 weeks; long-term
  within-person CV 14.9% over 5 years in PLCO (Cancer Data Access System publication).
- Coskun A et al. / EuBIVAS (2024). Biological variation data for testosterone, FSH,
  prolactin, LH and DHEA-S in men. Clin Chim Acta. Testosterone CVi 10%.
- Fraser CG. Biological Variation: From Principles to Practice (AACC Press, 2001):
  desirable analytical imprecision = 0.5 x CVi; RCV = 2.77 x sqrt(CVi^2 + CVa^2);
  index of individuality II = CVi / CVg; II < 0.6 means population reference intervals
  have limited value for the individual (Harris EK, 1974).
- Brambilla DJ et al. Intraindividual variation in serum testosterone and other hormones
  in men (Boston Area Community Health Survey). Conclusion: "one sample is generally not
  sufficient to characterize an individual's hormone levels."

## "Optimal" bands (what the longevity-testing market sells)
- Longevity Benchmark, "Normal Vs Optimal Lab Ranges (2026)", medically reviewed by
  Michael Teplitsky MD, reviewed 2026-08-06:
  https://www.longevitybenchmark.com/biomarkers/normal-vs-optimal/
  Fasting insulin 2-5, fasting glucose 75-90, HbA1c 4.9-5.3, ApoB <80, hsCRP <0.5,
  homocysteine <8 (via its table; homocysteine <8 also in BioAccelera), ferritin men
  50-150, vitamin D 40-60, TSH 0.5-2.5. Same page notes the 1-in-20 panel effect:
  a 20-marker panel flags at least one value ~64% of the time in a healthy person.
- The Biological Edge, "The Optimal Male Bloodwork Panel (2025)":
  https://www.thebiologicaledge.com/labs/optimal-male-bloodwork-panel
  Total testosterone 600-900 ng/dL, SHBG 20-40 nmol/L, vitamin D 50-70 ng/mL.
- BioAccelera, "The Essential Bloodwork Guide: What to Test and Why":
  https://www.bioaccelera.com/blog/bloodwork-guide-what-to-test
  Triglycerides optimal below 70, hsCRP below 0.5, homocysteine below 8,
  testosterone 600-900; notes afternoon testosterone runs 20-30% lower than morning.
- Biohack Ageless, "The Longevity Blood Panel":
  https://www.biohackageless.com/bloodwork/longevity-blood-panel-biomarkers.html
  hsCRP <0.5 optimal; vitamin D 40-60; notes hsCRP can go from 0.3 to 50+ during a cold.
- Longevity Atlas, Biomarkers: https://www.longevityatlas.hu/en/biomarkers
  Lp(a) optimal <75 nmol/L (<30 mg/dL).
- NCEP Adult Treatment Panel III: LDL cholesterol optimal <100 mg/dL.

## Prices (context, checked 2026-11-27)
- Function Health: $499/year membership for 100+ labs, quarterly testing.
- InsideTracker Ultimate plan: ~$589 (single test) for 48 biomarkers.
- These are the products whose core promise ("know your optimal") this build tests.
  Prices are context only; no price is used in any computation.
