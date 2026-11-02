# Provenance

- Source: U.S. Bureau of Labor Statistics, American Time Use Survey (ATUS)
  multi-year microdata 2003-2025: Activity, Who, Respondent, and Roster files.
- Files were downloaded for the 2026-10-27 build from BLS
  (https://www.bls.gov/tus/datafiles-2023.htm and the multi-year files page)
  and are cached at `../2026-10-27/the-friend-workout-died/data/raw/` in this
  repo's working copy; the raw .dat files (about 1 GB) are not committed here.
- Committed extract: `data/respondent_day.csv` (250,165 diary days, one row
  per respondent) plus `data/results.json`, `data/model.json`, and
  `data/friend_minutes_by_hour.csv` reproduce every number in the README.
- BLS TRT cross-check values quoted in the README were computed from the
  respondent file's TRTFRIEND variable in the same working copy.
