# Build #61 — "Breakfast Is Dessert" (working title) — pre-registration

Date: 2026-11-07. Topic: nutrition. Data: NHANES dietary recalls,
cycles 2007-08 through 2017-18 (DR1IFF + DR2IFF), day 1 primary,
WTDRD1 survey weights. Adults 20-79 primary; children 2-19 secondary.

## The novelty case (why an expert would be surprised)

Everyone in nutrition "knows" two things: breakfast cereal is sugary, and
dessert is sugary. Nobody has measured the two against each other at
population scale. The settled take is that breakfast is the virtuous meal
("the most important meal of the day") and the sweet stuff lives in the
evening snack slot. This build puts the meal America calls breakfast on the
same scale as the occasions it calls snacks — grams of sugar per 100 kcal —
and asks whether the virtuous meal is actually the sweetest one on the clock.

What would surprise someone who knows the field:
1. A head-to-head number: breakfast sugar density vs snack sugar density,
   and vs the 9pm snack (the dessert slot). If breakfast is at or above the
   snack line, the reputation of the meal is backwards.
2. A share nobody has published: the fraction of American breakfasts that
   cross the sugar density of a typical dessert occasion. A mean can hide
   behind a few sugary outliers; a share cannot.
3. The trend: did breakfast get sweeter or less sweet from 2007 to 2018
   while the whole public conversation was about soda?
4. The mechanism: which food groups actually carry breakfast sugar
   (cereal? juice? pastry? the milk?), and whether a model can even tell a
   breakfast occasion from a snack occasion by its nutrient profile alone.
   If it cannot, breakfast and snack are the same event wearing two names.

## Pre-registered primary question

Is the population-average breakfast sweeter (total sugars per 100 kcal)
than the population-average snack occasion, and what share of breakfasts
exceed the median snack occasion's sugar share of calories?

## What would change the headline

- If breakfast < snack on sugar density: the headline becomes the gap
  itself (how much less sweet, and which meal is actually the sweetest),
  or the trend / demographic split if that is where the surprise is.
- If the "dessert threshold" share is small (<10%): the story is that
  breakfast's reputation survives the test, and the finding is the
  distribution, not the mean.
- No headline will be asserted from a mean alone; every claim is paired
  with the share, the trend, and the food-group decomposition.

## Outcome vs pre-registration (recorded 2026-11-07, after analysis)

- Primary question, answered NO on the mean: breakfast 6.48 g/100 kcal vs
  snack 7.46 (CIs 6.39-6.57 vs 7.36-7.57, no overlap). Breakfast is 87% as
  sweet as a snack, not sweeter. The headline pivoted per the pre-registered
  rule to the gap itself plus the share: breakfast sits 0.98 from the snack
  line and 2.45 from lunch, and 55.5% of breakfasts cross the 25% dessert
  line.
- The kids' panel is where the title holds literally: kids' breakfast 7.41
  vs adult snack 7.46.
- The classifier guess was wrong in the interesting direction: nutrients
  alone separate breakfast from snack well (AUC 0.89), but sugar is the
  blind spot (single-feature AUC 0.46). The finding is not "you cannot tell
  them apart" but "sugar is the one thing that cannot tell them apart."
- The trend went the other way from the natural guess: breakfast got 15%
  less sweet 2007-2018, not sweeter. No single food group drove it.
- Two genuinely surprising nulls: no income gradient in breakfast
  sweetness, and the BMI gradient runs backwards (leanest eat sweetest).

## Known limitations (stated up front)

- Total sugars, not added sugars: NHANES individual-foods files for these
  cycles do not carry added sugars. Intrinsic sugars (fruit, plain milk)
  count. The food-group decomposition exists precisely so the reader can
  see how much of breakfast sugar is fruit/milk vs cereal/pastry/juice.
- Recalls are self-reported; day 2 is by phone and runs ~100 kcal lower.
  Primary analysis uses day 1 only; day 2 is a sensitivity check.
- Occasion names are the respondent's own ("breakfast", "snack"); the
  comparison is between named occasions, which is the point: the test is
  about the meal's reputation, so the name is the treatment.
- Clock times are heaped (see build #56); occasion-level sugar density
  does not depend on exact timing, only on the name and the hour band.
