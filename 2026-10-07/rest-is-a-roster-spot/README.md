# Rest Is a Roster Spot

**The NHL schedule hands out roughly four standings points a year between its luckiest and unluckiest teams — more than most trade-deadline deals are worth — and nobody's roster accounts for it. Edmonton, meanwhile, flies more miles than any team in hockey and still somehow catches the breaks.**

*Musing with Mike · 2026-10-07 · Topic: sports analytics (hockey)*

Every front office I've ever watched — and I spent years around marketplace teams at Lyft, DoorDash, and Patreon before Meta, where the same logic runs the building — prices what it can put in a spreadsheet. Goals, assists, cap hit, term. The schedule goes in a different bucket. It's weather. It's the league's problem. Nobody puts a number on it, so nobody manages it, and anything nobody manages is exactly where the mispricing hides.

So I priced it. All 6,560 regular-season games across the last five NHL seasons, pulled from the league's own API, with pre-game Elo ratings built game by game so no result ever leaks into its own prediction, and every game's rest, back-to-back, three-in-four, travel mileage, and timezone shift attached to both teams. Then I asked the only question that matters to an operator: take the talent out, and what's the schedule itself worth?

## Key findings

**1. Rest is worth about ten points of win probability, and it prices like a star.** Forget the model for a second and just count. When the home team is the tired one — two or more fewer rest days than the visitor — it wins 47.6% of the time, below a coin flip in its own building. At equal rest it's 53.0%. Give the home team one extra day and it jumps to 58.1%. That's a ten-and-a-half-point swing from the worst rest spot to a good one, in a league where the entire home-ice advantage is worth about four. A visiting team on the second night of a back-to-back loses 59.1% of the time; make the home team rested on top of it and it's 60.7%, against a 53.7% baseline. Connor McDavid is not walking through the door to fix your Tuesday in Columbus. The calendar already decided a chunk of that game before the anthem.

**2. Talent still runs the league — the schedule is the biggest thing that isn't talent.** I trained an XGBoost model on pre-game Elo plus the schedule features and tested it strictly out-of-time, training on 2021–24 and scoring 2024–26 so it never grades its own homework. It lands at AUC 0.577. SHAP puts Elo first by a mile (0.462 mean impact) — good teams win, breaking news — but the next tier is all schedule: recent travel load for both teams, the mileage gap, the visitor's back-to-back flag, timezone direction, rest differential. A logistic model with *only* schedule features, no idea who's playing, still beats a coin flip at AUC 0.536. Kill the rest features in the model and the average game moves 2.7 points of win probability, with the worst-scheduled games moving 17. The honest read: you cannot predict a hockey game, but you can predict which team the week has been beating up.

**3. The schedule is a standings transfer, and in 2025-26 it moved 4.4 points.** Zero out every team's rest advantage and disadvantage, re-score all five seasons, and convert the win-probability changes into standings points. In 2025-26 the Dallas Stars collected a league-best +2.2 points from their rest schedule and the San Jose Sharks and Chicago Blackhawks each gave back −2.2 — a 4.4-point spread between the luckiest and unluckiest schedules, dealt out before anyone laced a skate. Over five years the pattern hardens instead of washing out: Philadelphia bleeds −1.9 points a season, Chicago −1.9, San Jose −1.6. Wild-card races in this league are routinely decided by two points. The Flyers have been starting every season roughly a win in the hole, and it isn't their roster's fault, and it isn't fixable by their roster either. That is a structural tax, and structural taxes are the kind nobody negotiates because nobody sees the invoice.

**4. Edmonton flies the most — and catches the breaks anyway.** The Oilers average 49,580 air miles a season, the most in hockey, 46% more than the New York Islanders' league-low 34,001. San Jose, Anaheim, Dallas, and Seattle round out the mileage leaders; the bottom of the table is one tight northeastern neighborhood bus league. Geography is destiny for the travel tax, and Edmonton drew the longest straw in the league. Here's the part I didn't expect: despite all those miles, the Oilers own the *best* five-year rest luck in the model at +1.5 points a season, and +2.1 in 2025-26 alone. The miles are real and the rest breaks are real, and they don't cancel — they coexist, which means whatever Edmonton loses to geography it has quietly been recovering in rest spots. File that away next time the schedule drops and the annual outrage cycle starts: the invoice everyone reads (the miles) is not the invoice that decides games (the rest).

## What I built

| # | Question | Method | Output |
|---|----------|--------|--------|
| 1 | What is rest worth, raw? | Home win% by rest differential across 6,560 games, plus back-to-back splits | `fig1_rest_curve.png` |
| 2 | Does the schedule predict anything once talent is counted? | Chronological pre-game Elo; XGBoost + schedule-only logistic, trained 2021–24, tested 2024–26; SHAP ranking | `fig2_shap.png` |
| 3 | Who does the schedule pay? | Counterfactual: rest/B2B/3-in-4 features zeroed, expected standings points re-scored per team-season | `fig3_schedule_luck.png`, `data/schedule_luck.csv` |
| 4 | Who pays the travel tax? | Haversine mileage between consecutive game cities per team, 5-season averages; back-to-back counts | `fig4_travel_tax.png`, `data/travel_tax.csv` |
| 5 | Is home ice just rest in a costume? | Home win% raw vs equal-rest, by season | `fig5_home_edge.png` |

Reproduce: `python3 analysis.py` — downloads five seasons of schedules from the NHL's public API once (cached under `data/cache/`, gitignored), builds the Elo ladder and every feature, retrains the models, and writes `results.json`, `findings.txt`, all five figures, and `data/games.csv` with the full game-level dataset. Every number in this piece traces to that run.

## The honest limits

The model is a pricing tool, not a crystal ball, and AUC 0.577 is what hockey actually allows — this sport has a coin-flip core that no feature set has ever beaten for long, and I'd distrust anyone whose hockey model claims much more. The schedule-only AUC of 0.536 is small but it's the right kind of small: stable, directional, and still standing after talent is removed. The rest curve in Figure 1 needs no model at all, which is why I trust it most.

Two caveats deserve daylight. The travel-load features the model leans on (miles across each team's previous six games) are a road-wear proxy, not a priced-per-mile causal effect — SHAP says the model uses them, not that a specific connecting flight through Denver costs a specific goal. And the schedule-luck table neutralizes rest, back-to-backs, and three-in-fours, but leaves travel in both arms, so it prices the *rest* schedule specifically. Mileage luck would be a second, separate table, and Edmonton would not enjoy reading it.

The 2025-26 equal-rest number deserves its own raised eyebrow: control for rest last season and home teams won 49.9% — *less than half* — of their games. One season is not a eulogy for home ice, and the five-year picture still shows a real edge, but the direction rhymes with everything else here. Home ice used to be a fortress. More and more, it looks like it was two things all along: a rested team and a tired visitor, wearing a jersey.

## What it's worth

A win is two points, and four points is roughly the distance between picking 20th and golfing in April. If I ran a team, the schedule release would get the same treatment as free agency: model the rest map in July, count your net back-to-backs against rested opponents, and know — before a single signing — whether you're starting the season up two points or down two. Montreal, San Jose, the Islanders, and Pittsburgh each played 16 back-to-backs in 2025-26; Calgary and Winnipeg played 9. That's not a complaint, it's a line item, and line items can be managed: sports-science budgets, travel operations, goalie rotation planning, even which games you circle for your backup. The teams that treat rest as a roster spot will take points from the teams that treat it as weather. They already are.

---

**Sources:** NHL public API (`api-web.nhle.com`), club schedule endpoints for all 33 team-seasons × 5 seasons (2021-22–2025-26), retrieved 2026-10-07; arena coordinates and timezones coded as static reference data in `analysis.py`. Code and full game-level data: this directory.
