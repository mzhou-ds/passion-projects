import csv, os
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DATA = os.path.join(PROJ, "data")

# (passage_id, curator label) — hand-verified management-relevant passages
KEEPS = [
 ("analects-0003","I.V","resource-discipline","Rule a country: reverent attention to business, sincerity, economy in expenditure, love for men, employ the people at the proper seasons."),
 ("analects-0015","II.I","lead-by-example","Govern by virtue like the north polar star: keep your place and all the stars turn towards you."),
 ("analects-0017","II.III","culture-over-coercion","If led by laws and punishments, people avoid punishment but have no shame. If led by virtue and propriety, they have shame and become good."),
 ("analects-0032","II.XVII","career-craft","Tsze-chang seeks official emolument: hear much, put aside doubts, speak cautiously, act cautiously -- this is the way to get emolument."),
 ("analects-0033","II.XIX","hire-upright","Advance the upright and set aside the crooked, then the people will submit."),
 ("analects-0034","II.XX","develop-people","Preside with gravity so they reverence you; be filial and kind so they are faithful; advance the good and teach the incompetent so they seek virtue."),
 ("analects-0057","III.XIX","mutual-obligation","A prince should employ his minister according to the rules of propriety; ministers should serve their prince with faithfulness."),
 ("analects-0088","IV.XXIV","communicate-carefully","The superior man is slow in speech and earnest in conduct."),
 ("analects-0104","V.XIV","learn-from-below","Not ashamed to ask and learn of his inferiors -- the mark of the man titled Wan."),
 ("analects-0105","V.XV","manager-scorecard","Four traits of a superior man: humble in conduct, respectful to superiors, kind in nourishing the people, just in ordering them."),
 ("analects-0120","VI.III","comp-fairness","A superior man helps the distressed but does not add to the wealth of the rich."),
 ("analects-0129","VI.XII","hire-autonomy","Has he got good men? Tan-t'ai Mieh-ming never comes to my office except on public business."),
 ("analects-0155","VII.X","hire-planners","When called to office, undertake its duties. For command: not the reckless tiger-fighter, but the man full of solicitude who adjusts his plans then executes."),
 ("analects-0184","VIII.II","care-for-people","When those in high stations perform all duties to relations and do not neglect old friends, the people are aroused to virtue."),
 ("analects-0186","VIII.IV","executive-presence","Three things for the man of high rank: deportment free from violence and heedlessness, countenance near to sincerity, words far from lowness."),
 ("analects-0189","VIII.VII","burden-of-office","The officer may not be without breadth of mind and vigorous endurance. His burden is heavy and his course is long."),
 ("analects-0202","VIII.XX","talent-density","Shun had five ministers, and the empire was well-governed. King Wu: I have ten able ministers."),
 ("analects-0228","IX.XXV","intrinsic-will","The commander of a large state may be carried off, but the will of even a common man cannot be taken from him."),
 ("analects-0273","XI.XXIII","principled-service","A great minister serves his prince according to what is right, and when he finds he cannot, retires. The others are ordinary ministers."),
 ("analects-0274","XI.XXIV","hire-competence","Appointing the unready Tsze-kao as governor: 'You are injuring a man's son.' I hate your glib-tongued people."),
 ("analects-0275","XI.XXV","humility","Tsze-lu boasts he could fix a great state in three years; the Master smiles: management of a State demands the rules of propriety -- his words were not humble."),
 ("analects-0277","XII.II","servant-leadership","Employ the people as if assisting at a great sacrifice; do not do to others what you would not wish done to yourself."),
 ("analects-0282","XII.VII","trust-foundation","Requisites of government: sufficiency of food, sufficiency of military equipment, confidence of the people. Without the people's faith there is no standing for the state."),
 ("analects-0284","XII.IX","shared-prosperity","If the people have plenty, their prince will not be left to want alone. If the people are in want, the prince cannot enjoy plenty alone."),
 ("analects-0286","XII.XI","role-clarity","There is government when the prince is prince and the minister is minister; when the father is father and the son is son."),
 ("analects-0288","XII.XIII","conflict-resolution","In hearing litigations I am like any other; what is necessary is to cause the people to have no litigations."),
 ("analects-0289","XII.XIV","consistency","The art of governing: keep its affairs before the mind without weariness, and practise them with undeviating consistency."),
 ("analects-0291","XII.XVI","strengths-coaching","The superior man seeks to perfect the admirable qualities of men, not their bad qualities."),
 ("analects-0292","XII.XVII","rectify","To govern means to rectify. If you lead the people with correctness, who will dare not be correct?"),
 ("analects-0293","XII.XVIII","culture-top-down","If you, sir, were not covetous, although you should reward them to do it, they would not steal."),
 ("analects-0294","XII.XIX","culture-wind-grass","Why use killing? Let your evinced desires be for what is good and the people will be good. Superiors and inferiors are like wind and grass."),
 ("analects-0297","XII.XXII","hire-upright","Employ the upright and put aside the crooked; in this way the crooked can be made upright."),
 ("analects-0301","XIII.II","hire-talent","Employ first the services of your officers, pardon small faults, and raise to office men of virtue and talents."),
 ("analects-0302","XIII.III","clarity-cascade","Rectify names: if names are incorrect, language is wrong, affairs fail, proprieties and music do not flourish, punishments are misawarded."),
 ("analects-0305","XIII.VI","lead-by-example","When a prince's personal conduct is correct, his government is effective without issuing orders. If not correct, orders will not be followed."),
 ("analects-0308","XIII.IX","sequence","The people are numerous -- enrich them. When enriched, what more? Teach them."),
 ("analects-0312","XIII.XIII","self-mastery","If a minister make his own conduct correct, what difficulty in assisting government? If he cannot rectify himself, what has he to do with rectifying others?"),
 ("analects-0314","XIII.XV","dissent","No pleasure in being a prince but that no one can oppose what I say: if his words are not good and no one opposes them, ruin follows from this one sentence."),
 ("analects-0315","XIII.XVI","attract-talent","Good government obtains when those who are near are made happy and those who are far off are attracted."),
 ("analects-0316","XIII.XVII","patience","Do not be desirous to have things done quickly; do not look at small advantages. Haste prevents thoroughness; small advantages block great affairs."),
 ("analects-0319","XIII.XX","accountability","The officer: in conduct maintains a sense of shame, and when sent on commission does not disgrace his prince's commission."),
 ("analects-0323","XIII.XXIV","calibration","Not all approval or hatred is earned; best when the good in the neighborhood love him and the bad hate him."),
 ("analects-0324","XIII.XXV","role-fit","The superior man is easy to serve, difficult to please; in employing men, he uses them according to their capacity."),
 ("analects-0328","XIII.XXIX","train-first","Let a good man teach the people seven years, and they may then likewise be employed in war."),
 ("analects-0329","XIII.XXX","onboarding","To lead an uninstructed people to war is to throw them away."),
 ("analects-0330","XIV.I","intrinsic-motivation","When good government prevails, to think only of salary is shameful; when bad government prevails, to think only of salary is shameful."),
 ("analects-0341","XIV.VIII","tough-love","Can there be love which does not lead to strictness? Can there be loyalty which does not lead to instruction?"),
 ("analects-0352","XIV.XXIII","candor-up","How should a ruler be served? Do not impose on him, and moreover withstand him to his face."),
 ("analects-0372","XIV.XLIV","ease-of-leading","When rulers love to observe the rules of propriety, the people respond readily to the calls on them for service."),
 ("analects-0373","XIV.XLV","servant-leadership","He cultivates himself so as to give rest to others; so as to give rest to all the people -- even Yao and Shun were solicitous about this."),
 ("analects-0397","XV.XXII","substance-over-signal","The superior man does not promote a man for his words, nor put aside good words because of the man."),
 ("analects-0398","XV.XXIII","reciprocity","Is there one word as a rule of practice for life? Reciprocity: what you do not want done to yourself, do not do to others."),
 ("analects-0407","XV.XXXII","leadership-stack","Knowledge to attain, virtue to hold, dignity so the people respect him, propriety in moving the people -- else full excellence is not reached."),
 ("analects-0412","XV.XXXVII","duty-over-pay","A minister in serving his prince reverently discharges his duties and makes his emolument a secondary consideration."),
 ("analects-0417","XVI.I","culture-retention","Rulers are not troubled lest people be few but lest they not keep their places; not poverty but want of contented repose. Attract the remote with civil culture and virtue; make them contented and tranquil."),
 ("analects-0426","XVI.X","manager-checklist","Nine considerations: see clearly, hear distinctly, benign countenance, respectful demeanor, sincere speech, reverent business, question doubts, anger thinks of difficulties, gain thinks of righteousness."),
 ("analects-0428","XVI.XII","legacy","Duke Ching had a thousand teams of horses, yet on his death the people praised him for not a single virtue. Po-i and Shu-ch'i starved, and the people praise them still."),
 ("analects-0436","XVII.VI","virtue-five","Five things of perfect virtue: gravity, generosity of soul, sincerity, earnestness, kindness. If kind, this enables you to employ the services of others."),
 ("analects-0458","XVIII.II","integrity","Serving men upright, where shall I go and not be thrice dismissed? Serving crooked, why leave home at all?"),
 ("analects-0466","XVIII.X","role-fit","The virtuous prince does not neglect relations, does not let great ministers repine at not being employed, does not dismiss old families without cause, does not seek in one man talents for every employment."),
 ("analects-0477","XIX.X","trust-before-labor","The superior man, having obtained the people's confidence, may then impose labours on them; having the prince's confidence, may then remonstrate."),
 ("analects-0480","XIX.XIII","learning-culture","The officer, having discharged his duties, should devote his leisure to learning. The student, having completed his learning, should apply himself to be an officer."),
 ("analects-0486","XIX.XIX","blameless-culture","Rulers have failed and the people are disorganised. When you find the truth of an accusation, grieve for and pity them; do not feel joy at your own ability."),
 ("analects-0493","XX.I","grand-summary","Chau: by generosity won all; by sincerity made them trust; by earnest activity achieved greatly; by justice all were delighted. Attended to weights and measures, restored discarded officers, called the retired into office."),
 ("analects-0494","XX.II","management-playbook","Five excellent: beneficent without great expenditure; lays tasks without repining; pursues desires without covetousness; dignified ease without pride; majestic without fierceness. Four bad: death without instruction is cruelty; sudden work demands are oppression; lax orders then severity is injury; stingy rewards is acting a mere official."),
]

rows = {r["passage_id"]: r for r in csv.DictReader(open(os.path.join(DATA, "all_passages.tsv")), delimiter="\t")}
missing = [pid for pid, _, _, _ in KEEPS if pid not in rows]
assert not missing, missing

with open(os.path.join(DATA, "leadership.tsv"), "w") as f:
    f.write("passage_id\tbook\tchap\ttheme\tlabel\ttext\n")
    for pid, chap, theme, label in KEEPS:
        r = rows[pid]
        f.write("%s\t%s\t%s\t%s\t%s\t%s\n" % (pid, r["book"], chap, theme, label, r["text"].replace("\t", " ")))
print("kept:", len(KEEPS))
