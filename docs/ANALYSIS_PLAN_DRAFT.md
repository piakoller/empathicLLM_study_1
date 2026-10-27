# Draft: analysis plan and sample size (27 Oct 2026)

For the meeting of 28 Oct. Assumes the current app: one answer at a time, a choice of
statements A–D, 10 of the 20 questions per participant. If the rating format changes
(A vs. B comparison, or short scales), the outcome and the power figures change with it.

## Design

- Within-subject. Each participant rates 10 answers to 10 different questions, in random
  order. With three arms the split per person is 4/3/3; with two arms 5/5.
- Patients and clinicians take part and are analysed separately. A running count per role
  decides which 10 questions someone gets, so every question is rated equally often and
  appears in every arm equally often (`study_data.assign_items`).
- All arms come from the same model, server and settings (runs of 27 Oct 2026); readability
  and length are similar across arms (Flesch 40–42, 59–83 words).

## Outcomes

**Primary (patients):** per answer, whether the participant picks statement A
("Die Antwort informiert mich klar, nimmt mir die Sorge und gibt mir ein gutes Gefühl").

**Primary hypothesis:** patients pick A more often for Two-Stage answers than for
Clinical Only answers.

**Secondary**

- Two-Stage vs. Direct Empathy (same outcome).
- Distribution of all four statements per arm; in particular C (too complicated) and
  D (unsettling) as a burden signal.
- Clinicians: A ("medizinisch korrekt, empathisch und hervorragend geeignet") per arm, and
  D ("medizinisch bedenklich …") per arm as a safety signal.
- Patients: change in the pre/post mood items (calm, tense, uneasy, overwhelmed, confident).
  Exploratory only: each person reads all arms, so a change cannot be attributed to one arm.
- Reading time per answer (`response_time_s`).
- Manipulation check, from the texts: words and Flesch score per arm.

## Analysis

- Primary model: mixed-effects logistic regression,
  `A ~ arm + (1 | participant) + (1 | question)`, Clinical Only as reference
  (R `lme4::glmer`, or Python `statsmodels` / `pymer4`).
- Two contrasts (Two-Stage vs. Clinical Only, Two-Stage vs. Direct Empathy), Holm-corrected,
  α = 0.05 two-sided. Report odds ratios and the model-based proportions of A per arm with
  95 % confidence intervals.
- Sensitivity analysis: logistic regression with question as a fixed effect and
  participant-clustered standard errors (the model used in the simulation below).
- All rated answers enter the analysis, including those of participants who stop early;
  the mixed model handles unequal numbers of answers per person.
- Questions dropped at the medical sign-off are removed from all arms before the analysis.

## Sample size (simulation)

Assumptions: Clinical Only gets A in 30 % of answers; Two-Stage 15 or 20 percentage points
more (Direct Empathy halfway); variation between participants SD 1.0 and between questions
SD 0.5 on the logit scale; 10 answers per person, assigned exactly as in the app; 200
simulated studies per cell. The false-positive rate of the test was 5.0–5.5 % under no effect.

Power for the primary contrast (Two-Stage vs. Clinical Only), patients:

| Effect | Design | n = 20 | 40 | 60 | 80 | 100 |
| --- | --- | --- | --- | --- | --- | --- |
| +15 pp | 2 arms | 48 % | 79 % | 94 % | 97 % | 100 % |
| +15 pp | 3 arms | 36 % | 63 % | 78 % | 87 % | 96 % |
| +20 pp | 2 arms | 72 % | 95 % | 99 % | 100 % | 100 % |
| +20 pp | 3 arms | 55 % | 85 % | 98 % | 100 % | 100 % |

Reading:

- With the 40 patients named in the KEK description, **two arms** reach about 80 % power
  for a 15-point difference; **three arms** need about **60–70 patients** for the same.
- Three arms give the comparison with Direct Empathy, at the cost of fewer answers per arm
  and person (3–4 instead of 5).
- The assumptions (30 % baseline, size of the participant and question variation) are
  guesses; the pilot gives first estimates. Rerun with
  `python analysis/power_sim.py . out.json` from the `user_study` folder after changing
  the assumptions at the top of the script.
- Clinicians: the same table applies for the same effect; 40 clinicians give the precision
  of the 40-patient row.

## Open for the meeting

1. Two or three arms (decision 2), given the table above.
2. Rating format (decision 3). A vs. B comparison would need its own power calculation.
3. Realistic recruitment: how many PSMA patients per month can be asked at Insel?
