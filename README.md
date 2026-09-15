# user_study — Phase-I patient study

A Streamlit app. Patients read model-generated answers to questions about PSMA
radioligand therapy and rate them, with a short questionnaire before and after.

    pip install -r requirements.txt
    streamlit run app.py

## How an answer gets in front of a patient

    uq_medgemma_benchmark/results/current/*.json      the benchmark runs
              │
              │  build_questions.py --run <prefix>
              ▼
    questions.json          every condition's answer for every question ("bundle")
    questions_provenance.json   which run each arm came from, and its metadata
              │
              │  study_data.assign_items(user_id)      decided per participant
              ▼
    app.py → study_views.py → study_persistence.py → MongoDB (fallback: local file)

**The bundle format matters.** `questions.json` holds *all* conditions per
question; the condition a given participant sees is decided at runtime from a
SHA-256 of their `user_id`:

    condition(question i) = conditions[(i - 1 + offset_p) mod C]

Within a participant the conditions are balanced and every question appears
once; across participants each question appears in every condition about
equally often, so question difficulty is a block factor instead of a confound.
`study_data.load_bundle()` still accepts a flat list of pre-assigned items, but
then there is only one answer per question and the counterbalancing silently
does nothing. If you ever hand-edit `questions.json`, keep the bundle shape.

## Files

| file | role |
|---|---|
| `app.py` | entry point; session state, CSS, save-on-change |
| `study_views.py` | onboarding, demographics, the rating pages, outro |
| `study_data.py` | loads the bundle, assigns conditions per participant |
| `study_persistence.py` | MongoDB, with a local `fallback_results.json` |
| `questionnaire.py` / `_views.py` / `_data.py` | pre- and post-questionnaire |
| `questionnaire_questions.json` | the questionnaire items |
| `questions.json` | the study bundle — built, not hand-written |
| `questions_provenance.json` | provenance of the bundle; keep with the study records |
| `build_questions.py` | builds the bundle from the benchmark runs |
| `screen_patient_answers.py` | flags answers that a patient will stumble over |
| `cleanup_user_study.py` | parks dead weight in `_attic/`; dry run by default |
| `styles.css`, `scroll_component/` | presentation |

## Before a run

    python build_questions.py --list-runs          # see what exists
    python build_questions.py --run 20260909       # both arms from one run
    python screen_patient_answers.py questions.json

`build_questions.py` refuses to build if the arms come from different inference
setups. That check exists because the study file used until 15 September 2026
had its Clinical Only answers from a LMDeploy run and its Direct Empathy
answers from a 4-bit HuggingFace run a week earlier — patients would have been
comparing the backend as much as the prompting strategy.

`screen_patient_answers.py` flags; it does not judge. Read the most-flagged
answers yourself before a study run.

## Documents

- `docs/README_questionnaire.md` — the questionnaire items and the Likert scale
- `docs/PATCH_NOTES.md` — why condition assignment moved into `study_data.py`
- `docs/PATIENT_ANSWERS_BEFORE_STUDY.md` — what is wrong with the generated
  answers and what to change in the prompt before the next run

## `_attic/`

Files that are no longer used but are not thrown away: superseded study files,
duplicates of data that lives in the benchmark repository, scratch drafts. Each
was parked with a stated reason — run `python cleanup_user_study.py` to see the
reasons again.

## Open, not decided

- There is no consent step in the app flow (onboarding → demographics → pre →
  evaluation → post → outro). If consent is on paper, the approval reference
  belongs in the onboarding text.
- The per-item measure is one forced choice among four statements that each mix
  several constructs, so it yields a four-category distribution rather than
  separate empathy and correctness scores.
- The pre/post questionnaire spans all items mixed together, so its change
  cannot be attributed to a condition. Fine as a secondary outcome, worth
  saying so explicitly.
