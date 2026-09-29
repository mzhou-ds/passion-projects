"""Hand-adjudicated verdicts: for each modern statement, the best Confucian match,
judged by a human who read the full 66-passage corpus. verdict in
{strong, moderate, weak, absent}."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)

# (modern_id, verdict, [(passage_id, note)])
V = [
 ("oxy1","moderate",[("analects-0341","XIV.VIII: love that does not lead to strictness, loyalty that does not lead to instruction -- coaching as a duty of care")]),
 ("oxy2","strong",[("analects-0324","XIII.XXV: employ men according to their capacity -- role-fit delegation"),("analects-0129","VI.XII: Tan-t'ai never comes to the office except on public business -- the empowered employee who needs no check-ins")]),
 ("oxy3","moderate",[("analects-0184","VIII.II: those in high stations perform all duties to relations; the people are aroused to virtue"),("analects-0436","XVII.VI: kindness enables you to employ the services of others")]),
 ("oxy4","weak",[("analects-0494","XX.II: beneficent without great expenditure; lays tasks without repining -- efficient execution, but no roadblock/prioritization idiom")]),
 ("oxy5","strong",[("analects-0314","XIII.XV: if a ruler's words are not good and no one opposes them, ruin follows -- dissent as a duty"),("analects-0352","XIV.XXIII: do not impose on him, and withstand him to his face -- candor upward")]),
 ("oxy6","strong",[("analects-0034","II.XX: advance the good and teach the incompetent"),("analects-0308","XIII.IX: enrich them, then teach them -- development as a sequence"),("analects-0301","XIII.II: raise to office men of virtue and talents -- advancement")]),
 ("oxy7","moderate",[("analects-0286","XII.XI: prince is prince, minister is minister -- everyone knows their role"),("analects-0302","XIII.III: rectify names, or affairs cannot be carried to success -- clarity cascade")]),
 ("oxy8","strong",[("analects-0209","IX.VI: 'Must the superior man have such variety of ability? He does not need variety of ability.' -- both Google's data and Confucius rank technical skill LAST")]),
 ("q01","moderate",[("analects-0286","XII.XI: role clarity"),("analects-0302","XIII.III: clarity cascade")]),
 ("q02","absent",[]),
 ("q03","strong",[("analects-0324","XIII.XXV: uses men according to their capacity"),("analects-0466","XVIII.X: does not seek in one man talents for every employment")]),
 ("q04","absent",[]),
 ("q05","moderate",[("analects-0184","VIII.II: duties to relations; the people aroused to virtue"),("analects-0003","I.V: love for men as a requisite of rule")]),
 ("q06","strong",[("analects-0034","II.XX: advance the good and teach the incompetent"),("analects-0308","XIII.IX: teach them")]),
 ("q07","moderate",[("analects-0314","XIII.XV: the ruler must tolerate opposition"),("analects-0352","XIV.XXIII: withstand him to his face")]),
 ("q08","weak",[("analects-0412","XV.XXXVII: makes his emolument a secondary consideration -- duty over pay, but no mission narrative")]),
 ("q09","weak",[("analects-0184","VIII.II: the people aroused to virtue -- peer culture only by implication")]),
 ("q10","absent",[]),
 ("q11","absent",[]),
 ("q12","strong",[("analects-0328","XIII.XXIX: teach the people seven years"),("analects-0480","XIX.XIII: the officer devotes his leisure to learning")]),
]

UNREDISCOVERED = [
 ("analects-0494","XX.II","The 2,500-year-old toxic-manager taxonomy","Four bad things: putting people to death without instructing them (cruelty); demanding the full tale of work suddenly without warning (oppression); issuing lax orders then insisting with severity (injury); stingy rewards (acting the part of a mere official)."),
 ("analects-0294","XII.XIX","Wind and grass: the mechanism of culture","Let your evinced desires be for what is good, and the people will be good. Superiors and inferiors are like wind and grass -- the grass bends where the wind blows. Culture follows what the leader visibly wants, not what the handbook says."),
 ("analects-0323","XIII.XXIV","Adversarial calibration","Do not trust universal approval or universal hatred. The read that matters: the good in the neighborhood love him, and the bad hate him. Approval from the wrong people is a contra-indicator."),
 ("analects-0330","XIV.I","Salary-shame as a selection filter","When good government prevails, to be thinking only of salary is shameful. Intrinsic motivation used not as engagement fluff but as a criterion for who should hold office."),
 ("analects-0417","XVI.I","Retention through contented repose","Rulers are not troubled lest their people be few, but lest they not keep their several places. Attract the remote with civil culture and virtue, and make them contented and tranquil. Retention as an outcome of fit and ease, not perks."),
]

json.dump({"verdicts": [{"id": i, "verdict": v,
        "passages": [{"passage_id": p, "note": n} for p, n in ps]} for i, v, ps in V],
           "unrediscovered": [{"passage_id": p, "book": b, "title": t, "note": n}
                              for p, b, t, n in UNREDISCOVERED]},
          open(os.path.join(PROJ, "data", "adjudication.json"), "w"), indent=1)
print("adjudication written")
