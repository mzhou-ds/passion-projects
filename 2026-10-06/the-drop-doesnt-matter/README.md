# The Drop Doesn't Matter

**EDM producers obsess over energy, danceability, and the perfect 128 BPM drop. On 19,000 EDM tracks, those are close to the least useful popularity signals in the data. What actually moves the score is how long the track is, how loud it is, and how dark it sounds — and even all of that together explains only about a third of popularity. The rest is fame, catalog, and playlists.**

*Musing with Mike · 2026-10-06 · Topic: EDM*

Every electronic producer I know has the same folk theory: nail the drop — max energy, max danceability, tempo locked to the grid — and the track travels. I believed it too, standing in enough 2 a.m. rooms where the drop is the entire religion. So I tested it the way I'd test any marketplace claim: take the sound apart, train a model on sound alone, and see what survives.

It mostly doesn't. The model that knows everything about how an EDM track *sounds* and nothing about who made it can explain roughly one-third of why one track scores 70 and another scores 10. And inside that third, the drop features are the supporting cast, not the leads. Duration — the least sexy variable in music — is the star. That's not a production insight. That's a distribution insight wearing a production costume, and it's exactly the kind of mispricing an operator should care about: the industry optimizes the part of the product that matters least to the outcome it reports.

## Key findings

**1. EDM is engineered differently and paid worse for it.** Across 18,975 EDM-family tracks (19 genres) vs 1,000 each of pop, hip-hop, and rock: EDM's median energy is 0.79 vs pop's 0.62, median tempo 125.0 BPM vs pop's 118.7, median valence 0.38 vs pop's 0.50 (EDM is measurably darker), and median duration 220 seconds. Yet EDM's median Spotify popularity is 31 vs pop's 66 and hip-hop's 58. The most deliberately engineered sound in the dataset earns half of pop's median score. Structure is not the bottleneck — distribution is. (Rock's median of 0 in this snapshot is a catalog artifact worth noting: a legacy-heavy sample where over half the rock tracks sit at popularity 0; it flatters no one and I don't lean on it beyond structure.)

**2. Sound predicts about a third of popularity — honestly reported.** An XGBoost regressor trained on 13 audio-only features (no artist, no genre label, no leakage) within the EDM family: test R² = 0.365, MAE = 14.8 points on a 0–100 scale, vs a median-guess baseline MAE of 20.4 (train R² = 0.599, so it does overfit somewhat — the test number is the honest one). Read plainly: knowing the waveform gets you roughly a third of the way to knowing the score. The other two-thirds is who made it, when, and which playlists touched it. Anyone selling "hit-predicting AI" on audio features alone is selling you that third and hoping you don't ask about the rest.

**3. The drop features rank near the bottom; duration, loudness, and mood run the model.** SHAP mean |impact| ranking: duration 4.09, energy 2.69, loudness 2.66, valence 2.66, tempo 1.85 — and danceability *ninth* at 1.49, behind acousticness and speechiness. The raw correlations agree: duration r = −0.17, instrumentalness r = −0.15, loudness r = +0.13, while energy r = −0.03 and tempo r = −0.04 are noise-level. Worse for the folk theory, the canonical settings *underperform*: tracks at 120–128 BPM average 29.7 popularity vs 34.7 below 110 BPM; danceability above 0.80 averages 26.7 vs 33.6 in the 0.50–0.65 band; energy above 0.85 averages 30.2 vs 34.2 at 0.50–0.70. And duration has a cliff: 210–240-second tracks average 38.1, tracks over 300 seconds average 23.8. The SHAP dependence plot shows the model literally falling off a ledge around 240 seconds. The perfect festival weapon — long, maximal, locked at 128 — is, on average, the *least* popular shape in the family.

**4. The archetype that loses is the warehouse; the ones that win are short and human.** KMeans (k = 5, silhouette 0.183; all k in 3–7 score 0.15–0.19, so treat clusters as lenses, not species) finds five sound archetypes. The loser is unambiguous: C2 "instrumental, groove-led, long-form" — minimal-techno, Detroit techno, Chicago house, techno; mean duration 370 seconds, instrumentalness 0.76, n = 4,571 — at mean popularity 25.9, median 20. The winners: C3 "groove-led, slow, short-form, euphoric" (house, dance, edm, deep-house; 202 seconds, valence 0.54, n = 6,948) at mean 34.1, median 38, and C4 "high-energy, fast, dark" (drum-and-bass, hardstyle, dubstep, trance; 148 BPM, n = 4,879) at mean 34.2, median 35. That's an 8-point mean gap between the warehouse and the winners — real money at catalog scale. Subgenre means tell the same story from the other end: Detroit techno 11.2 and Chicago house 12.3 at the bottom; progressive-house 46.6 and deep-house 44.8 at the top. The originators are the worst-compensated sounds in their own family.

## What I built

| # | Question | Method | Output |
|---|----------|--------|--------|
| 1 | Is EDM actually built differently? | Median + distribution comparison, EDM family (19 genres) vs pop / hip-hop / rock on duration, tempo, energy, instrumentalness, danceability, loudness, valence | `figures/fig1*` |
| 2 | Does the sound predict the score? | XGBoost regressor on 13 audio features only, 80/20 split (15,180 train / 3,795 test), SHAP TreeExplainer summary + dependence | `figures/fig2*`, `fig3*` |
| 3 | What are EDM's archetypes and which get paid? | KMeans on 10 standardized audio features, k selected by silhouette over 3–7 (best in 4–6: k = 5), PCA check | `figures/fig4*` |
| 4 | Where does sound and score disagree most? | Test-set predicted-minus-actual gap; top 15 each direction | `figures/fig5*`, tables below |

Reproduce: `python3 analysis.py` — downloads the 13.6 MB parquet once (single file, no API polling), runs all four analyses, writes `figures/*.png`, `results.json`, and `findings.txt`. Every number in this README traces to `results.json` / `findings.txt` from that run. Requires: pandas, numpy, scikit-learn, xgboost, shap, matplotlib, pyarrow.

## The model, honestly

Test R² = 0.365 is the number to quote and it deserves suspicion in both directions. It's *higher* than a pure "sound is nothing" story — duration, loudness, and valence carry real signal, and the duration cliff at ~240 seconds is sharp enough to act on. It's also nowhere near "we can predict hits": MAE 14.8 means the typical track's score is off by ±15 points, and the predicted-vs-actual scatter (`fig3b`) is a cloud with a diagonal rumor running through it. The train/test gap (0.599 vs 0.365) says the model memorizes artist-like sound fingerprints in training that don't generalize — which is itself evidence that "sound" in this dataset partially *is* artist identity in disguise. Genres are sampled at exactly 1,000 tracks per genre in the source (114,000 rows), so the EDM family here is a balanced laboratory sample, not the streaming market — deep-house does not release as many tracks as techno in the wild. All conclusions are within-sample.

The SHAP dependence panels (`fig3`) are the most actionable artifact in the piece: duration positive below ~230s and sharply negative above ~250s (a ~10-point SHAP swing across the cliff); energy flat then *negative* past ~0.7; loudness close to monotonic — louder (less negative dB) predicts higher popularity across almost the whole range. If a label A&R person asked me for three levers from sound alone, they'd be: cut it to 3.5 minutes, master it loud, don't chase max energy. None of them is "make the drop bigger."

## Clustering notes

Silhouette scores are low across the board (k = 3: 0.188, k = 4: 0.181, k = 5: 0.183, k = 6: 0.182, k = 7: 0.145) — EDM sound is a continuum with soft neighborhoods, not five natural kinds. PCA confirms it: PC1 + PC2 explain only 24.5% + 16.6% of variance, and in `fig4b` popularity is smeared across the entire sound map rather than pooled in any region. That's the visual version of the R²: there is no neighborhood of sound where popularity lives. The clusters earn their keep as *portfolio* labels — C2's long-form instrumental profile (370s, 0.76 instrumentalness) underperforming by ~8 points is a catalog-strategy fact even if the boundary around it is fuzzy.

## The arbitrage table

Gap = audio-only predicted popularity − actual popularity, computed out-of-sample on the 3,795-track test set. Positive gap: the sound predicts a bigger track than the score shows ("underexposed by sound"). Negative gap: the score far exceeds anything the sound justifies — fame, catalog age, and playlist gravity doing the lifting. Framing caveat, stated once and meant: popularity is partly artist-fame-driven, so read these as "sound predicts more/less than the score shows," never as "this track deserves X."

**Underexposed — predicted ≫ actual (top 15):**

| # | Track | Genre tag | Actual | Predicted | Gap |
|---|-------|-----------|--------|-----------|-----|
| 1 | Julia Michaels;Niall Horan — What A Time | electro | 0 | 63.6 | +63.6 |
| 2 | Sam Smith;Normani — Dancing with a Stranger (JP title in source) | dance | 0 | 59.5 | +59.5 |
| 3 | Julia Michaels — Issues | electro | 0 | 58.0 | +58.0 |
| 4 | The Prophet — Mayhem MF - Original Mix | hardstyle | 0 | 55.7 | +55.7 |
| 5 | James Hype — Crank | house | 0 | 52.5 | +52.5 |
| 6 | James Hype — Crank | deep-house | 0 | 52.5 | +52.5 |
| 7 | Praveen et al. — Endrendrum Punnagai LoFi Mix | idm | 2 | 53.6 | +51.6 |
| 8 | Katy Perry;Juicy J — Dark Horse | dance | 0 | 51.1 | +51.1 |
| 9 | Lady Gaga — Million Reasons | dance | 0 | 50.1 | +50.1 |
| 10 | Gryffin;OneRepublic — You Were Loved | edm | 0 | 49.5 | +49.5 |
| 11 | Avicii;Aloe Blacc — SOS | edm | 0 | 49.2 | +49.2 |
| 12 | Avicii;Aloe Blacc — SOS | dance | 0 | 49.2 | +49.2 |
| 13 | Alex Schulz — We Could Be Anything | deep-house | 0 | 48.5 | +48.5 |
| 14 | Armin van Buuren;R3HAB;Simon Ward — Love We Lost | progressive-house | 0 | 47.8 | +47.8 |
| 15 | Burna Boy — On the Low | dance | 2 | 49.7 | +47.7 |

**Overexposed — actual ≫ predicted (top 15):**

| # | Track | Genre tag | Actual | Predicted | Gap |
|---|-------|-----------|--------|-----------|-----|
| 1 | David Guetta;Bebe Rexha — I'm Good (Blue) | edm | 98 | 14.6 | −83.4 |
| 2 | Shawn Mendes — There's Nothing Holdin' Me Back | dance | 86 | 12.6 | −73.4 |
| 3 | Tiësto;Ava Max — The Motto | edm | 86 | 14.9 | −71.1 |
| 4 | Joel Corry;MNEK — Head & Heart | house | 80 | 10.9 | −69.1 |
| 5 | Mark Ronson;Bruno Mars — Uptown Funk | dance | 83 | 14.3 | −68.7 |
| 6 | MEDUZA et al. — Bad Memories | house | 85 | 21.8 | −63.2 |
| 7 | Doja Cat — Boss Bitch | dance | 79 | 16.8 | −62.2 |
| 8 | Shawn Mendes — Treat You Better | dance | 84 | 23.1 | −60.9 |
| 9 | Avicii — The Nights | dance | 86 | 27.0 | −59.0 |
| 10 | Modjo — Lady - Hear Me Tonight | house | 78 | 20.0 | −58.0 |
| 11 | Felix Jaehn;Ray Dalton — Call It Love | house | 77 | 20.6 | −56.4 |
| 12 | Chris Brown — Under The Influence | dance | 96 | 41.3 | −54.7 |
| 13 | Topic;Bebe Rexha — Chain My Heart | edm | 70 | 15.3 | −54.7 |
| 14 | Topic;Bebe Rexha — Chain My Heart | house | 70 | 15.3 | −54.7 |
| 15 | Master KG;Nomcebo Zikode — Jerusalema | house | 74 | 20.2 | −53.8 |

Now the honest read of my own table, because it indicts itself in an instructive way. The underexposed list is dominated by tracks scored **0** that any human knows are enormous — Dark Horse at 0, SOS at 0, a Julia Michaels record at 0. Those zeros are not "nobody listens"; they're how this dataset's popularity snapshot represents tracks whose specific version/ID carries no current score (re-releases, regional versions, duplicate IDs across genre tags — note Crank and SOS each appear twice under different genre labels). So the top of the underexposed table is substantially a *data artifact list*: it proves the model's sound template matches the pop-crossover shape, and it proves the score column can't be trusted at zero. The overexposed side has no such excuse and is the cleaner signal: I'm Good (Blue) at 98 predicted 14.6, Uptown Funk tagged "dance" at 83 predicted 14.3. The biggest tracks in the family are, sonically, unremarkable to the model — short-ish, vocal, mid-energy pop shapes carried by artist gravity. If you A&R by soundalike, you will systematically underrate exactly the records that print money, because what printed was never in the waveform.

## The operator takeaway

EDM's popularity market misprices duration and distribution, and prices the drop at a premium it hasn't earned. Three actionable reads:

- **For producers/labels:** the sub-4-minute cut is not a TikTok compromise, it's the popularity-maximizing shape in the full catalog data too — the model's value falls off a cliff past ~250 seconds and long-form instrumental is the single worst-compensated archetype (−8 points vs the winning clusters). Release the radio edit *as* the record, not as the afterthought.
- **For playlist/catalog buyers:** Detroit techno (mean 11.2) and Chicago house (12.3) catalog is the cheapest attention in the family *relative to cultural equity* — the originator genres with the deepest sync/heritage value and the lowest streaming scores. If scores ever mean-revert toward influence, that's the long position. (Within-sample caveat applies: these are snapshot scores, not royalty statements.)
- **For anyone building "hit prediction":** cap your claims at the R². A third is real — loudness and length are levers — but the arbitrage table shows the tails are fame and data artifacts, not sound. Sell the third as mix/master QA, not as prophecy.

What I did *not* find: any evidence that maximizing energy, danceability, or parking on 128 BPM helps. The genre's central production religion optimizes variables ranked 2nd, 9th, and 5th — and at their extremes, all three point the wrong way.

## Limitations

- **Snapshot data.** Popularity is Spotify's 0–100 index as captured when the dataset was collected (Maharshi Pandya, ~2022 vintage); it decays, resets across versions, and is not streams, revenue, or ticket sales. The abundance of exact zeros (including famous tracks) is a known artifact of that snapshot — means/medians are robust to it in aggregate; individual-track reads are not.
- **Balanced-sample distortion.** 1,000 tracks per genre across 114 genres is a designed sample, not the market. Cross-genre medians compare *samples*, and EDM-family aggregates weight minimal-techno equally with house.
- **Duplicate tracks across genre tags.** The same recording appears under multiple `track_genre` labels (e.g., SOS as both edm and dance); the model trains/tests on rows, so near-duplicates can straddle the split and mildly flatter test R².
- **Audio features are Spotify's black box.** Energy, valence, danceability etc. are Spotify's proprietary estimates, taken as given; "valence" finding is a finding about Spotify's valence meter, not about human emotion.
- **Duration filter.** Tracks outside 20–900 seconds (160 rows, mostly data errors/outliers) were excluded from all analyses; EDM n falls from 19,000 to 18,975.
- **Correlation, not causation.** SHAP describes this model's splits, not what *causes* popularity; loudness may proxy for commercial mastering budgets, short duration for pop-crossover intent. No artist, label, release-date, or playlist features were used — by design (that's the question), which also caps accuracy by design.

## Sources

- Maharshi Pandya, *Spotify Tracks Dataset* (Hugging Face: `maharshipandya/spotify-tracks-dataset`), parquet snapshot downloaded directly from `https://huggingface.co/api/datasets/maharshipandya/spotify-tracks-dataset/parquet/default/train/0.parquet` (114,000 tracks). Spotify audio features and popularity index originate from the Spotify Web API as collected by the dataset author.
- Methods: XGBoost (Chen & Guestrin 2016) with SHAP TreeExplainer (Lundberg et al. 2017/2020); KMeans (scikit-learn) with silhouette-based k selection over k = 3–7, reported for 4–6 per design and chosen at k = 5.

## Layout

```
the-drop-doesnt-matter/
├── analysis.py          # download data, all 4 analyses, figures, results.json, findings.txt
├── README.md            # this file
├── results.json         # every headline number, machine-readable
├── findings.txt         # plain-text trace of the run
└── figures/
    ├── fig1_structure_distributions.png
    ├── fig1b_median_bars.png
    ├── fig2_shap_summary.png
    ├── fig3_shap_dependence.png
    ├── fig3b_pred_vs_actual.png
    ├── fig4_cluster_profiles.png
    ├── fig4b_pca_clusters.png
    └── fig5_arbitrage_scatter.png
```

*The parquet cache (`spotify_tracks.parquet`) is downloaded by the script on first run and is not part of the write-up — delete it freely; the script re-fetches it.*
