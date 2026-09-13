# Data sources

## 1. ClinicalTrials.gov API v2 (Part 1)
- Endpoint: `https://clinicaltrials.gov/api/v2/studies`
- Accessed 2026-09-13. Queries like `?query.term=<term>&pageSize=1000&countTotal=true` with pagination via `nextPageToken`.
- Search terms (mapped to labels in `src/01_fetch_trials.py`): "cold water immersion", "sauna", "photobiomodulation", "intermittent fasting", "time restricted eating", "nicotinamide mononucleotide", "metformin aging", "creatine supplementation", "mindfulness meditation", "breathwork", "light therapy circadian", "ketogenic diet", "ashwagandha", "magnesium supplementation", "zone 2 exercise".
- Cached summary: `data/trials_summary.json`. Raw records were not stored (each term's full records are several MB); re-run `src/01_fetch_trials.py` to regenerate.

## 2. NHANES 2017–March 2020 pre-pandemic (Part 2)
- Publisher: CDC National Center for Health Statistics (public domain).
- Files (SAS XPT, in `data/nhanes/`): P_DEMO, P_SLQ, P_BMX, P_GHB, P_BPQ, P_DIQ.
- Download pattern from the published CDC data pages (e.g. the 2017–2020 Questionnaire datapage links):
  `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/<FILE>.xpt`
- Key variables: `SLD012`/`SLD013` (usual weekday/weekend sleep hours), `BMXBMI` (measured BMI), `LBXGH` (HbA1c %), `BPQ020` (ever told had hypertension), `DIQ010` (ever told had diabetes), `WTMECPRP` (MEC exam weight), `RIDAGEYR`, `RIAGENDR`.
- Analytic sample: adults 20+ with valid 2–14h habitual sleep, n = 9,110 unweighted.
- Reproduce: place the six `.xpt` files in `data/nhanes/` and run `src/02_sleep_analysis.py`.
