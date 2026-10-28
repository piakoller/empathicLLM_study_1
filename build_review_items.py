"""
build_review_items.py — the blinded item list for the physicians' medical check.

    python build_review_items.py

Reads questions.json and writes
    review_items.json                     the 60 answers without their arm, in the
                                          same order and with the same IDs (A01–A60)
                                          as the Excel sheets in medical_review/
    medical_review/review_key.json        ID -> question and arm; for the study team
                                          only, never in the repository

The app shows review_items.json in its review mode (?review=<token>, review_view.py).
"""

from __future__ import annotations

import json
import pathlib
import random

BASE_DIR = pathlib.Path(__file__).resolve().parent
BUNDLE = BASE_DIR / "questions.json"
OUT_ITEMS = BASE_DIR / "review_items.json"
OUT_KEY = BASE_DIR / "medical_review" / "review_key.json"

# Flagged by the automatic screening, and Q14 where the arms contradict each other.
# Reviewed first; same set and wording as in the Excel sheets.
PRIORITY = {(20, "clinical_only"), (11, "direct_empathy"), (16, "direct_empathy"), (20, "direct_empathy"),
            (11, "two_stage"), (12, "two_stage"), (14, "clinical_only"), (14, "direct_empathy"), (14, "two_stage")}
REASON = {20: "automatische Prüfung: Antwort nicht im ersten Satz", 11: "automatische Prüfung",
          16: "automatische Prüfung: Antwort nicht im ersten Satz", 12: "automatische Prüfung: «Studien zeigen»",
          14: "die Antworten zu dieser Frage widersprechen sich"}
SEED = 20261028   # the Excel sheets of 27 Oct 2026 were built with this seed


def main() -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    arms = bundle["meta"]["conditions"]
    rows = [(q["question_index"], q["patient_query"], arm, q["answers"][arm])
            for q in bundle["questions"] for arm in arms]
    rng = random.Random(SEED)
    prio = [r for r in rows if (r[0], r[2]) in PRIORITY]
    rest = [r for r in rows if (r[0], r[2]) not in PRIORITY]
    rng.shuffle(prio)
    rng.shuffle(rest)

    items, key = [], {}
    for i, (q, query, arm, answer) in enumerate(prio + rest):
        item_id = f"A{i + 1:02d}"
        items.append({"id": item_id, "question_index": q, "patient_query": query, "answer_text": answer,
                      "hint": REASON.get(q, "") if (q, arm) in PRIORITY else ""})
        key[item_id] = {"question_index": q, "arm": arm}

    OUT_ITEMS.write_text(json.dumps({"built_from": bundle["meta"].get("built_at", ""), "items": items},
                                    indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_KEY.parent.mkdir(exist_ok=True)
    OUT_KEY.write_text(json.dumps(key, indent=2), encoding="utf-8")
    print(f"[OK] {len(items)} items -> {OUT_ITEMS.name}; key -> {OUT_KEY.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
