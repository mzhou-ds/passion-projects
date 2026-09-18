# The Window Is a Contract

**What 18 seasons of Cup finalists say about McDavid's Oilers, 2026–2031.**

Every spring the same debate: is Edmonton's window closing? I built a model to price it instead of arguing about it. Four pieces:

1. **Cluster 501 forward lines** by 5v5 play style. Find where McDavid's line lives.
2. **Fit NHL aging curves** from 1,600+ skaters' real birthdates. Forwards peak at 25.
3. **Train a Cup-finalist classifier** (XGBoost, leave-one-season-out) on 18 seasons, 554 team-seasons. AUC 0.70; median finalist ranks #2 of ~32. It called the 2026 Final exactly (Carolina, Vegas).
4. **Project Edmonton's roster five years out** — age-adjusted, cap-constrained — under two scenarios for the summer of 2028.

## The findings

**1. The McDavid line is a different species.**
All six qualifying McDavid-line seasons land in the "freight trains" cluster — lines that generate 3.42 expected goals per 60, best in the league. The 2023-24 Hyman–Draisaitl–McDavid unit posted 4.47 xGF/60: the 2nd most dangerous 5v5 line of 501. McDavid's units sit in the top 2–10% of the league's most elite cluster. There is no replacing that with money.

**2. What actually predicts a Cup Final: goal differential, chance creation, and — the surprise — the penalty kill.**
SHAP values rank PK goals-against 4th among nine features, ahead of the power play. Champions kill penalties. The 2026 champion Hurricanes are the template: structured, deep, and elite shorthanded.

**3. The window doesn't close on age. It closes — or doesn't — on July 1, 2028.**
The youth wave (Savoie, Howard, Podkolzin entering their primes) offsets the veterans' decline almost exactly; the aging curve never produces a cliff. What produces a cliff is the contract decision. If McDavid re-signs (8 × $17M): P(Cup Final) holds at ~0.11–0.13 every year through 2030 — a perennial contender, roughly double the average team. If he walks — even with a generous $11M star-UFA replacement at 90% of his on-ice chance creation — the probability collapses to 0.05 in 2028-29 and 0.03 by 2031. The model also says the current roster is already past its peak: team 5v5 xGF/60 fell from 3.21 (2023-24) to 2.64 (2025-26).

**4. The rising cap is Edmonton's best player.**
$104M → $113.5M → ~$121.5M → $130M → $139M. At those ceilings, $17M for McDavid in 2028 is ~14% of the cap — roughly what Draisaitl's $14M costs today. The "can they afford him" framing is backwards. The discount contract ($12.5M) is what's funding the current roster; the only question is the signature.

## The numbers

| Scenario | 26-27 | 27-28 | 28-29 | 29-30 | 30-31 |
|---|---|---|---|---|---|
| A: McDavid re-signs — P(Final) | 0.11 | 0.13 | 0.13 | 0.10 | 0.07 |
| B: McDavid walks — P(Final) | 0.11 | 0.13 | 0.05 | 0.05 | 0.03 |
| A: cap space ($M) | 8.4 | 18.8 | 17.0 | 27.0 | 52.9 |

Average team: 0.0625. Model: XGBoost, leave-one-season-out AUC 0.702.

## How it was built

- `src/01_lines_cluster.py` — 501 forward lines (≥125 min 5v5, 2023–2026), 12 features, k=5 (silhouette 0.127). → `figures/01_line_clusters.png`
- `src/02_fetch_ages.py` — birthdates for 1,632 skaters via NHL API (polite 0.35s interval)
- `src/03_age_curves.py` — delta-method aging curves, xG/60 by position. → `figures/02_age_curves.png`
- `src/04_cup_model.py` — XGBoost on 554 team-seasons (2008–2025), 36 finalists, 9 features, LOSO validation. → `figures/03_shap.png`
- `src/05_window.py` — roster projection: on-ice xGF/60 baselines (shrinkage for small samples), TOI-weighted, age-adjusted; D-corps defensive effect; Jarry's actual GSAA/60; cap ledger. → `figures/04_window.png`

`src/05_window.py` prints the full forecast table and saves `data/processed/window_forecast.csv`.

## Data

- MoneyPuck (moneypuck.com): lines, skaters, teams, goalies CSVs, 2008–2026
- NHL API (api-web.nhle.com): player birthdates
- Spotrac: Oilers 2026-27 contract table (~June 2026)
- Cap ceilings: $104M (2026-27), $113.5M (2027-28) confirmed May 2026; 2028-31 assumed ~+7%/yr
- Season labels are start years: "2025" = 2025-26

## Caveats, stated plainly

- Aging curves are averages. McDavid is not average; generational players age slower. This likely *understates* scenario A.
- Special teams are held at 2025-26 levels. Coaching changes or a PP scheme shift would move the needle.
- The "star UFA" in scenario B is generous (90% of McDavid's on-ice chance creation for $11M). Reality would be worse.
- 2028-31 cap ceilings are assumptions, not announcements.
- One model, one dataset. The 2026 Final call was a hit; the model also whiffed 2025 (had EDM at 0.08 — they made the Final anyway).

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/01_lines_cluster.py
python src/02_fetch_ages.py        # ~10 min, polite NHL API crawl
python src/03_age_curves.py
python src/04_cup_model.py
python src/05_window.py
```
