"""Measure how much of each wisdom text is literally telling you what to do.

Sentence splitter: regex-based, abbreviation-protected (NLTK data downloads
are blocked in this environment, so no punkt tagger).

Imperative classifier: rule-based on the sentence's first content word.
A sentence counts as imperative when it opens with a base-form verb from a
curated list, or with 'let' / 'do not' / 'never' + verb, and is not excluded
by the guards (first word a common noun, second word a copula, etc.).
The classifier is validated against a hand-labelled stratified sample in
src/validate_classifier.py.
"""
import re, os, json, csv, random, statistics
from collections import Counter

CLEAN = "data/processed/clean"
OUT = "data/processed"

TEXTS = [
    ("tao_te_ching.txt", "Tao Te Ching", "East", "Legge 1891"),
    ("analects.txt", "Analects", "East", "Legge 1861"),
    ("zhuangzi.txt", "Zhuangzi", "East", "Giles 1889"),
    ("dhammapada.txt", "Dhammapada", "East", "Müller 1881"),
    ("gita.txt", "Bhagavad Gita", "East", "Arnold 1885"),
    ("upanishads.txt", "Upanishads", "East", "Müller 1879"),
    ("meditations.txt", "Meditations", "West", "Haines 1916"),
    ("enchiridion.txt", "Enchiridion", "West", "Rolleston 1881"),
    ("seneca_letters.txt", "Seneca, Letters 1-20", "West", "Gummere 1917"),
    ("ecclesiastes.txt", "Ecclesiastes", "West", "KJV 1611"),
    ("proverbs.txt", "Proverbs", "West", "KJV 1611"),
    ("emerson_essays.txt", "Emerson, Essays I", "West", "1841"),
    ("walden.txt", "Walden", "West", "1854"),
]

ABBR = ["Mr", "Mrs", "Ms", "Dr", "St", "vs", "e.g", "i.e", "etc", "pp", "ch",
        "vol", "ed", "no", "viz", "cf", "ca", "B.C", "A.D", "Jan", "Feb", "Mar",
        "Apr", "Jun", "Jul", "Aug", "Sep", "Sept", "Oct", "Nov", "Dec",
        "Chap", "Bk", "Fig", "U.S", "U.S.A", "Capt", "Lieut", "Gen", "Col",
        "Messrs", "M", "Mme", "Mlle"]
ABBR_RE = re.compile(r"\b(" + "|".join(re.escape(a) for a in ABBR) + r")\.")

def split_sentences(text):
    # protect abbreviations, then split on terminal punctuation
    text = ABBR_RE.sub(lambda m: m.group(1).replace(".", "\x01"), text)
    # also protect decimals / initials like "A. B."
    text = re.sub(r"\b([A-Z])\.", lambda m: m.group(1) + "\x01", text)
    parts = re.split(r"([.!?…]+[\"'”’\)\]]*\s+)", text)
    sents, buf = [], ""
    for p in parts:
        buf += p
        if re.search(r"[.!?…]+[\"'”’\)\]]*\s+$", p):
            sents.append(buf.strip()); buf = ""
    if buf.strip():
        sents.append(buf.strip())
    # paragraph breaks are also boundaries for verse-like texts
    out = []
    for s in sents:
        for chunk in re.split(r"\n\s*\n", s):
            c = chunk.strip()
            if c:
                out.append(c)
    # restore abbreviation dots
    out = [s.replace("\x01", ".") for s in out]
    # filter fragments: need >=3 words and at least one letter;
    # drop chapter-heading / navigation junk that survives cleaning
    kept = []
    for s in out:
        words = re.findall(r"[A-Za-zÀ-ÿ'’-]+", s)
        if len(words) < 3 or not re.search(r"[A-Za-z]", s):
            continue
        if "sister projects" in s or "→" in s or "←" in s:
            continue
        letters = [w for w in words if w.isalpha()]
        if letters and all(w.isupper() for w in letters):
            continue  # all-caps chapter title, e.g. OF THE BHAGAVAD-GITA
        kept.append(s)
    return kept

# --- imperative classifier -------------------------------------------------
IMPERATIVE_VERBS = set("""abandon abide accept acquire act adhere admire admit advance advise aim allow answer apply approach arise ask aspire attend attain avoid awake bear be become beg behave believe benefit beware bid blame bless boast borrow bow break breathe bring build burn buy call calm care carry cast cease celebrate change cherish choose claim cleanse clear climb close collect come comfort command commit compare complain complete conceive concentrate concern conclude confess conquer consider console contemplate content continue control correct count create cry cultivate curb cure dare deal decide declare decline dedicate defeat defend delay delight deliver demand deny depend describe desire despise destroy detect develop devote die differ dig direct discern discipline discover discuss dislike dismiss display dispose dispute disregard distinguish distribute divide do doubt draw dread dream drink drive dwell eat employ empty endure enjoy enter entertain envy escape eschew esteem estimate examine exceed excuse exercise expect experience explain explore express extend face fail fall fear feed feel fight find finish fix flee fly follow forbear forbid force forget forgive forsake foster free fulfil gain gather give go govern grasp guard guide handle happen harm hasten hate have hear heed help hide hold honor hope humble hurry hurt ignore imagine imitate improve incline increase indulge inform inquire inspire instruct intend invite judge keep kill kindle know labour lack laugh lay lead learn leave lend let lie lift light like limit listen live look lose love make manage mark marry master measure meditate meet mend mention mind miss mistake mix mourn move name need neglect note notice obey observe obtain offer open oppose order overcome owe own pass pause pay perceive perform persist persuade pick place plan plant play please ponder possess practise practice praise pray prefer prepare preserve press pretend prevent proceed produce profit promise promote protect prove provide pull punish purchase pursue push put question quiet quit raise reach read realise realize reason receive reckon recognise recognize recollect recover reduce reflect refrain refuse regard rejoice relax release rely remain remember remind remove render renew repent reply reproach require rescue resist resolve respect rest restrain retire return reveal revere reward ride rise risk roam rule run save say search see seek seize select sell send sense serve set settle shake share shed shine shun shut sigh sign sing sink sit sleep smile speak spend stand stay steal step stir stop store strive struggle study submit suffer suppose suppress surrender surround survive swallow swear sweep take talk taste teach tell tempt tend thank think throw touch train travel treat tremble trust try turn understand undertake use utter value vanish venture view visit wait wake walk wander want warn wash watch wear weep weigh welcome whisper win wish withdraw witness wonder work worry worship wound wrap write yield show curse greet beckon summon grow smell mean attempt succeed attack retreat march sail swim jump dance treasure adore grieve request""".split())

# first words that are far more often nouns/subjects than commands in these texts
NOUN_FIRST = set("""shun like love work life time death man men woman child father mother son brother people nation city house day night morning evening year season water fire wind stone tree mountain river road way path door gate book word speech silence action thought deed thing things mind heart soul spirit self friend master sage king god heaven earth body virtue wisdom truth nature world pleasure pain fear hope faith desire will reason knowledge ignorance doubt certainty beauty goodness justice law custom habit opinion impulse passion appetite sense sight sound taste smell tongue eye ear hand foot head tongue""".split())

NON_STARTERS = set("""the a an this that these those it he she they we you i if when while but and for so as with in on at by from of to there here now then thus hence therefore however yet still also not no what who which whose whom why how where all every each some many few both either neither one two three four five six seven eight nine ten first second third nor or""".split())

def first_content_word(sent):
    s = sent.strip()
    s = re.sub(r"^\[\s*\d+\s*\]\s*", "", s)
    # strip leading quotes, brackets, section markers (I., alpha., 1., etc.)
    s = re.sub(r"^[\s\"'“‘\(\[\{«»—–-]+", "", s)
    s = re.sub(r"^([IVXLCDM]+\.|[a-zα-ω]\.|[0-9]+[.)])\s+", "", s, flags=re.I)
    s = re.sub(r"^[\s\"'“‘\(\[\{«»—–-]+", "", s)
    m = re.match(r"([A-Za-zÀ-ÿ]+)", s)
    return (m.group(1).lower(), s) if m else (None, s)

def is_imperative(sent):
    # a vocative opening ("O mind, remember thy deeds!") is not the command;
    # the word after the vocative comma is
    m = re.match(r"^\s*[\"'\u201c\u2018]*O\s+[A-Za-z\u00c0-\u00ff]+,\s+", sent)
    if m:
        sent = sent[m.end():]
    w, s = first_content_word(sent)
    if not w:
        return False
    # a question is not a command, however it starts
    if sent.rstrip().rstrip("\"'”’)]").rstrip().endswith("?"):
        return False
    low = s.lower()
    if re.match(r"do\s+what\b", low):
        return False
    if low.startswith("let ") and "rather than" in low:
        return False
    # cross-references, not commands ("See ch. i.", "See Lun Yü, ix, 27")
    if low.startswith("see "):
        ref_words = {"ch", "ch.", "chap", "chap.", "lun", "post", "ix", "iv", "vi", "vii", "viii", "xi", "xii", "p", "p.", "pp", "pp."}
        if any(w in ref_words for w in re.findall(r"[a-z.]+", low)):
            return False
    # hypotheses, not commands ("Suppose they were virtuous", "Say he was...")
    if w == "suppose":
        return False
    if w == "say" and re.match(r"^(he|she|it|they|we|you)\b", low.split(None, 1)[1] if len(low.split(None, 1)) > 1 else ""):
        return False
    # fixed-phrase exclamations ("Praise to Thee!", "Talk of heaven!")
    if (w == "praise" and low.startswith("praise to")) or (w == "talk" and low.startswith("talk of")):
        return False
    if low.startswith("let ") or low.startswith("let us") or low.startswith("let him") \
       or low.startswith("let her") or low.startswith("let them") or low.startswith("let the"):
        return True
    if re.match(r"(do not|don't|do)\s+[a-z]", low):
        return True
    if re.match(r"never\s+([a-z]+)", low):
        nw = re.match(r"never\s+([a-z]+)", low).group(1)
        if nw in IMPERATIVE_VERBS or nw in ("do", "let"):
            return True
        return False
    if w in NON_STARTERS or w in NOUN_FIRST:
        return False
    if w not in IMPERATIVE_VERBS:
        return False
    # guards: 'Love is...' / 'Work was...' (subject + copula) and 'Know that...' is fine
    rest = s[len(w):].strip()
    if re.match(r"^(is|are|was|were|has|have|had|seems|seemed|will|shall|would|can|could|may|might)\b", rest, re.I):
        return False
    return True

# --- word-list rates --------------------------------------------------------
NEG = set("not no never without nothing none neither nor cannot can't couldnt couldnt won't wouldnt shouldn't isn't aren't wasn't weren't doesn't don't didn't hasn't haven't hadn't".split())
OBLIG = set("must should ought shall".split())
SECOND = set("you your yours thou thy thee ye".split())
FIRST = set("i me my mine we us our ours".split())
SELF = set("self soul mind heart spirit".split())

def word_rate(words, vocab):
    return 1000.0 * sum(1 for w in words if w in vocab) / max(1, len(words))

def analyze_file(fname):
    txt = open(os.path.join(CLEAN, fname), encoding="utf-8").read()
    sents = split_sentences(txt)
    words = re.findall(r"[A-Za-zÀ-ÿ'’-]+", txt.lower())
    words = [w.strip("'’-") for w in words]
    imp = sum(1 for s in sents if is_imperative(s))
    q = sum(1 for s in sents if s.rstrip().endswith("?"))
    lens = [len(re.findall(r"[A-Za-zÀ-ÿ'’-]+", s)) for s in sents]
    return {
        "sentences": len(sents),
        "words": len(words),
        "imperative_share": 100.0 * imp / max(1, len(sents)),
        "imperative_n": imp,
        "question_share": 100.0 * q / max(1, len(sents)),
        "negation_per_1000": word_rate(words, NEG),
        "obligation_per_1000": word_rate(words, OBLIG),
        "second_person_per_1000": word_rate(words, SECOND),
        "first_person_per_1000": word_rate(words, FIRST),
        "self_words_per_1000": word_rate(words, SELF),
        "will_per_1000": word_rate(words, {"will"}),
        "median_sentence_len": statistics.median(lens) if lens else 0,
        "mean_sentence_len": statistics.mean(lens) if lens else 0,
    }

def main():
    rows = []
    for fname, title, trad, edition in TEXTS:
        m = analyze_file(fname)
        m.update({"file": fname, "title": title, "tradition": trad, "edition": edition})
        rows.append(m)
        print(f"{title:28s} n={m['sentences']:5d} imp={m['imperative_share']:5.1f}% q={m['question_share']:4.1f}% neg={m['negation_per_1000']:5.1f} obl={m['obligation_per_1000']:4.1f} 2nd={m['second_person_per_1000']:5.1f} 1st={m['first_person_per_1000']:5.1f} self={m['self_words_per_1000']:4.1f} medlen={m['median_sentence_len']}")
    with open(os.path.join(OUT, "metrics.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    json.dump(rows, open(os.path.join(OUT, "analysis_results.json"), "w"), indent=2)
    # validation sample: stratified 60 predicted-imperative + 60 predicted-not
    random.seed(2026)
    pos, neg = [], []
    for fname, title, trad, edition in TEXTS:
        txt = open(os.path.join(CLEAN, fname), encoding="utf-8").read()
        for s in split_sentences(txt):
            (pos if is_imperative(s) else neg).append((title, s))
    random.shuffle(pos); random.shuffle(neg)
    sample = [("imperative", t, s) for t, s in pos[:60]] + [("not", t, s) for t, s in neg[:60]]
    random.shuffle(sample)
    with open(os.path.join(OUT, "validation_sample.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "source", "predicted", "sentence", "label", "notes"])
        for i, (pred, title, s) in enumerate(sample):
            w.writerow([i, title, pred, s.replace("\n", " "), "", ""])
    print(f"\nvalidation sample written: {len(sample)} sentences "
          f"({len(pos)} imperative candidates, {len(neg)} non-imperative in corpus)")

if __name__ == "__main__":
    main()
