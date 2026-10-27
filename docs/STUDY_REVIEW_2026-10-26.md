# empathicLLM patient study: readiness review (26 Oct 2026)

Reviewed: `user_study/` (app, questions.json bundle, questionnaire, docs) and `uq_medgemma_benchmark/` (prompts, current runs, derived evals).

## Bottom line

The study is feasible and the core design makes sense: within-subject, counterbalanced per participant, one model and backend for both arms, provenance recorded. **It is not ready for patients yet.** Three things block it:

1. Several answers contain factual errors or contradictions. Real PSMA patients could act on them.
2. The prompt fixes written up on 10 and 15 September were never applied. `prompts.py` has no `PATIENT_STYLE_RULES`, and the "Basierend auf den mir bereitgestellten Informationen" escape hatch is still there twice. The current bundle is the unfixed 9 September run: Flesch 26 / 32, and the answer is missing from sentence 1 in 18/20 and 15/20 answers.
3. Ethics, consent and data hosting are still open.

A rerun is warranted. It also lets you fix a design confound (point B1).

---

## A. Blockers

### A1. Factual errors and contradictions in the current answers

| Q | Arm | Problem |
|---|---|---|
| 20 Dauer | empathy | "Ein Zyklus besteht aus zwei Injektionen im Abstand von etwa vier Wochen". This is wrong: the regimen is one injection every 6 weeks, up to 6 cycles. |
| 20 Dauer | clinical | Does not answer the question. Gives ADT duration "24–36 Monate", which a patient will read as the duration of the PSMA therapy. |
| 17 Dosis | empathy | "keine Standarddosis", "MBq/kg". Pluvicto is a fixed activity (7.4 GBq) and is not weight-based. |
| 17 Dosis | clinical | Drifts to antiemetics and xerostomia. Does not answer. |
| 15 nach draussen | empathy | "mindestens 12 Stunden im Krankenhaus … bevor Sie entlassen werden" contradicts the 20 h stated in Q9 and Q18. 12 h is the visiting threshold. |
| 4 Entlassung | clinical | "während der ersten 20 Stunden … allein zu schlafen" contradicts Q14 (two weeks). |
| 4 / 14 | both | "Abstand zu Ihren Angehörigen und deren Arbeitskollegen" is garbled from the source. |
| 10, 13, 15 | both | I-131 rules (48 h) are presented as an alternative within PSMA therapy. Irrelevant and confusing. |
| 1 Heilung | empathy | "vollständige Heilung … nicht immer erreichbar" implies a cure is sometimes possible. In mCRPC this gives false hope. |
| 5 Wirkung | both | Mostly about PET sensitivity and antiemetics. The empathy arm misattributes "ca. 25 %". Neither answers the question. |
| 12 Lebenszeit | clinical | Discusses curative-therapy eligibility (10–15 years of life expectancy). Irrelevant and alarming. |
| 2 Strahlung | empathy | "Risiko … gering im Vergleich zu anderen Krebsarten" is meaningless. |
| 11, 12, 19 | empathy | "Gerne können wir … gemeinsam durchgehen" promises a follow-up conversation the system cannot have. |
| many | both | Refers patients to the "Radioonkologe". At Insel the treating discipline is nuclear medicine. |
| many | both | "Die bereitgestellten Dokumente / mir vorliegenden Informationen" (clinical 8/20, empathy 7/20). |

Root causes:

- **Retrieval.** PET-imaging and I-131 chunks are pulled for therapy questions.
- **Corpus.** The corpus has no patient-level PSMA therapy leaflet: nothing on schedule or cycles, and nothing on the local discharge rules.
- **Prompts.** The prompts still allow source references.

### A2. Ethics, consent, data

- There is no consent step and no approval reference in the app. The mood items ("Sorgen um meine Gesundheit") and demographics are health-related data. Clarify with KEK Bern (BASEC jurisdictional inquiry) whether the Human Research Act applies, before the first patient.
- Data goes to MongoDB. Confirm where the cluster is hosted. Atlas or any foreign cloud may not be acceptable for Insel patient data under Insel policy and the nDSG. If in doubt, use REDCap or an Insel-hosted DB.
- Patients currently in therapy will read texts that may be wrong. Add three things:
  - a clear statement that the texts may contain errors
  - a debrief sheet that corrects anything known to be wrong
  - a contact person for questions that come up while reading

### A3. Medical sign-off gate

After the rerun, have two nuclear medicine physicians rate every answer as correct / minor issue / potentially harmful. Drop a question from **both** arms if either arm is harmful. Do not hand-edit the texts.

---

## B. Design improvements

**B1. Confound: the empathy arm also differs in readability and length.** At present the arms differ in empathy, length (+20 %), Flesch (+6) and source-talk. A patient preference cannot be attributed to empathy. Apply the same patient style rules (readability, first-sentence answer, length cap, no drug names, no source-talk) to **both** prompts. Then the contrast is empathy alone. Report word count and Flesch per arm as manipulation checks.

**B2. Outcome measure.** The single forced choice among A–D has three problems:

- The statements mix several constructs.
- Option A ("nimmt mir die Sorge") rewards reassurance even when an honest answer should not reassure (Q8 "Kann ich sterben?").
- The coloured markers (green to red) prime a valence.

Replace it with 3–4 short 5-point items per answer, for example:

- "Ich habe die Antwort gut verstanden."
- "Die Antwort geht einfühlsam auf meine Sorgen ein."
- "Ich vertraue dieser Antwort."
- "Nach dem Lesen fühle ich mich … (deutlich beunruhigter … deutlich beruhigter)"

Remove the emoji colours. Add a "Weiter" confirmation instead of auto-advancing on the first click.

**B3. Question set.** Several questions are near-duplicates:

- Q9 / Q18 (length of stay)
- Q10 / Q13 (visits)
- Q4 / Q14 / Q15 (precautions)

Typos: Q12 "Therpie", Q20 "dauerte". Reduce to about 12 distinct questions (6 per arm). This also addresses the next point.

**B4. Burden.** The onboarding says "5–7 Minuten". 20 answers at about 145 words each, read by older patients, plus the questionnaires, is realistically **25–35 min**. Either cut to about 12 answers or state the real time.

**B5. Questionnaires.**

- The pre-questionnaire asks about "PRRT, SIRT", which are wrong therapies for this population. Use "PSMA-Therapie".
- The post-questionnaire drops `worried` and `relaxed`, so pre/post is incomplete.
- Use a validated short state-anxiety scale (e.g. STAI-SKD / STAI-6, German) rather than ad-hoc items, with identical items pre and post.
- `docs/README_questionnaire.md` (22 post items) is out of sync with the JSON (13).
- Post items refer to "das System" across both arms. Report them as secondary outcomes only.

**B6. Covariates worth one screen.** Treatment status (before / during / after PSMA therapy, which cycle), education, and a one-item health-literacy screener (e.g. Chew SILS-1).

**B7. App.**

- The outro shows the raw JSON ("Erhobene Daten") to patients. Remove it.
- Role is self-selected by patients. Use separate links instead (`?role=arzt`).
- A refresh creates a new participant. Read the participant ID from `st.query_params` or from a paper code.
- Python ≥3.12 is still undeclared.

**B8. Sample size.** For a paired comparison of per-participant mean ratings, d = 0.5 at 80 % power and α = .05 needs about 34 completers. Analyse with a mixed model (participant and question as random effects). Check this against realistic Insel PSMA patient throughput before fixing the timeline.

---

## C. Rerun plan

1. **Corpus.** Add Insel's own patient information leaflet for Lu-PSMA (cycles, inpatient stay, discharge rules). Exclude or deprioritise I-131 sections and PET-diagnostics chunks for therapy questions. Spot-check the top-k retrieval for every question.
2. **Prompts.** Add a shared `PATIENT_STYLE_RULES` to both arms:
   - answer in sentence 1
   - ≤120 words
   - ≤15 words per sentence
   - gloss or omit technical terms
   - no drug, receptor or trial names
   - never mention sources, documents or information
   - no offers of follow-up conversation
   - "Ihr Behandlungsteam der Nuklearmedizin" instead of "Radioonkologe"
   - Swiss spelling (ss)

   Remove both "Basierend auf den mir bereitgestellten Informationen" lines. Empathy arm: NURSE instructions only, and avoid the stock "Es ist verständlich" opener.
3. **Candidate selection.** You already generate 5 candidates. Select the first one that passes `screen_patient_answers.py` hard checks (source-talk, length, drug names, sentence 1) rather than always the top candidate.
4. **Run both arms** in one session, same server and settings, then run `check_runs.py`.
5. **Rebuild the bundle** with `build_questions.py`, screen it, then apply the physician sign-off gate (A3).
6. **Pilot** with 3–5 patients (think-aloud, timing) before the main run.
