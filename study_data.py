"""Data loading and per-participant condition assignment for the Phase-I study.

The condition a participant sees for each question is decided here, not in
questions.json, so that condition is crossed with question across the sample
instead of being fixed to a subset of questions.

Assignment rule
---------------
With C conditions and questions indexed 1..N, participant p gets

    condition(question i) = conditions[(i - 1 + offset_p) mod C]

where offset_p is derived from the participant's user_id. Two properties follow:

  * within a participant, the conditions are balanced (N/C each, ±1) and every
    question is seen exactly once;
  * across participants, each question appears in every condition about equally
    often, so question difficulty becomes a block factor rather than a confound.

Presentation order is shuffled per participant with the same derived seed, so
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
    return len(load_bundle()["questions"])


def assign_items(user_id: str, bundle: dict | None = None) -> list[dict]:
    """Return this participant's items, one per question, conditions rotated.

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
    rotation = offset % len(conditions)

    items = []
    for i, q in enumerate(questions):
        cond = conditions[(i + rotation) % len(conditions)]
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


def load_questions(user_id: str | None = None) -> list[dict]:
    """Backwards-compatible entry point.

    With a user_id, returns that participant's counterbalanced items. Without
    one, returns the first rotation — useful only for counting items or for a
    preview, never for a real session.
    """
    return assign_items(user_id if user_id is not None else "__preview__")
