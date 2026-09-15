# Patch: condition assignment and source-file selection

Two files replaced: `build_questions.py`, `study_data.py`. Both are in git, so
`git diff` gives you the review. Nothing breaks before you rebuild — the new
`study_data.py` reads the current legacy `questions.json` too.

## What the patch fixes

**The question × condition confound.** The old `build_questions.py` gave the
first ten questions to Direct Empathy and the second ten to Clinical Only, with
`random.seed(42)`, so the assignment was identical for every participant. The
split put the existential questions on one side and the procedural ones on the
other:

| Clinical Only got | Direct Empathy got |
|---|---|
| Kann ich durch die PSMA-Therapie sterben? | Wie lange dauerte eine PSMA-Therapie? |
| Kann ich von meinem Krebs geheilt werden? | Darf ich Besuch erhalten? |
| Wie viel Lebenszeit kann ich hinzugewinnen? | Werden mir die Haare ausfallen? |
| Mein PSA-Wert steigt weiter an. Ist das ein Problem? | Wird mir übel werden? |

Patients rating "verunsichert mich" more often for Clinical Only would be
reacting to the question, not to the answer style — and the effect would point
the way the hypothesis predicts.

**The backend mix.** `get_latest_result_file()` took the newest file per glob.
Direct Empathy resolved to the 13 Aug HuggingFace-Transformers run, Clinical
Only to the 20 Aug LMDeploy run, so the two study conditions came from two
different inference backends. The new script refuses to build such a bundle
unless you pass `--allow-mixed-backend`.

**`--include-twostage` did nothing.** It is wired up now.

## How assignment works now

`questions.json` holds every condition's answer for every question. The
condition each participant sees is decided at runtime in
`study_data.assign_items()`:

    condition(question i) = conditions[(i - 1 + offset_p) mod C]

`offset_p` comes from a SHA-256 of the `user_id` — not Python's `hash()`, which
is salted per process and would reassign a participant after a server restart.
Within a participant the conditions are balanced and every question appears
once; across participants each question appears in every condition about
equally often, so question difficulty becomes a block factor. Presentation
order is shuffled per participant with the same seed.

Simulated over 600 participants, 20 questions × 3 conditions: every
question × condition cell landed between 180 and 216 (perfect balance 200), and
each participant got a 6/7/7 or 7/7/6 split.

## Rebuild

    cd user_study
    python build_questions.py --list-runs                    # see what's there
    python build_questions.py --run 20260813                 # two conditions
    python build_questions.py --run 20260813 --include-twostage   # three

Pinning `--run 20260813` uses the same complete six-condition set the e-poster
rests on, so the patient study and the uncertainty analysis describe the same
model outputs. Without `--run`, the newest file per condition is used and the
backend check will stop you if they disagree.

## Three lines to change in `study_views.py`

The counterbalancing only takes effect after this. Without it the app still
runs, but every participant gets the same assignment as before.

```python
# line 13
from study_data import load_questions
# becomes
from study_data import load_questions, n_questions
```

```python
# in _render_onboarding
num_questions = len(load_questions())
# becomes
num_questions = n_questions()
```

```python
# in _render_demographics
session_state.mock_data = load_questions()
# becomes
session_state.mock_data = load_questions(session_state.user_id)
```

Optionally, in `_record_ratings`, store the machine-readable slug next to the
label so the analysis does not have to parse display strings:

```python
"condition": item.get("_condition", "unknown"),
# becomes
"condition": item.get("_condition", "unknown"),
"condition_key": item.get("condition", "unknown"),
```

## Two things to decide before you run this

**Two conditions or three.** Three lets you test the finding that matters most
from the uncertainty analysis — that the two-stage rewrite is the risky
architecture — but each participant then rates only ~7 items per condition
instead of 10. With two conditions you get more precision on a comparison whose
answer you already partly know.

**Two-stage answers are twice as long.** In the pinned run: clinical-only 113
words on average, direct empathy 152, two-stage 226. If you include two-stage,
length is strongly confounded with condition, and "zu kompliziert geschrieben"
will pick that up. The uncertainty analysis has the same problem — empathy and
length correlate at r = 0.68 — so it is worth deciding whether length is a
nuisance variable to control or part of what you are measuring. Recording it
per item (it is derivable from `answer_text`) at least lets you model it.

## Still open, from the wider review

- The per-item measure is a single forced choice among four statements that mix
  constructs (A = clear *and* reassuring *and* good feeling). It yields a
  four-category distribution rather than empathy and correctness scores. Three
  or four short Likert items per answer would give continuous per-item outcomes
  and a direct parallel to the automated NURSE coverage.
- The pre/post questionnaire measures the effect of reading all items mixed, so
  it cannot be attributed to a condition. Fine as a secondary outcome, worth
  stating explicitly.
- There is no consent step in the app flow (onboarding → demographics → pre →
  evaluation → post → outro). If consent is on paper, note the approval
  reference in the onboarding text; if not, it needs to be in the app before
  any real patient sees it.
- An alternative to hash-based rotation, if you want near-perfect balance: keep
  a participant counter in MongoDB and use `counter % C` as the offset. Worth it
  only if the sample is small enough that random imbalance matters.
