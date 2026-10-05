# Data provenance

- Dataset: How Couples Meet and Stay Together (HCMST) 2017-2022,
  public version 2.2 ("small public" file), Rosenfeld et al., Stanford.
- Landing page: https://data.stanford.edu/hcmst2017
- File downloaded: https://stacks.stanford.edu/file/druid:hg921sg6829/HCMST%202017%20to%202022%20small%20public%20version%202.2.dta
- Raw .dta md5 (this run): `fe0000cbf379bebcb86ba8d7b00cbd9a` — raw file is kept in `data/raw/`
  and git-ignored; re-download with `python3 src/fetch_hcmst.py`.
- Citation: Rosenfeld, Michael J., Reuben J. Thomas, Sonia Hausen,
  et al. 2019+. "How Couples Meet and Stay Together 2017-2022,"
  public version 2.2 [computer file]. Stanford, CA: Stanford
  University Libraries. https://data.stanford.edu/hcmst2017
- `couples.csv` here is a derived, de-identified analytic extract
  (one row per respondent's current or most recent partner) built by
  `src/fetch_hcmst.py`. No names or geography below national level.
