"""Data loading and per-participant condition assignment for the Phase-I study.

The condition a participant sees for each question is decided here, not in
questions.json, so that condition is crossed with question across the sample
instead of being fixed to a subset of questions.

Assignment rule
---------------
Each participant sees K = QUESTIONS_PER_PARTICIPANT of the N questions (all of
them if N <= K). With questions indexed 0..N-1 and C conditions, participant
number s (the slot) gets the K questions

    start, start + 1, ..., start + K - 1   (mod N),   start = s mod N

and the question at position j of that window gets

    conditions[(j + rotation) mod C],   rotation = (s div N) mod C

Three properties follow:

  * within a participant, every chosen question is seen once and the conditions
    are balanced (K/C each, ±1);
  * every N consecutive slots use every start once, and every question lies in
    exactly K of the N windows, so each question is rated equally often (K/N of
    the participants each);
  * every N*C consecutive slots put each question in every condition equally
    often, so question difficulty is a block factor rather than a confound.

The slot is the number of earlier participants of the same role
(study_persistence.participant_count), so patients and clinicians are balanced
separately. Without a database the slot falls back to a hash of the user_id;
the balance then holds only in expectation (with 40 participants a question
gets 20 ratings, give or take 3).

Presentation order is shuffled per participant with a seed from the user_id, so
serial position does not stay tied to a particular item.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import random

_BASE_DIR = pathlib.Path(__file__).parent
_QUESTIONS_PATH = _BASE_DIR / "questions.json"

CONDITION_LABELS = {
    "clinical_only": "Clinical Only (RAG)",
    "direct_empathy": "Direct Empathy (RAG)",
    "two_stage": "Two Stage (RAG)",
}

# At most this many answers per participant (about 15 minutes; KEK clarification: 10).
QUESTIONS_PER_PARTICIPANT = 10


def _stable_offset(user_id: str) -> int:
    """Deterministic non-negative int from a user id.

    Python's hash() is salted per process, so it cannot be used: the same
    participant would get a different assignment on a server restart.
    """
    digest = hashlib.sha256(str(user_id).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def load_bundle() -> dict:
    """Load questions.json, accepting both the bundle format and the old flat list."""
    if not _QUESTIONS_PATH.exists():
        raise FileNotFoundError(
            f"Missing {_QUESTIONS_PATH}. Run 'python build_questions.py' first."
        )
    data = json.loads(_QUESTIONS_PATH.read_text(encoding="utf-8"))

    if isinstance(data, dict) and "questions" in data:
        if not data["questions"]:
            raise ValueError("questions.json contains no questions")
        return data

    # Legacy format: a flat list of pre-assigned items. Wrap it so the app keeps
    # working, but there is only one condition available per question, so no
    # counterbalancing is possible. Rebuild with build_questions.py to fix that.
    if isinstance(data, list) and data:
        questions = []
        for i, item in enumerate(data, start=1):
            if not {"patient_query", "answer_text"}.issubset(item):
                continue
            cond = item.get("_condition", "legacy")
            questions.append({
                "question_index": item.get("question_index", i),
                "patient_query": item["patient_query"],
                "answers": {cond: item["answer_text"]},
            })
        if not questions:
            raise ValueError("No valid study items found in questions.json")
        return {
            "meta": {"backend": "unknown (legacy questions.json)",
                     "conditions": [], "n_questions": len(questions), "legacy": True},
            "questions": questions,
        }

    raise ValueError("Unrecognised questions.json format")


def n_questions() -> int:
    """Number of items a participant will see. Safe to call before assignment."""
    return min(QUESTIONS_PER_PARTICIPANT, len(load_bundle()["questions"]))


def assign_items(user_id: str, bundle: dict | None = None, slot: int | None = None) -> list[dict]:
    """Return this participant's items: a window of QUESTIONS_PER_PARTICIPANT
    questions, conditions rotated, in shuffled order (see the module docstring).
    `slot` is the participant number; None falls back to a hash of the user_id.

    Each item carries the fields the views and the persistence layer expect:
    item_id, question_index, patient_query, answer_text, condition and
    _condition (kept for backwards compatibility with existing records).
    """
    bundle = bundle or load_bundle()
    questions = bundle["questions"]
    conditions = list(bundle["meta"].get("conditions") or [])

    if not conditions:
        # Legacy bundle: use whichever single condition each question carries.
        items = []
        for q in questions:
            cond, answer = next(iter(q["answers"].items()))
            items.append(_make_item(q, cond, answer))
        return items

    offset = _stable_offset(user_id)
    if slot is None:
        slot = offset
    n, k = len(questions), min(QUESTIONS_PER_PARTICIPANT, len(questions))
    start = slot % n
    rotation = (slot // n) % len(conditions)

    items = []
    for j in range(k):
        q = questions[(start + j) % n]
        # By position in the window, not by question index: N need not be a
        # multiple of C, and the window wraps around.
        cond = conditions[(j + rotation) % len(conditions)]
        answer = q["answers"].get(cond)
        if not answer:
            continue
        items.append(_make_item(q, cond, answer))

    random.Random(offset).shuffle(items)
    return items


def _make_item(question: dict, condition: str, answer: str) -> dict:
    label = CONDITION_LABELS.get(condition, condition)
    idx = question["question_index"]
    slug = condition.upper()
    return {
        "item_id": f"Q{idx:02d}_{slug}",
        "question_index": idx,
        "patient_query": question["patient_query"],
        "answer_text": answer,
        "condition": condition,
        "condition_label": label,
        "_condition": label,
    }


def load_questions(user_id: str | None = None, slot: int | None = None) -> list[dict]:
    """Backwards-compatible entry point.

    With a user_id, returns that participant's counterbalanced items. Without
    one, returns the first rotation — useful only for counting items or for a
    preview, never for a real session.
    """
    return assign_items(user_id if user_id is not None else "__preview__", slot=slot)
