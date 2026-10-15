# Provenance

- **Snapshot date:** 2026-10-15 (America/Los_Angeles), captured by `src/01_fetch.py`.
- **Source:** Beatport chart pages. Each page embeds its Top 100 in the
  `__NEXT_DATA__` dehydrated react-query payload; no API key, no login.
  Charts fetched: the overall Top 100 (`/top-100`) and the 17 genre Top 100s
  linked from Beatport's homepage navigation. Every genre slug/id pair was
  verified against the genre metadata object embedded in its own page
  payload (id, name, slug, sub-genres all match the chart fetched).
- **Raw capture:** `data/raw/charts_raw.json.gz` is the unmodified payload set
  (18 charts x 100 tracks) that all analysis in this project reads.
- **Fields used per track:** id, name, mix name, artists, remixers, genre,
  sub-genre, BPM, key (name + chord type), length, label, release date
  (new_release_date, falling back to publish_date), price (USD), explicit and
  exclusive flags.
- **Known data quirks:** release dates on catalog/reissue entries are the
  original release dates; many drum & bass tracks are listed at half-tempo
  BPM; artist identity is the credited name string exactly as Beatport
  stores it.
- **Fetch etiquette:** one fresh request per chart, 2 seconds apart, 18
  requests total for a full refresh.
- **Why not the Spotify dataset used on 2026-10-06:** the Hugging Face
  parquet endpoint was unreachable through this machine's proxy on
  2026-10-15 (repeated proxy disconnects), so this build uses the live
  Beatport census instead. The pivot is documented here rather than hidden.
