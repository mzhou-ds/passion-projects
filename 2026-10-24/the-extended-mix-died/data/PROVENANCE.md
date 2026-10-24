# Provenance

All data comes from the public iTunes Search API (`https://itunes.apple.com/search`,
no key, US storefront), queried 2026-10-24 by `src/01_fetch.py`:

- Panels are curated artist lists (36 dance, 12 pop, 10 hip-hop, 12 rock artists),
  chosen to span each genre's commercial history from the 1990s to the 2020s.
  For each artist, up to 200 song results (`entity=song`, `attribute=artistTerm`),
  covering studio albums, singles, EPs and remix packages as a normal listener
  encounters them in the mainstream storefront. 13,835 raw rows; 13,471 after
  de-duplication by trackId and basic sanity filters (year 1985–2026, ≥30s).
- Fields used: trackId, trackName, collectionName, artistName, releaseDate,
  trackTimeMillis, primaryGenreName, previewUrl.
- Raw JSON is cached per artist under `data/raw/` (gitignored for size, ~22 MB);
  `data/fetch_manifest.json` records the query list and row counts, and
  `src/01_fetch.py` re-creates the raw pull exactly.
- Preview audio features (`src/03_audio.py`) are computed from the 30-second
  preview URLs the API returns, decoded with ffmpeg to 22050 Hz mono PCM.
  Previews are the first 30 seconds of each track (verified against tracks
  with known openings, e.g. deadmau5 "Strobe"). Only the derived features are
  kept (`data/preview_features.csv`); no audio is stored or redistributed.

Known limitations are listed in the README's Caveats section: storefront
survivorship (the catalog is what is still for sale in 2026), the 200-track
per-artist cap (binds hardest on prolific remix-era artists), release dates
that follow the collection rather than the original single for some reissues,
and title-parsing for version tags/stems (rules in `src/02_catalog.py`).
