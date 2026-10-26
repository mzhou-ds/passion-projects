# The Fake Sage Speaks Wellness

*Musing with Mike · 2026-10-26 · Topic: philosophy · Build #50*

Somewhere on your feed today there is a quote card. A soft gradient, a serif font, a line about your journey and your inner light, signed Laozi. He never said it. Everybody in quote scholarship knows individual fakes get passed around, and sites like Quote Investigator debunk them one at a time, like pulling single weeds. What nobody had done, as far as I can find, is count the whole garden. So this build counts it, and then asks the more interesting question. If the fakes were random noise, they would sound like the real thing. Do they?

The dataset is Wikiquote, which turns out to be the one place on the internet that sorts quotations into editorial buckets at scale: sourced to a named work, disputed, misattributed, or attributed with no source at all. I pulled the full pages for 28 thinkers, 8 Eastern sages, 19 Western philosophers, and Alan Watts as the bridge figure, and parsed out 4,253 quote entries with their bucket labels. Then I measured the language of each bucket and trained a classifier to see if a quote's voice alone gives away whether it is real.

## Why this would surprise someone who knows the field

Quote debunking treats every fake as an isolated accident, a game of telephone that went wrong once. The data says the fakes are not accidents in aggregate. They form a dialect. Across 28 thinkers, the invented quotes are half the length of the real ones, use therapy and self-help vocabulary at more than twice the rate, and talk to *you* at two and a half times the rate. And the dialect is not spread evenly. It is projected hardest onto the Eastern sages, whose fake quotes carry two and a half times the therapy vocabulary of fake Western quotes, even though their real writings differ from Western ones by far less. The internet did not just misquote Laozi. It recast him, and the recast version is a wellness coach.

## Finding 1: Laozi is the most faked sage in the canon, and it is not close

Of the quotes Wikiquote's editors could actually check, 19.1 percent of Laozi's canon is disputed or misattributed, the worst rate of all 28 thinkers. Voltaire is second at 14.8 percent, then Sun Tzu at 13.3, the Buddha at 12.9, and Aristotle at 12.7. The pooled rate across everyone is only 3.9 percent, so this is not a uniform fog. It concentrates.

Laozi is also, quietly, the most read philosopher in the set. His Wikipedia article drew 4.61 million views in 2024, more than Marcus Aurelius at 3.34 million and more than double Nietzsche. Fame and fakeness do travel together across the 28, but loosely: the Spearman correlation between 2024 pageviews and fake rate is 0.32 with a p-value of 0.09. Suggestive, not proven. I am reporting it as suggestive.

The fakes also migrate between sages. The single most famous line pinned on Confucius, "the journey of a thousand miles begins with a single step," sits in the Misattributed section of his page. It is a loose rendering of chapter 64 of the Tao Te Ching. It belongs, in other words, to Laozi, the one thinker with an even bigger fake problem. A good line does not die when it is debunked. It just changes its sage.

## Finding 2: the real East-West gap is not fakes. It is missing sources.

On proven fakes, the Eastern median is 6.3 percent of a thinker's checked canon against 3.2 percent for the West, and with only 8 Eastern thinkers that gap is not significant (permutation p = 0.23). I want to be straight about that, because the sharper result is next to it.

Count everything that cannot be traced to a source, the disputed, the misattributed, and the plain "attributed" quotes with no work named, and the gap opens up. The median Eastern thinker has 13.1 percent of his Wikiquote canon unverifiable. The median Western thinker has 3.2 percent. That difference is significant (permutation p = 0.021).

Rumi is the extreme case and he is worth pausing on. Of his 442 quote entries, 370, or 84 percent, are listed as attributed with no source text at all. Only 67 are tied to the Masnavi or the Divan. The Rumi that English readers quote is mostly a free-floating tradition of lines that passed through old anthologies and modern paraphrase, including translators who openly rework him rather than translate him. Voltaire has the same disease in milder form at 42 percent unverified. The Western canon mostly arrives with receipts because it was written in languages its quoters read, printed early, and argued over by scholars in the same tongue. The Eastern canon in English arrives through translation chains, and at every link in the chain the receipt gets easier to lose.

## Finding 3: fake quotes speak a different dialect, and you can hear it within a single thinker

Pool all 147 proven fakes against all 3,653 sourced quotes:

| Feature | Fake | Sourced |
|---|---|---|
| Median length | 15 words | 34 words |
| Therapy / self-help words per 1,000 | 23.6 | 10.0 |
| Second person per 1,000 | 25.7 | 9.9 |
| First person per 1,000 | 33.1 | 20.8 |

The length gap is the biggest single effect (Cohen's d of minus 0.57), with therapy vocabulary and second person close behind (d of 0.54 and 0.50). The obvious objection is that this just compares different authors, so I ran the test that controls for the author. Take only the 20 thinkers who have at least 3 fakes of their own, and compare each man's fakes against his own real quotes. The fakes still run warmer and more personal: therapy vocabulary higher, Wilcoxon p = 0.036, and second person higher, p = 0.008. Same sage, two voices. One of them wrote books. The other one writes quote cards.

A model can hear it too. An XGBoost classifier given nothing but these language features, no author names, no topics, separates fake from sourced at an AUC of 0.74 in cross-validation. SHAP values say length does most of the work, then first person, therapy vocabulary, and second person. The quotes the model flags hardest read exactly like the feed: "You become what you give your attention to," filed as misattributed under Epictetus. "You yourself, as much as anybody in the entire universe, deserve your love and affection," filed as misattributed under the Buddha. Short, warm, second person, built to be saved and shared.

## Finding 4: the wellness voice is aimed at the East

Here is the comparison I did not expect to be this clean. Fake quotes pinned on Western thinkers carry therapy vocabulary at 17.0 words per thousand. Fake quotes pinned on Eastern sages carry it at 42.4 per thousand, two and a half times as much, with second person at 42.3 against 19.9. Their real writings are not nearly that far apart: sourced Eastern quotes sit at 15.1 per thousand against 9.1 for sourced Western ones. So the projection is not a magnified version of a real difference. It is mostly invention. When the internet needs a line about healing, journeys, and your inner light, it does not sign it Kant. It signs it Rumi or the Buddha, whether they wrote anything like it or not.

There is an operator's lesson in this, and it is the same one from every marketplace I have worked in. The fake dialect is not a corruption of the product. It is the product, optimized. A real line from the Tao is long, strange, and often about governing a state. It does not fit a quote card and it does not make a stranger feel seen in four seconds. The invented line does both, so it outcompetes the real one in every feed it enters, and the sage's name is just the trust mark that gets it past your guard. Provenance is the mispriced asset here. The receipts exist, Wikiquote keeps them for free, and almost nobody checks, which is exactly why the fakes win.

## What would change my mind, and the honest limits

- Wikiquote's buckets are editorial judgment, not ground truth. A quote marked sourced is sourced to Wikiquote's standard, and the disputed sections are only as complete as the editors who maintain each page. Famous thinkers get more editorial attention, which cuts both ways: more fakes caught, and more quotes checked.
- Fake counts per thinker are small. Laozi's headline 19.1 percent is 9 fakes out of 47 checked quotes. The per-thinker rates should be read as rankings with wide error bars. The dialect results, which pool 147 fakes and repeat within authors, stand on firmer ground.
- "Attributed with no source" is not the same as fake. Rumi's 84 percent includes lines from a genuine centuries-old anthology tradition. What it measures is the absence of a checkable source in the form English readers actually consume, which is the thing that lets real fakes blend in.
- The therapy lexicon is my judgment call, frozen in `src/03_analyze.py` before the group comparisons. The headline does not rest on it alone: length and second person are lexicon-free and tell the same story.
- Pageviews are an imperfect fame proxy. The Buddha's views are split across the "Buddha" and "Gautama Buddha" article titles, so his fame is understated here, one more reason the fame correlation is reported as suggestive.
- English Wikiquote only. The fake-quote economy in other languages has different sages and probably a different dialect.

## Run it

```bash
pip install -r requirements.txt
python3 src/01_fetch.py    # Wikiquote wikitext + 2024/2025 Wikipedia pageviews for 28 thinkers
python3 src/02_parse.py    # section-aware parse -> data/quotes.csv (4,253 quotes with bucket labels)
python3 src/03_analyze.py  # rates, dialect stats, paired tests, XGBoost + SHAP -> results.json
python3 src/04_charts.py   # charts/
```

Key outputs: `results.json` (every number above), `data/per_thinker.csv`, `data/quotes_features.csv` (every quote with its language features, the reusable asset here), and charts: `provenance_stack.png`, `fake_dialect.png`, `east_west_wellness.png`, `fame_vs_fake.png`, `shap_importance.png`.

## Sources

- English Wikiquote pages for the 28 thinkers (Laozi, Confucius, Mencius, Zhuangzi, Gautama Buddha, Sun Tzu, Rumi, Kahlil Gibran, Alan Watts, Socrates, Plato, Aristotle, Heraclitus, Epicurus, Marcus Aurelius, Epictetus, Seneca the Younger, Voltaire, Jean-Jacques Rousseau, Immanuel Kant, Arthur Schopenhauer, Søren Kierkegaard, Friedrich Nietzsche, Ralph Waldo Emerson, Henry David Thoreau, William James, John Stuart Mill, Bertrand Russell), fetched via the MediaWiki API on 2026-10-26. Raw wikitext and the fetch log are in `data/raw/`.
- Wikimedia pageviews API, English Wikipedia monthly views for calendar 2024 (and Jan to Sep 2025, in the fetch log).
