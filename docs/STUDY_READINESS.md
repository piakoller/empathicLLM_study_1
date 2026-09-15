# Readiness check, 15 September 2026

The app was run end to end in a container with Streamlit's own test harness
(`streamlit.testing.v1.AppTest`), one simulated participant per role, every
click driven through the real widgets. What follows separates what was
verified from what is still open.

**Verdict: the software runs. Three things should be settled before the first
patient, one of which is not a software question.**

---

## 1. No consent step

The flow is onboarding → demographics → pre-questionnaire → 20 ratings →
post-questionnaire → outro. Nothing asks for consent, and the onboarding text
carries no ethics approval reference.

If consent is collected on paper, the approval reference belongs in the
onboarding screen so the app and the paper record match. If it is not, it needs
to be in the app before any patient sees it. This is the one item on this list
that a code fix cannot close.

## 2. A crash on any machine without `secrets.toml` — fixed

`st.secrets.get("MONGODB_URI")` does not return `None` when there is no
`secrets.toml`; it raises `StreamlitSecretNotFoundError`. That took down the
whole save path — the `os.environ` lookup and the local-file fallback below it
never ran. The failure lands right after the demographics page, on the first
save, before a single rating is collected.

On this laptop the file exists, so it never showed. It is gitignored, so a
clone or a fresh server is exactly the case that breaks.

Fixed in `study_persistence.py` (`_mongo_uri()`, wrapped in try/except).
Verified in three separate processes:

| state | before | after |
|---|---|---|
| `secrets.toml` present | works | works, same value |
| no file, no env var | **raises** | falls back to `fallback_results.json` |
| no file, `MONGODB_URI` set | **raises** | uses the env var |

A full 20-item session was then run with no `secrets.toml` at all: it completed
and the record landed in `fallback_results.json`.

## 3. Python 3.12 or newer is required, and nothing says so

`questionnaire_views.py`, line 182:

    parts = [f"{v} = {lbl.split('–', 1)[-1].strip()}" for v, lbl in …]

A backslash inside an f-string expression is a **SyntaxError before Python
3.12** (allowed from 3.12 by PEP 701). The app does not start on 3.11 — it
fails at import, before any page renders.

This laptop runs 3.13, so it works here. `requirements.txt` pins three packages
and no Python version, and several hosts still default to 3.11. Either add

    python_requires / runtime.txt:  python-3.12

or rewrite that one line so it runs anywhere:

    sep, nbsp = "–", " "
    parts = [f"{v}{nbsp}={nbsp}{lbl.split(sep, 1)[-1].strip()}" for v, lbl in …]

---

## What was verified as working

A complete session, for both roles, driven through the real widgets:

| check | patient | physician |
|---|---|---|
| flow reaches the outro | yes | yes |
| ratings recorded | 20 | 20 |
| distinct questions | 20 | 20 |
| condition split | 10 / 10 | 10 / 10 |
| pre-questionnaire items | 10 | 3 |
| post-questionnaire items | 13 | 7 |
| response time per item | 20/20 | 20/20 |
| payload `status` | completed | completed |

The differing questionnaire counts are by design: `_PATIENT_ONLY_KEYS` filters
the mood items out for physicians.

Also checked:

- **Counterbalancing is live.** `questions.json` is in bundle format, so
  `study_data.assign_items()` decides the condition per participant. Simulated
  over 600 participants: every participant 10/10, each question appearing in
  both conditions across the sample (cells 279–321, even split 300).
- **Answer text is safe to render.** All 40 answers were scanned for
  Markdown-active characters (`#`, `*`, `-`, `_`, backticks, pipes, raw HTML) —
  none present, so `st.markdown(answer_text)` cannot mangle them. No answer is
  empty, none carries a `VERBAL_CONFIDENCE` tag, the longest is 1799 characters.
- **Provenance is recorded.** Both arms come from the LMDeploy run of
  9 September; `questions_provenance.json` holds the full metadata.

## What could not be verified here, and is yours to do

**The live MongoDB connection.** The test used a placeholder URI on purpose, so
as not to touch your credentials. Do one complete run yourself and confirm a
document with `status: "completed"` appears in `empathicLLM_study.study_1`.
Until that is seen once, the database path is untested.

## Two things to expect during data collection

**A page refresh creates a new participant.** `user_id` is a fresh UUID per
browser session, so F5 mid-study starts the participant over and leaves a
partial record behind under a different id. With patients on tablets this will
happen. Nothing in the code prevents it; filter on `status == "completed"` in
the analysis, and expect the participant count to exceed the completed count.

**The answers are still hard to read.** German Flesch 24 (clinical) and 32
(empathic) against about 60 for patient information; in 16 of 20 answers the
answer to the question is not in the first sentence. That is what patients will
be rating. It is not a blocker — it is the object of study — but
`docs/PATIENT_ANSWERS_BEFORE_STUDY.md` describes what a re-run would change,
and this is the last moment at which that decision is free.
