"""Power simulation for the patient study: two vs three arms, 10 answers per participant.

Outcome per answer: participant picks statement A ("informiert mich klar, nimmt mir die
Sorge") or not. Primary contrast: two_stage vs clinical_only. Analysis: logistic
regression with question fixed effects and participant-clustered standard errors.
Assignment: the app's own rule (study_data.assign_items with consecutive slots).
"""
import sys, json, itertools, warnings
import numpy as np, pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, sys.argv[1])  # user_study folder
import study_data as sd

warnings.filterwarnings("ignore")
rng = np.random.default_rng(1)
bundle = sd.load_bundle()
logit = lambda p: np.log(p / (1 - p))

SD_PARTICIPANT, SD_QUESTION, REPS = 1.0, 0.5, 200
P_BASE = 0.30
SCENARIOS = {"+15 pp": {"clinical_only": 0.30, "direct_empathy": 0.375, "two_stage": 0.45},
             "+20 pp": {"clinical_only": 0.30, "direct_empathy": 0.40, "two_stage": 0.50}}
DESIGNS = {"3 arms": ["clinical_only", "direct_empathy", "two_stage"],
           "2 arms": ["clinical_only", "two_stage"]}
NS = [20, 40, 60, 80, 100]

assign = {}
for dname, conds in DESIGNS.items():
    b = {"meta": {**bundle["meta"], "conditions": conds}, "questions": bundle["questions"]}
    assign[dname] = [[(i["question_index"], i["condition"]) for i in sd.assign_items(f"u{s}", b, slot=s)]
                     for s in range(max(NS))]

rows = []
for (sname, probs), (dname, conds), n in itertools.product(SCENARIOS.items(), DESIGNS.items(), NS):
    hits = 0
    for _ in range(REPS):
        u = rng.normal(0, SD_PARTICIPANT, n)
        v = rng.normal(0, SD_QUESTION, 21)
        recs = []
        for p in range(n):
            for q, c in assign[dname][p]:
                eta = logit(probs[c]) + u[p] + v[q]
                recs.append((p, q, c, rng.random() < 1 / (1 + np.exp(-eta))))
        df = pd.DataFrame(recs, columns=["p", "q", "arm", "a"]).astype({"a": int})
        try:
            fit = smf.logit("a ~ C(arm, Treatment('clinical_only')) + C(q)", df).fit(
                disp=0, cov_type="cluster", cov_kwds={"groups": df["p"]})
            term = [t for t in fit.params.index if "two_stage" in t][0]
            hits += fit.pvalues[term] < 0.05 and fit.params[term] > 0
        except Exception:
            pass
    rows.append({"effect": sname, "design": dname, "n": n, "power": hits / REPS})
    print(rows[-1], flush=True)

out = pd.DataFrame(rows).pivot_table(index=["effect", "design"], columns="n", values="power")
print(out.to_string())
json.dump(rows, open(sys.argv[2], "w"), indent=1)
