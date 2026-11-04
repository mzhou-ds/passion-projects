# Home Ice Is a Body Clock

**The schedule explains only a quarter of home ice. What it does explain
is not the flight. It is the direction of the flight, and whether the
visitor played yesterday.**

*Musing with Mike · 2026-11-04 · Topic: sports-analytics · Build #58*

Every hockey fan knows home teams win about 54% of the time, and every
fan has a theory for why: the crowd, last change, the familiar boards.
The analytics version of that theory is the schedule: the home team is
rested and the visitor just flew in. I went in expecting the schedule to
explain most of the edge. It explains about a quarter of it. The building
itself is real. But inside that quarter, the mechanism is nothing like
the usual story. Miles traveled do nothing. How many games into a road
trip it is does nothing. What matters is two things: whether the visitor
played yesterday, and which way their body clock just moved.

## Why this would surprise someone who knows the field

People who follow hockey analytics know rest matters and know travel
matters, and the standard way to measure travel is hours shifted or
miles flown. Measured that way, timezone shift shows nothing at all in
these four seasons: home teams win 54.8% with no shift, 54.5% at one
hour, 53.6% at two, 53.5% at three. Flat. That flat line is the trap.
Split the same shifts by direction and a 9.5-point swing appears. When
the visitor flew east three hours, losing time, the home team wins
58.3%. When the visitor flew west three hours, gaining time, the home
team wins 48.8%, worse than a coin flip. The body clock is asymmetric:
flying east hurts and flying west does not, which is exactly what sleep
science predicts and exactly what a pooled "hours shifted" variable
erases. The second surprise is the same kind of asymmetry on the
calendar. A visitor on a back-to-back hands the home team 60.3% against
52.8% when rested, about 6.5 points after adjusting for team quality.
A home team on a back-to-back loses nothing at all. Sleeping in your own
bed erases the penalty. So the schedule's bite is narrow and specific:
the clock and the calendar, not the flight. A 1,000-mile trip and a
300-mile trip are worth the same once you know the direction and the
rest. That reframes what a "hard schedule" even is, and it means the
Western teams pay a structural tax the Eastern teams never see: San Jose
flies east two or three hours on 63% of its road games, Vegas on 62%,
while an Eastern team almost never flies east at all.

## What I built

| # | Question | Data | Script |
|---|----------|------|--------|
| 1 | How much of home ice is the schedule, and how much is the building? | 4,163 regular-season games, logistic model with Elo control, schedule-neutral counterfactual | `src/03_analysis.py` |
| 2 | Does the flight itself matter: miles, or trip length? | Arena-to-arena miles and road-trip game number for every visitor | `src/02_features.py`, `src/03_analysis.py` |
| 3 | Does timezone shift matter, or only its direction? | Venue UTC offsets vs each visitor's home offset (DST-safe) | `src/02_features.py`, `src/03_analysis.py` |
| 4 | Do back-to-backs tax both teams, or only the visitor? | Rest days and back-to-back flags for both teams | `src/03_analysis.py` |
| 5 | Which buildings are real fortresses once schedule and quality are stripped out? | Observed minus expected home wins per building | `src/03_analysis.py` |
| 6 | Does the story hold in the playoffs, where teams are rested? | Regular-season model applied to 256 playoff games | `src/03_analysis.py` |

Reproduce: `python3 src/01_fetch.py && python3 src/02_features.py &&
python3 src/03_analysis.py` (fetch takes ~90 seconds; the NHL API is
public and needs no key).

## Findings

**1. The schedule explains about a quarter of home ice, not most of it.**
Home teams won 54.3% of regular-season games. Set every schedule
feature to neutral (equal rest, no back-to-backs, no timezone shift,
first game of a trip, short hop) and the model still predicts 53.1%.
That leaves a 3.1-point residual building edge: crowd, last change,
line matchups, familiarity. Anyone telling you home ice is "all travel"
is wrong, and anyone telling you it is "all crowd" is missing a quarter
of it. The model controls for team quality with venue-blind Elo ratings
(K=20, reset each season), so this is not just good teams playing at
home.

**2. The direction gap is the biggest schedule effect in the sport.**
At a one-hour shift: 58.5% home wins when the visitor flew east (n=569)
against 50.4% when they flew west (n=569). At two hours: 56.1% vs
51.0%. At three hours: 58.3% (n=319) vs 48.8% (n=322). The pooled shift
is flat because the two directions cancel. If your model uses absolute
hours, you will conclude travel does nothing. It does plenty, in one
direction only.

**3. Back-to-backs tax only the visitor.** A visitor that played
yesterday loses 60.3% of the time (n=829) against 52.8% when rested
(n=3,334), about +6.5 points for the host after adjusting for quality
(p=0.005). A home team on a back-to-back shows no penalty at all
(p=0.50). At season scale that is roughly half an expected win per team
per season just from hosting tired visitors, about 8.4 such games a
year. The rest gradient itself is weak (about +1.6 points per extra rest
day, p=0.069, and non-monotonic in the raw split): it is the cliff of
zero rest days that bites, not each additional day.

**4. Miles and trip length are noise.** Each extra 1,000 miles of
visitor travel is worth +1.3 points and is not significant (p=0.40).
Each additional game into a road trip is worth +0.1 points (p=0.83),
and the raw split is flat from game 1 (54.0%) through game 4+ (55.5%).
The "grueling road trip" story does not survive contact with the data.
Teams do not wear down over a trip; they suffer on the day after a game
and on the morning their clock moved east.

**5. The true fortress ranking is not the loud-building ranking.**
After schedule and Elo, Carolina is the league's biggest residual
fortress (+11.3 points, 70.8% observed at home against 59.4% expected),
then Colorado (+9.0), Tampa Bay (+8.2), and Vegas (+8.1). At the bottom
are Chicago (-9.5), Vancouver (-9.4), and San Jose (-8.6). Standard
errors are about 4.3 points, so treat the middle of the list as noise
and the extremes as real. Colorado's altitude is a plausible piece of
its edge; Carolina's is not explained by anything in this model, which
is the point of a residual. Vegas is the interesting case: it has one
of the worst schedule profiles in the league and still clears +8, so
its edge is building, not calendar.

**6. Edmonton pays the tax and still holds its building.**
The Oilers won 60.0% at home against 56.0% expected, a +4.0-point
residual that sits inside the noise (plus or minus 4.4). The schedule
profile underneath is unfriendly: 37% of Edmonton's road games are
two-to-three-hour eastward trips, the bad direction, while visitors to
Rogers Place fly west, the favorable direction, far more often than
they fly east. Edmonton is not the league's most taxed team, the
Pacific clubs are worse, but it is on the paying side of the ledger in
both directions and still wins at home.

**7. The playoffs behave the way the model says they should.**
Playoff home teams won only 52.0% (n=256), below the regular-season
54.3%, which fits a world where teams are rested, nobody plays
back-to-backs, and travel is series-based. Applying the regular-season
model to playoff games predicts 53.3%, close to the observed 52.0%
given 256 games of noise. The transfer is not decisive, but it points
the right way: shrink the schedule tax and the home edge shrinks with
it. Playoff "home ice advantage" is worth less than the regular-season
number suggests, and a series price built on 54% is overpaying for it.

## Charts

- `charts/counterfactual.png` — observed 54.3% vs schedule-neutral 53.1%
- `charts/tz_direction.png` — east vs west at 1, 2, 3 hours
- `charts/back_to_back.png` — visitor rested vs back-to-back
- `charts/rest_diff.png` — home win rate by rest differential
- `charts/trip_game.png` — flat across road-trip game number
- `charts/fortress.png` — residual home edge by building

## Data and sources

- NHL public API (`api-web.nhle.com`, no key): club schedules for all
  32 current teams plus Arizona for 2023-24, seasons 2023-24 through
  2026-27 to Nov 3, 2026. 4,823 games fetched, 4,163 regular-season
  games analyzed after excluding 19 neutral-site games (Global Series
  and similar). 256 playoff games used for the transfer check.
- Arena coordinates are standard public arena locations, used only for
  the miles feature. Timezone shifts use each game's venue UTC offset
  against the visitor's home offset on that date, taken from the
  visitor's nearest home game, so daylight saving changes and Arizona's
  non-observance are handled by the data itself.
- `data/games_raw.csv` (fetched games), `data/games_features.csv`
  (regular-season features), `data/playoff_features.csv`,
  `data/findings.json` (every number in this README).

## Methods and limitations

Logistic regression of home win on Elo difference plus rest
differential, back-to-back flags, signed timezone shifts, travel miles,
road-trip game number, and season dummies. Pseudo-R-squared is 0.020:
single hockey games are mostly noise, and these effects are
season-scale, not per-game predictions. Do not use this model to pick
tonight's winner; use it to price a schedule.

Limitations, stated plainly: Elo is a coarse quality control, so the
fortress residuals absorb anything Elo misses (altitude, roster
construction for home matchups, coaching). Travel is arena-to-arena
distance, not actual flight paths or arrival times, which the API does
not publish. Rest is capped at seven days, and road-trip counts run
through preseason continuity at season openers. Overtime and shootout
wins count as wins. The timezone result is observational: eastward
trips correlate with which teams travel, and Elo only partly separates
that. The direction gap is large and consistent across all three shift
sizes, which is why it is reported as a finding rather than a quirk,
but a causal claim would need sleep and arrival-time data the league
does not publish.
