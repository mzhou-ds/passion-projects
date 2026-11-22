# Provenance

## Source
NHL public API (`api-web.nhle.com`), no key required:
`GET https://api-web.nhle.com/v1/gamecenter/{season}02{game:04d}/play-by-play`

Every regular-season game from 2015-16 through 2026-27 (2026-27 in progress as
of 2026-11-22). Fetched 2026-11-22 by `src/01_fetch.py` with 6 concurrent
workers, up to 4 retries per game. No games were sampled: this is the full
census of regular-season play-by-play for those seasons.

## What was extracted per game
From each game's play list (`plays`), in chronological order:

- **Goals** by period type (REG / OT / SO). Official final score counts at
  most one shootout goal, while play-by-play lists every shootout attempt, so
  `goals_total = goals_reg + goals_ot + (1 if any SO goal else 0)`. Validated:
  `goals_total` equals the official home + away score in every game fetched.
- **Empty-net goal (ENG)**: a goal whose details carry no `goalieInNetId`
  (the goalie was not in net). Counted for regulation only, plus a separate
  `eng_ot` column for the rare OT case. Cross-check: every ENG sits inside a
  goalie-out interval derived from `situationCode` (see below).
- **Situation code**: 4 characters, `[awayGoalie 1/0][awaySkaters][homeSkaters]
  [homeGoalie 1/0]`. `'1551'` is 5v5 with both goalies in; `'1560'` is home
  goalie pulled, 6 skaters vs 5. The API emits no explicit `goalie-pulled`
  event, so pull intervals are derived from situation-code transitions in
  period 3. Interval start = time of the first play with a goalie out;
  interval end = time of the first later play with the goalie back in, or
  20:00.
- **Endgame pull**: a goalie-out interval in period 3 where the pulling team
  is trailing and at most 6:00 remains. Goalie-out intervals outside that
  definition are almost entirely delayed-penalty pulls (a team pulls its
  goalie for an extra attacker while the opponent is about to be penalised):
  they last seconds, happen at any score and any time, and are stored
  separately (`dp_pull_time_sec`) and excluded from the 6v5 rates.
- **Power play**: both goalies in, 5 skaters vs 3 or 4, regulation only.
  Time integrated the same way (interval start/end from situation-code
  transitions). The advantaged team is the one with 5 skaters; the goal
  credited is scored by that team.
- **Pull outcome**: the fetch records first-interval outcomes, but the
  analysis scores the whole game: GF/GA summed over ALL endgame intervals,
  tie = the pulling team's net goals cover the first deficit. (A coach often
  pulls, resets, and pulls again, so first-interval outcomes understate
  success.)
- **External validation**: the 2023-24 team ENG totals reproduce StatMuse /
  Daily Faceoff exactly (WPG 24, TBL 23, FLA 21, SJS 4, EDM 12; league
  average 13.8 per team), and `goals_total` equals the official final score
  in every game fetched.
- **Players**: goals and ENGs per player-season, with names from the game's
  `rosterSpots` (locale dicts, `default` form taken). Shootout-deciding
  goals are type `goal` with periodType `SO` but are not real goals, so they
  are excluded from player totals (they still count once toward the official
  final score). Career totals sum the fetched seasons (2015-16 onward only;
  they are not lifetime totals for veterans).

## Known limitations
- 2019-20 (1,082 games) and 2020-21 (868) are COVID-shortened seasons;
  season aggregates for those years are per-game rates, so they still compare.
- 2026-27 is partial (games played through 2026-11-21).
- The break-even pull-time model (section 5 of the analysis) is a Poisson
  first-goal model using pooled empirical rates; it assumes goal arrivals are
  memoryless and ignores that a team that ties puts its goalie back in, and
  that a team down 2 that concedes an ENG is finished. It is a back-of-the
  envelope bound, not a win-probability model.
- The XGBoost ENG-prediction model uses season-end points % as the team
  quality proxy (a mild look-ahead: the full season's record is used for a
  game played mid-season). It is used for feature ranking, not for betting.
- 5v5 time in the break-even model subtracts a flat 4 minutes per game for
  4v4/3v3 time, which is an approximation.
