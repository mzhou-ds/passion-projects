# Provenance

- **Fertility:** UN World Population Prospects (2024 revision series as
  distributed) via Our World in Data grapher file
  `children-per-woman-UN.csv` (period total fertility rate, 1950-2023).
  Fetched 2026-10-23 by `src/01_fetch.py`; committed as
  `data/fertility_un_owid.csv`. Headline 2023 values used: United States
  1.624, Canada 1.349, China 0.999, World ~2.25 (see file).
- **Microdata:** General Social Survey cumulative cross-section file,
  1972-2024 (NORC at the University of Chicago), via Kieran Healy's
  `gssr` mirror (github.com/kjhealy/gssr, `data/gss_all.rda`).
  `data/gss_extract.csv` is a 16-variable extract (year, age, cohort,
  sex, race, educ, degree, marital, divorce, childs, sibs, attend,
  relig, region, wrkstat, wtssall) produced with the same extraction
  pattern as the 2026-10-14 build in this repo. Weights: `wtssall`.
  `sibs` is top-coded at 6 in the GSS public file.
- **Kinship model:** original to this build; formulas and assumptions
  are stated in full in `src/02_kinship_model.py`. Projections past
  2023 hold TFR flat at 2023 levels and are labelled `projected`.
- **Context literature (cited, not used as data):** Alburez-Gutierrez
  et al. (2023), kinship projections in *PNAS Nexus*; Verdery et al.
  (2020), kinlessness projections in *PNAS*. The cousin-product
  framing, the three-country period model, and all headline numbers
  here are computed from the two sources above, not taken from either
  paper.
