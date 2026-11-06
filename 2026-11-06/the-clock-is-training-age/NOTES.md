# Build #60 — working notes

## Topic
fitness (rotation: next was `fitness`; previous builds #59 philosophy, #58 sports)

## The question
When do powerlifters peak — and what clock sets the peak?

## Novelty test (stated before building)

The settled take in strength sports is that strength peaks in your late 20s /
early 30s and then biology takes it away: "start young or don't bother," and
masters lifting is damage control. Coaching lore nods at "training age" as a
concept, but nobody has measured, at scale, whether the peak is set by
biological age or by years since first competition.

This build measures it on the full OpenPowerlifting archive (4.06M meet rows,
~1M lifters, revision 4a1c65a7, 2026-10-31): for every lifter, first meet,
best-total meet, age at both, and the training age at the best total.

It would surprise an expert if:
1. Age at best total tracks *starting* age almost 1-for-1 (regression slope
   near 1) — i.e. lifters who start at 40 peak at ~46, not at 30. That means
   the "peak at 30" is not a biological clock, it is a training-age clock
   plus the fact that most lifters happen to start young.
2. At equal training age, late starters (45+) reach nearly the same relative
   strength (DOTS) as early starters (<25). If a 45-year-old starter with 6
   years in reaches ~90% of a 22-year-old starter's peak DOTS, the "you're
   too old to get strong" story is mostly wrong.
3. The cross-sectional age decline (median best DOTS by age band) flattens
   dramatically once you hold training age fixed — i.e. the famous post-35
   decline is mostly a composition effect: the 45-year-olds in the data are
   mostly people who started at 20 and have already been competing 15+ years
   (plateaued, declining, or hanging on), not 45-year-old beginners.
4. The attrition curve: the modal powerlifting career is one meet. The
   "peak" is mostly a survival filter, and comebacks after multi-year gaps
   regain most of their strength — which reframes the whole sport as a
   retention problem, not a biology problem.

If instead age-at-best clusters at ~30 regardless of starting age and late
starters top out far below early starters at equal training age, the settled
take wins and I will say so plainly and pivot the headline to whatever the
data actually shows (e.g. the attrition/comeback finding).

## Data
- OpenPowerlifting bulk CSV, revision 4a1c65a7, updated 2026-10-30/31:
  https://openpowerlifting.gitlab.io/opl-csv/files/openpowerlifting-latest.zip
  (164M zip, 4,059,941 rows). Public domain.
- Note: openpowerlifting.org and data.openpowerlifting.org were unreachable
  from this VM (connection reset); the GitLab Pages host of the same file
  worked. Verified same revision (4a1c65a7) and row count.

## Scope decisions
- Raw, full-power (Event=SBD), sanctioned meets only; TotalKg>0, Dots>0, Age known.
- Lifter key = Name + Sex (OPL has no lifter ID; standard practice, noted as a limit).
- First meet >= 2010-01-01 (database coverage is thin/uneven before that, so
  "first meet in the data" would be a bad proxy for first meet ever).
- Peak analyses use "completed careers": >=3 meets AND no meet in the last
  2 years of data (last meet <= 2024-10-31), so the best total is an observed
  peak, not a right-censored one.
- Collision guard: drop lifters whose recorded Age ever drops by >1 year
  across meets (same name, different person), and careers spanning >40 years.
