# Provenance

- Source: Deezer public API (api.deezer.com, no key), fetched 2026-11-03.
  Artist search (`/search/artist`) resolved each panel name to a Deezer
  artist ID (see `data/deezer_matches.csv`). Six top hits were wrong on
  first pass and were hand-corrected before fetching: Diplo, Hardwell,
  Zedd, Alan Walker, Anyma, and FISHER (the DJ, confirmed by matching
  "Losing It" to artist id 56125). The other 26 top hits were the
  intended artists.
- Discographies: `/artist/{id}/albums`, paged at 100 (4,979 listings),
  then `/album/{id}` for full details (4,888 saved;
  `data/deezer_albums_raw.jsonl`). Detail fetching used 4 workers with
  backoff on 403/429 and per-album appends, so it is resumable.
- Two sources were tried and rejected first. MusicBrainz WS/2 gave
  complete-looking discographies, but an iTunes cross-check
  (`data/mb_crosscheck.csv`) showed it captures roughly half the new
  wave's catalog (Dom Dolla 33 of 70 iTunes collections, Sara Landry
  42 of 82, Cloonee 47 of 86) while exhaustively cataloging veterans,
  which would have manufactured the output gap this build tests.
  iTunes was then rejected because its artist lookup caps at 200
  collections and truncates prolific headliners (Tiesto exceeds it).
  Deezer has neither skew.
- Cleaning (all in `src/03_analysis.py`): Deezer's artist-albums
  endpoint also returns albums the artist merely contributed to, so
  15.2% of details were dropped for having a different main artist.
  Same artist + normalized title + record type + year was deduplicated
  once (4,140 to 4,036). Headline output is singles+EPs (3,195, 100%
  dated); albums are excluded from headline counts because Deezer's
  album shelf mixes studio albums with DJ-mix compilations.
- Exclusion: Armin van Buuren has no singles+EPs in the analysis
  because Deezer's endpoint returns only album-type items for him
  (424, mostly radio episodes and compilations) even though his
  singles exist on Deezer. He is kept in `data/artists.csv` and the
  exclusion is recorded in `data/analysis_summary.json`.
- Panel cohorts (pioneer / peak-edm / new-wave) are editorial labels
  by breakout era, documented per artist in `data/artists.csv`.
- Reproduce: `python3 src/01_resolve_deezer.py` (review
  `data/deezer_matches.csv`, fix any bad pin) then
  `python3 src/02_fetch_deezer.py && python3 src/03_analysis.py &&
  python3 src/04_model.py && python3 src/05_charts.py`.
  The committed `data/releases_clean.csv` reproduces every headline
  number without re-hitting the API.
