# Data sources

All fetched 2026-10-11. No API keys required.

- **ClinicalTrials.gov API v2** (`https://clinicaltrials.gov/api/v2/studies`, `query.intr` per molecule, pageSize 1000, de-duplicated by NCT ID): semaglutide, tirzepatide, liraglutide, dulaglutide, exenatide, retatrutide, albiglutide, lixisenatide → `trials.csv` (2,013 unique trials).
- **NCBI PubMed E-utilities** esearch, `"term"[tiab] AND YEAR[dp]`, 2010–2026, molecules + metformin/creatine benchmarks → `pubmed_yearly.csv`.
- **Wikimedia REST pageviews API**, per-article monthly, en.wikipedia, Jan 2019–Oct 2026: Ozempic, Wegovy, Mounjaro, Zepbound, Semaglutide, Tirzepatide, Rybelsus, Trulicity → `pageviews_monthly.csv`.
- **OpenFDA drug/event (FAERS)**, `patient.drug.medicinalproduct:"BRAND"` totals + top reaction counts for OZEMPIC, WEGOVY, MOUNJARO, ZEPBOUND, RYBELSUS, TRULICITY, VICTOZA, SAXENDA → `openfda.json`. Spontaneous reports: not incidence, duplicates possible.
