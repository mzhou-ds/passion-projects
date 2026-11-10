# NOTES — The Poppy Gap (build #64, 2026-11-10, culture)

## Novelty statement (written before building)

The settled take is "Canada does Remembrance Day, the US does Veterans Day, both 11 November, Commonwealth wears poppies." That sentence is true and tells you nothing. Nobody has measured the gap per capita, tested whether it tracks WWI sacrifice, or explained why it diverged. My hypothesis going in was that the gap tracks per-capita sacrifice. The data killed that hypothesis (New Zealand lost the most per capita and wears the fewest poppies of the Commonwealth three), and the replacement mechanism is sharper: the poppy survived only where 11 November stayed the country's single day of remembrance. The US split remembrance across Memorial Day and Veterans Day, and the flower fell between them. The twist that would surprise someone who knows the field: the poppy as a wearable symbol was invented by an American, Moina Michael, in 1918, and the American Legion adopted it before Canada did. The US did not reject the poppy; it misplaced it.

## Why this question, why today

Remembrance Day is tomorrow, 11 November. Michael spent yesterday trying to get a poppy in San Francisco and ended up emailing the Canadian consulate. The build measures exactly that experience.

## What failed

- Google Trends (pytrends) is blocked from this environment: trends.google.com read-times-out on every attempt, three tries, two separate sessions. Per the standing lesson (stop on timeouts, don't retry into a block), the Trends leg was dropped. The commercialization angle (Veterans Day sale vs Remembrance Day sale) is therefore argued qualitatively in the README, not measured. `src/fetch_trends.py` is kept so the pull can be rerun from another machine.
- "Buddy poppy" has no standalone Wikipedia article, so the pageviews pull covers "Remembrance poppy" only. Noted in the fetch script.
- The service restarted mid-run and wiped /tmp, including the pytrends venv. Recreated it; the Trends failure is a network block, not a venv issue.
- No national Poppy Appeal totals exist for Australia or New Zealand dollars, so those countries are partial in the charts. This is disclosed in the caveats rather than estimated.

## Numbers to double-check next year

- VFW Buddy Poppy dollar total is a 2018 figure ($12-15M). Worth re-sourcing if the VFW publishes a current one.
- Canada 2025 campaign total (the 2026 campaign launched 24 Oct 2026; its total lands in early 2027).
