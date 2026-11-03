# The New Wave Never Crossed Over

**EDM's pop era is over, but pop never left dance. The new headliners just never joined it.**

*Musing with Mike · 2026-11-03 · Topic: edm · Build #57*

Everyone tells the same story about dance music: it went pop in the 2010s,
and the headliners of today are pop stars who happen to DJ. I measured
whether that is true, generation by generation, using the complete
singles and EPs of 31 electronic artists on Deezer, from Tiesto and
Guetta to John Summit and Sara Landry. The pop crossover turns out to be
a generation, not a genre. The artists breaking through now release music
that is almost never tagged Pop, carries fewer featured artists, and runs
longer than the pop generation's radio-length singles. The Pop tags still
sitting on today's dance releases come from the veterans, not the new
wave. If you are booking or signing the new wave on pop-crossover
assumptions, you are pricing the wrong asset.

## Why this would surprise someone who knows the field

People inside dance music know the tech-house boom is real, and they know
songs got shorter. What nobody had measured is the generational break in
how releases are positioned. The familiar stat is the sound of the
chart, which mixes every generation together and hides who is doing
what. Split the same releases by the generation that made them, and the
break is stark: 1.1% of the new wave's 2019-25 singles and EPs are tagged
Pop, against 23.4% for the peak-EDM generation and 15.3% for the
pioneers, and the era-wide Pop share stayed flat only because veterans
kept releasing pop-tagged singles. The mechanism hiding under the
familiar stat is the crossover toolkit itself: a featured pop vocalist,
a radio-length edit, and pop positioning. The new wave dropped all three
at once, which is why its singles are longer, more solo, and tagged
Dance, Electro, House, or Techno instead. That points at a different
business read: the new headliners monetize club utility and scene
credibility, not radio reach, and the pop lane is now defended by
veterans rather than open to newcomers.

## What I built

| # | Question | Data | Script |
|---|----------|------|--------|
| 1 | Did the new wave cross over to pop, or stay genre-pure? | Deezer genre tags on 2019-25 singles+EPs, by cohort | `src/03_analysis.py` |
| 2 | Who actually releases the most new music now, veterans or newcomers? | Singles+EPs per artist per year, 2023-25, with a revisit check | `src/03_analysis.py` |
| 3 | Did the dance single really shrink, and did anyone refuse? | Track durations on singles, by era and cohort | `src/03_analysis.py` |
| 4 | Is every new dance single a collaboration now? | Contributor counts on singles+EPs, by era and cohort | `src/03_analysis.py` |
| 5 | What release strategies exist, and what predicts who still releases? | KMeans clusters + XGBoost with SHAP (n=31 artists) | `src/04_model.py` |

Reproduce: `python3 src/01_resolve_deezer.py` (review
`data/deezer_matches.csv`, fix any bad pin) then
`python3 src/02_fetch_deezer.py && python3 src/03_analysis.py &&
python3 src/04_model.py && python3 src/05_charts.py`.
The committed `data/releases_clean.csv` reproduces every headline
number without re-hitting the API.

## Findings

**1. The new wave never crossed over, and the numbers are not close.**
Of singles and EPs released in 2019-25, 1.1% of the new wave's (3 of 275)
are tagged Pop on Deezer, against 23.4% for the peak-EDM generation and
15.3% for the pioneers. Per artist, the gap is just as wide: the new
wave averages 0.8% Pop-tagged across a career, the peak generation
20.8% (Mann-Whitney p=0.002). The era-wide Pop share looks flat
(14.7% in 2005-12, 11.0% in 2013-18, 16.0% in 2019-25) only because
veterans kept releasing pop-tagged singles while the new generation
arrived and never joined them. Kygo (53% Pop-tagged lifetime), the
Chainsmokers (50%), and Alan Walker (41%) are the crossover generation.
John Summit, Fred again.., Dom Dolla, Mau P, and Sara Landry sit at 0
to 4%. Pop did not leave dance. It stayed with the people who crossed
over the first time.

**2. The new wave is also less collaborative and longer form.**
In 2019-25, 58.9% of the new wave's singles and EPs carry two or more
credited artists, against 85.4% for pioneers and 84.1% for the peak
generation. And the new wave's singles run longer: 234.6 seconds on
average in 2019-25, against 192.2 for the peak generation and 214.0 for
the pioneers. The crossover toolkit was a bundle, a featured vocalist
plus a radio-length edit plus pop positioning, and the new wave dropped
the whole bundle. A promoter buying John Summit expecting a Kygo-style
radio asset is buying the wrong thing. The asset is a club record.

**3. The veterans out-release the newcomers, but the gap is top-heavy
and mostly not significant.**
Pioneers averaged 11.6 singles and EPs per year in 2023-25, the peak
generation 9.7, the new wave 5.75 (medians 9.3, 9.3, 5.7). The pioneer
gap is not statistically significant (Mann-Whitney p=0.13, n=11 vs 8),
while the peak-generation gap is (p=0.037). Four hyper-releasers drive
the pioneer mean: Guetta (25.7 per year), Tiesto (19.7), Calvin Harris
(19.0), and Steve Aoki (18.3). I checked the obvious artifact, that
veterans pad their counts by re-releasing old songs: only 13.3% of
pioneers' recent output revisits an earlier title, against 6.2% for the
new wave, so new-title rates are barely changed (10.2 vs 5.4). The
treadmill also sped up for everyone: per-artist output in 2025 hit 12.0
for pioneers, 8.8 for the peak generation, and 6.6 for the new wave.

**4. The dance single lost 44% of its length, but the holdouts never
shrunk.**
Mean single length fell from 371 seconds in 2005-12 to 245 in 2013-18
to 208 in 2019-25. The peak generation shrank the most (193 seconds in
2019-25, radio length). The holdouts are the genres that never played
the radio game: Above & Beyond averages 326 seconds a single across a
career, deadmau5 355, and new-wave hard techno artist Sara Landry 295.
Length is a genre strategy, not a universal trend.

**5. Collaboration is the default now, except where the new wave bends
it back.**
Across eras, the share of singles and EPs with two or more credited
artists rose from 45.2% (2005-12) to 71.8% (2013-18) to 81.2% (2019-25).
But the new wave bends the curve back to 58.9% in 2019-25. The feature
era belongs to the old guard. The model agrees that the past predicts
the present: an XGBoost model of recent release rate (5-fold CV R2
0.57) leans hardest on lifetime output and peak-year output, while
career age is the weakest predictor. Momentum, not age, decides who
still releases. Clustering finds four strategies: pop crossovers (7
artists, 41% Pop-tagged), catalog engines (5: Guetta, Aoki, Tiesto,
Hardwell, Above & Beyond; 207 lifetime singles+EPs, 16.4 per year
recently), single machines (13, including Summit, Fred again.., and
Garrix), and quiet craftsmen (6 small-catalog, solo-leaning artists
including Mau P, Peggy Gou, and Skrillex).

## Methods and limits

- Source: Deezer public API, fetched 2026-11-03. Panel: 32 artists in
  three editorial cohorts by breakout era (pioneer pre-2013, peak-EDM
  2013-2018, new wave 2019+), documented in `data/artists.csv`. 31 are
  analyzed; see below for the exclusion.
- Two sources were tried and rejected, and the rejections are part of
  the result. MusicBrainz was dropped after an iTunes cross-check
  (`data/mb_crosscheck.csv`) showed it captures roughly half the new
  wave's catalog (Dom Dolla 33 of 70, Sara Landry 42 of 82, Cloonee 47
  of 86) while exhaustively cataloging veterans, which would have
  manufactured exactly the output gap this build tests. iTunes was
  dropped because its artist lookup caps at 200 collections and
  truncates prolific headliners. Deezer is a commercial catalog with no
  such cap and no such cohort skew.
- Cleaning: 4,979 album listings, 4,888 full details fetched. Deezer's
  artist-albums endpoint also returns albums the artist merely
  contributed to (remixes and features under another artist's name), so
  15.2% of details were dropped for having a different main artist.
  Same title, same record type, same year was deduplicated once
  (4,140 to 4,036). Headline output is singles+EPs only (3,195); albums
  mix studio albums with DJ-mix compilations on Deezer and are not a
  clean new-music series.
- Exclusion: Armin van Buuren is absent because Deezer's endpoint
  returns only album-type items for him (424, mostly radio episodes and
  compilations) even though his singles exist on Deezer. Excluding a
  high-output pioneer lowers the pioneer mean, so the output gap in
  finding 3 is, if anything, understated.
- Genre tags are Deezer's positioning tags, not audio analysis. A Pop
  tag means the release is positioned for pop, which is the business
  question here, not a claim about how it sounds. Contributor counts
  include featured vocalists and credited co-producers.
- Career-age curves are confounded with calendar era (every pioneer's
  late career coincides with the streaming era), so they are in
  `data/career_curve.csv` for reference but are not charted or
  headlined. Small-n statistics throughout: cohort means come with
  Mann-Whitney tests and n=31 artists, not just averages.

## Charts

- `charts/cohort_output_trend.png`: singles+EPs per active artist, by
  cohort and year.
- `charts/cohort_now_vs_catalog.png`: recent release rate and median
  catalog year, by cohort.
- `charts/format_mix.png`: single share of singles+EPs, by cohort.
- `charts/pop_generation.png`: Pop-tag share and mean single length in
  2019-25, by cohort.
- `charts/era_collab_pop.png`: collaboration share and Pop-tag share,
  by era.
- `charts/clusters.png`: four release strategies.
- `charts/shap_importance.png`: what predicts who still releases.
