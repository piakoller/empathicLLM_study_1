# Improving the answers before the patient study

Written 15 September 2026, after the EANM poster was submitted. Everything below
is measured on the files in this repository; the commands are given so each
number can be re-checked.

---

## 1. First, a problem that is not about wording

`user_study/questions.json` holds the 20 answers patients will read: 10 in the
*Clinical Only (RAG)* arm, 10 in the *Direct Empathy (RAG)* arm, one answer per
question, monadic.

Those answers were traced back to the runs they came from:

| study arm | source run | generated | inference |
|---|---|---|---|
| Clinical Only (RAG) | `uq_tradeoff_clinical_only_20260820T170637.json` | 20 Aug 2026 | **LMDeploy**, medgemma-27b-it |
| Direct Empathy (RAG) | `uq_tradeoff_direct_empathy_20260813T162303.json` | 13 Aug 2026 | **HuggingFace Transformers, 4-bit** |

All 20 matched verbatim, so the provenance is certain. The two arms were
produced on two different inference stacks, one of them 4-bit quantised, a week
apart, with `n_candidates` 3 and no `max_tokens` cap — while the uniform re-run
of 9/10 September used LMDeploy in both arms, `n_candidates` 5 and
`max_tokens` 2048.

This matters because the patient study asks patients to react to *one* thing:
empathic prompting versus neutral prompting. As the files stand, the two arms
also differ in the numerical precision of the model that wrote them.
Quantisation is known to change fluency and word choice — exactly the surface
properties a patient rates. Any difference the study finds would be open to the
objection that it came from the backend, and there is no way to separate the two
afterwards.

The re-run of 9/10 September was made to remove precisely this problem from the
poster analysis. The study material was not rebuilt with it.

**Recommendation, before anything else: regenerate `questions.json` from one
uniform run.** Not a rewrite of the texts — a regeneration, so that both arms
come from the same server, the same settings and the same day. Everything in
section 3 is worth doing in the same pass.

Reproduce the trace:

```bash
python - <<'PY'
import json, glob, re
q = json.load(open('user_study/questions.json'))
norm = lambda t: re.sub(r'\s+', ' ', t).strip()
for f in sorted(glob.glob('uq_medgemma_benchmark/results/uq_tradeoff_*.json')):
    d = json.load(open(f))
    ans = {norm((r['generation_meta'].get('final_answer') or '').split('VERBAL_CONFIDENCE:')[0])
           for r in d['results']}
    hit = sum(norm(x['answer_text']) in ans for x in q)
    if hit:
        print(f"{hit:3d}/20  {d['metadata']['mode']:<62} {f.split('/')[-1]}")
PY
```

---

## 2. What is wrong with the answers themselves

`screen_patient_answers.py` (next to this file) checks each answer and prints
what a human should look at. On the current study file:

| | Clinical Only | Direct Empathy |
|---|---|---|
| German Flesch (Amstad) | **24.3** | **32.5** |
| below 50 ("mittelschwer") | 10/10 | 10/10 |
| patient not addressed in sentence 1 | 9/10 | 6/10 |
| longer than 150 words | 4/10 | 6/10 |
| more than 15 % of sentences over 20 words | 6/10 | 6/10 |
| unexplained technical terms | 4/10 | 5/10 |
| answer talks about its own sources | 3/10 | 4/10 |
| drug or receptor names | 2/10 | 2/10 |

A German Flesch of 24 is the band academic prose sits in. Patient information is
usually aimed at 60 and above. Both arms are far outside that, and the empathic
arm — the one meant to be gentler — is only eight points better while being 13
words longer.

Four concrete things sit behind those numbers.

**The answer arrives late.** "Werden mir durch die PSMA-Therapie die Haare
ausfallen?" is answered in sentence three; sentences one and two explain PSMA
expression in salivary glands. "Bin ich nach der Entlassung gefährlich für meine
Mitmenschen?" opens with "Nach einer PSMA-Therapie können Sie vorübergehend eine
geringe Menge Radioaktivität ausscheiden" — the reassurance that the dose to
others is very low waits until paragraph three. A frightened reader stops early;
whatever they read first is what they take away. 15 of 20 answers in the
September empathic run open with "Die …", i.e. with the therapy rather than with
the person.

**Jargon is passed through unexplained.** *exprimieren, Xerostomie,
Thrombozytopenie, Leukopenie, prophylaktisch, systemisch, metastasiert,
kastrationsresistent*. The style rules already require a gloss at first use; the
answers do not follow it, because nothing checks.

**The answers talk about their own evidence layer.** "Die bereitgestellten
Dokumente behandeln …", "Die mir vorliegenden Informationen beziehen sich …",
"Studien zeigen …". A patient asked about their treatment, not about the
chatbot's reading material, and this phrasing reads as hedging.

There is a cause for this one in the prompt. `build_direct_empathic_prompt`
forbids "die bereitgestellten Dokumente" and then offers a replacement:

```python
"IMPORTANT: Never use phrases like 'die bereitgestellten Dokumente' or 'laut den Unterlagen'. "
"If referencing evidence, write 'Basierend auf den mir bereitgestellten Informationen...' or speak directly as an expert."
```

The sanctioned alternative is the same move in different words, and it is the
one the model picked. It should be removed, not replaced.

**Substance names the patient cannot act on.** Ondansetron, Granisetron,
Dexamethason, Pilocarpin, 5-HT₃-Antagonisten, Serotoninrezeptoren. The patient
does not choose the antiemetic. "Sie bekommen vor der Behandlung ein Medikament
gegen Übelkeit" carries everything they can use.

---

## 3. What to change in the prompt

Additions to `PATIENT_STYLE_RULES` in `uq/rag/prompts.py`. The existing rules
stay; these are the ones the measured defects call for.

```python
PATIENT_STYLE_RULES_V2_ADDITIONS = (
    "- Answer the question in the FIRST sentence, before any explanation. "
    "If the answer is reassuring, say so first: 'Nein, Ihre Haare fallen davon "
    "nicht aus.' Give the reason afterwards.\n"
    "- Speak to the patient in the first sentence. Do not open with 'Die "
    "PSMA-Radioligandentherapie ...' or with a restatement of the question "
    "('Die Frage nach ...').\n"
    "- Never mention your sources, your documents, the guidelines, the studies "
    "or the information available to you. Say the fact itself.\n"
    "- Do not name drugs, receptors or trial names. Write what the patient will "
    "notice or receive: 'ein Medikament gegen Übelkeit', not 'ein "
    "5-HT3-Antagonist wie Ondansetron'.\n"
    "- At most 120 words.\n"
)
```

Two notes on this.

The first-sentence rule is the one worth having even if nothing else changes.
It costs nothing in content, it is checkable, and it changes what a frightened
reader takes away from the first three seconds.

The 120-word cap replaces the current 150. The empathic arm already averages 145
and reaches 253; a cap only binds if it is below the current mean.

The two-stage architecture already does the first-sentence thing on its own —
in the September run it addresses the patient in sentence 1 in 19 of 20 answers
and never opens with "Die". It is also the longest (181 words on average, up to
262) and has the longest sentences. If a third arm is ever wanted, that is the
trade it brings.

---

## 4. What not to change

**Do not edit the answer texts by hand.** The moment a human rewrites them, the
study measures the human. If a specific answer is unusable, drop that question
from both arms rather than repair it.

**Do not tune the prompt against the NURSE keyword count.** The poster analysis
already showed how tight that coupling is: the "understanding" category is
triggered in all six conditions by the single word *verständlich*, and removing
that one word turns p = 0.003 into p = 0.16. A prompt written to score well on
the keyword list produces answers that sound written to score well. The patient
ratings are the outcome now; the keyword count should not be steering the input.

**Do not add empathy phrases to raise the count either.** The current empathic
answers are not cold because they lack warmth vocabulary. They are cold because
they answer late and explain too much.

---

## 5. Order of work

1. Remove the "Basierend auf den mir bereitgestellten Informationen" escape
   hatch from `build_direct_empathic_prompt`.
2. Add the V2 rules to `PATIENT_STYLE_RULES`.
3. Re-run both arms — same server, same settings, same session.
4. `python screen_patient_answers.py results/<new run>.json` on each, and read
   the three most-flagged answers per arm yourself.
5. Rebuild the study bundle from the new runs:

       cd user_study
       python build_questions.py --list-runs
       python build_questions.py --run <timestamp prefix of the new runs>

   `questions.json` must stay in bundle format — every condition's answer for
   every question. `study_data.assign_items()` picks the condition per
   participant from it; a flat list of pre-assigned items still loads, but it
   silently turns the counterbalancing off and puts question difficulty back on
   top of condition.
6. Screen the rebuilt bundle (`python screen_patient_answers.py questions.json`)
   and keep the report together with `questions_provenance.json`: between them
   they record what patients were shown, from which run, and what was known
   about it beforehand.

Step 4 is the one that catches what a checklist cannot. The script flags; it
does not judge.
