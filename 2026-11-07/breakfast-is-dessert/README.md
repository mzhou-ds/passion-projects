# Breakfast Is Dessert

**Build #61 — Musing with Mike — 2026-11-07 — nutrition**

The most important meal of the day is also the sweetest meal of the day,
except for the one we call a snack. The average American breakfast carries
6.48 grams of sugar per 100 calories. Lunch carries 4.03. Dinner carries
3.45. A snack carries 7.46. Breakfast sits right next to the snack slot and
nowhere near lunch or dinner. And most breakfasts are dessert by the
numbers: 55.5 percent of adult breakfasts get more than a quarter of their
calories from sugar. For kids it is 67.7 percent, and the average kid's
breakfast is exactly as sweet as the average adult snack.

This is not a story about cereal being sugary. Everyone knows that. It is a
measurement nobody had made: put the meal with the health halo on the same
scale as the occasions we call snacks, and see which one is sweeter.

## Findings

**1. Breakfast is the second-sweetest meal, and it is not close.**
Adults 20 to 79, NHANES 2007 to 2018, day 1 recalls, survey-weighted.
Breakfast: 6.48 g sugar per 100 kcal (95% CI 6.39 to 6.57). Snack: 7.46
(7.36 to 7.57). Lunch: 4.03. Dinner: 3.45. The gap between breakfast and
snack is 0.98. The gap between breakfast and lunch is 2.45. Breakfast is
closer to dessert than it is to lunch. The 9pm snack, the closest thing to a
dessert slot in the data, runs 7.41, barely above breakfast's 6.48. The
median breakfast gets 27.2 percent of its calories from sugar. The median
dinner gets 10.9 percent. See `charts/01_sugar_density_by_meal.png`.

**2. Most breakfasts are dessert by the numbers.** 55.5 percent of adult
breakfasts are over 25 percent sugar calories. 46.2 percent are over 30
percent. 38.2 percent are sweeter than the median snack occasion itself.
This is not a few sugary outliers dragging a mean around. It is the middle
of the distribution. And it survives the obvious objection: throw out every
breakfast under 300 calories, the coffee-with-sugar and the single banana,
and 47.7 percent are still over 25 percent. The typical breakfast carries
17.5 g of sugar, about 4.4 teaspoons, which is more sugar in grams than the
typical snack (11.8 g). See `charts/02_breakfast_distribution.png`.

**3. Kids' breakfasts are literally as sweet as snacks.** Children 2 to 19:
breakfast runs 7.41 g per 100 kcal against the adult snack's 7.46. Two out
of three kids' breakfasts (67.7 percent) are over 25 percent sugar calories,
and 56.7 percent are over 30 percent. For kids the title of this build is
not a stretch. It is the measured value.

**4. Breakfast quietly got 15 percent less sweet while nobody was watching.**
From 2007-08 to 2017-18, breakfast sugar density fell from 6.90 to 5.87,
and the share of breakfasts over 25 percent sugar fell from 59.7 to 49.1
percent. Snacks fell too, from 7.87 to 7.09. The whole public conversation
about sugar in that decade was about soda. Breakfast improved anyway, and
no single food group drove it. Fruit's share of breakfast sugar fell from
21.3 to 16.4 percent while sugars, sweets and beverages rose from 26.4 to
29.4 percent, which looks like less juice and whole fruit at the table and
more sweetener in the coffee and the pastry. Kids improved as well, from
7.87 to 7.03, but they started so sweet that they still end the decade
sweeter than adults started it. See `charts/04_trend.png`.

**5. A third of America's sugar is eaten before noon.** 32.2 percent of the
day's sugar lands before 12:00. Breakfast supplies 19.9 percent of daily
sugar on only 16.0 percent of daily calories. The morning is sugar-dense
relative to the rest of the day, which is the opposite of how we talk about
it. See `charts/03_sugar_clock.png`.

**6. The sweet breakfast has no income gradient, and the BMI gradient runs
backwards.** Breakfast sweetness is flat across poverty bands: 6.49 below
1.3x the poverty line, 6.33 in the middle, 6.59 above 3.5x. Rich and poor
eat equally sweet breakfasts. By body mass it inverts: the leanest adults
(BMI under 18.5) eat the sweetest breakfasts at 7.12, and it falls steadily
to 6.09 at BMI 30 and over. By race the spread is small: 5.66 for Mexican
American adults up to 6.68 for non-Hispanic White adults. Women eat
slightly sweeter breakfasts than men (6.77 vs 6.23). None of this is a story
about one group eating badly. It is a story about the default breakfast
being sweet for everyone.

**7. Sugar is the one nutrient that cannot tell breakfast from a snack.**
Train a gradient boosting model on nutrients alone to separate breakfast
occasions from snack occasions and it does fine, AUC 0.89. It does it on
protein, caffeine and sodium, the eggs and the coffee and the salt. But
hand it sugar density alone and it scores 0.46, worse than a coin flip.
Sugar is the blind spot. Breakfast is a real meal with a real profile, eggs
and coffee and a bigger plate, and on sweetness it is the same event as a
snack wearing a different name. See `charts/06_classifier.png`.

**8. Where the sugar comes from.** Four food groups carry 96 percent of
breakfast sugar: sugars, sweets and beverages 27.9 percent, grains 25.7
percent, milk and dairy 22.0 percent, fruit 20.0 percent. The single
biggest contributor is milk, milk drinks and yogurt at 17.9 percent, which
is mostly lactose plus flavored milk. Then sugars and sweets at 13.9
percent, nonalcoholic beverages (juice drinks, sweetened coffee and tea)
at 12.1 percent, ready-to-eat cereal at 8.9 percent, and fruit at 8.3
percent citrus and other fruit plus the juice subgroups. The fruit share is
the honest caveat on this whole build: a fifth of breakfast sugar is fruit,
and some of that is a banana, not a Pop-Tart. The other four fifths are
not. See `charts/05_whats_in_it.png`.

## What to do with this

If you sell breakfast, the halo is the product. Cereal, yogurt, juice and
pastry all borrow the reputation of the most important meal of the day, and
the data says the reputation is doing more work than the food. The trend in
finding 4 is the opening: breakfast got 15 percent less sweet in a decade
without anyone campaigning for it, which means the category moves when the
products move, not when the messaging moves. The cheapest version of a
better breakfast is not a lecture. It is the same plate with the juice
swapped for the fruit and the sweetened yogurt swapped for the plain one.
That is a product decision, not a willpower decision.

If you eat breakfast, the test is simple. Look at the share, not the grams.
If a quarter of your breakfast's calories are sugar, you ate dessert. The
explorer in this folder lets you set your own line and see how many
breakfasts fall past it.

## Methods

Data: NHANES dietary recalls (What We Eat in America), cycles 2007-08
through 2017-18, Individual Foods files DR1IFF and DR2IFF, plus
demographics and body measures. Primary analysis uses day 1 only with the
day-1 dietary weight WTDRD1. Adults 20 to 79 with a reliable recall and a
plausible day (500 to 6,000 kcal): 24,156 person-days, 135,625 occasions.
Children 2 to 19 are a secondary panel (300 to 6,000 kcal).

Occasions: food items collapsed to one row per person, clock time and
occasion name. Occasion names are the respondent's own: breakfast (codes 1,
10), lunch (2, 11, 12, 5), dinner (3, 4, 14), snack (6, 13, 15, 16, 17,
18), drink (7, 19). Sugar density is a ratio of sums, total weighted sugar
over total weighted calories, so big occasions count more than small ones.
Confidence intervals come from a 300-replicate cluster bootstrap that
resamples people. Day 2 is a sensitivity check: breakfast 6.55, snack 7.63,
same story.

Classifier: breakfast vs snack occasions, features are nutrient densities
(sugar, protein, fat, carb, fiber, sodium, caffeine per 100 kcal), occasion
size and clock time. Train/test split by person so no person's occasions
appear on both sides. XGBoost (300 trees, depth 4) and logistic regression,
with SHAP on the nutrients-only model.

Explorer: `explorer.html` is a self-contained page with a slider for the
dessert line. The curves are the survey-weighted survival functions from the
occasion data, precomputed at 1 percent steps.

## Limitations

- **Total sugars, not added sugars.** These NHANES cycles do not carry
  added sugars in the individual-foods files. Intrinsic sugars from fruit
  and plain milk count. Finding 8 exists so the reader can see how much of
  breakfast sugar is fruit (20 percent) versus everything else.
- **Recalls are self-reported.** People round times and forget items. Day 2
  is collected by phone and runs about 100 kcal lower. The day-2 sensitivity
  check reproduces every headline number.
- **Occasion names are the respondent's own.** The comparison is between
  named occasions, which is the point: the test is about the meal's
  reputation, so the name is the treatment. A 10pm "snack" of cake and a
  7am "breakfast" of cake are different rows because the person named them
  differently.
- **Drink and other occasions are excluded from the meal comparison.**
  Near-zero-calorie items (a sugar packet in black coffee, reported on its
  own) make their sugar ratios meaningless. The four named meals are the
  comparison set.
- **2007 to 2018 only.** Later NHANES cycles use a different food-code
  system and were not in the local extract. The trend stops at 2017-18.

## Reproduce

```
python src/build_occasions.py  # NHANES XPT files -> data/occasions.parquet
python src/analyze.py          # headline stats -> output/results.json
python src/followups.py        # sensitivities, trend decomposition
python src/model.py            # classifier + SHAP -> output/model.json
python src/charts.py           # charts/*.png
python src/make_explorer.py    # explorer.html
```

## Sources

- CDC/NCHS, NHANES 2007-08 through 2017-18 dietary recall files (DR1IFF,
  DR2IFF, DEMO, BMX), https://www.cdc.gov/nchs/nhanes/
- USDA Food and Nutrient Database for Dietary Studies (FNDDS) coding
  scheme, for the food-group labels in finding 8
- Local copies of the NHANES files were reused from build #56
  (`2026-10-28/nutritional-jetlag`); no new download was needed
