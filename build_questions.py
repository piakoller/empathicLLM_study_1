"""
build_questions.py
==================
Merges the triple-pillar pipeline results (empathic NURSE-based responses)
with the rulebasedLLM baseline responses into a single questions.json
suitable for the 2AFC user study UI.

The assignment of pipeline vs. baseline to "A" or "B" is randomized
per question (seeded for reproducibility) to control for position bias.

Run once:
    python build_questions.py

Output:
    questions.json  (in the user_study directory)
"""

import json
import pathlib
import random

# ── Paths ──
BASE = pathlib.Path(__file__).resolve().parent
TRIPLE_PILLAR = BASE.parent / "triple_pillar_pipeline" / "results" / "psma_benchmark_results.json"
RULEBASED     = BASE.parent / "rulebasedLLM" / "results" / "psma_benchmark.json"
OUTPUT        = BASE / "questions.json"

# ── Load sources ──
with open(TRIPLE_PILLAR, encoding="utf-8") as f:
    tp_data = json.load(f)                          # list of {request, response}

with open(RULEBASED, encoding="utf-8") as f:
    rb_data = json.load(f)                          # {model, rows: [...]}

rb_rows = rb_data["rows"]                           # list of {index, question, baseline_response, …}

# ── Build lookup: question text → baseline response ──
baseline_by_question: dict[str, str] = {}
for row in rb_rows:
    baseline_by_question[row["question"].strip()] = row["baseline_response"]

# ── Merge into 2AFC items ──
random.seed(42)                                     # reproducible A/B assignment
items: list[dict] = []

for i, tp_item in enumerate(tp_data):
    query = tp_item["request"]["query"].strip()
    patient_id = tp_item["request"]["patient_id"]
    pipeline_response = tp_item["response"]["final_response"]

    # Find matching baseline
    baseline_response = baseline_by_question.get(query)
    if baseline_response is None:
        print(f"[WARN] No baseline match for [{patient_id}]: {query[:60]}... -- skipping")
        continue

    # Randomize which answer is A vs B to prevent position bias
    if random.random() < 0.5:
        answer_a = pipeline_response
        answer_b = baseline_response
        source_a = "triple_pillar_pipeline"
        source_b = "baseline_medgemma"
    else:
        answer_a = baseline_response
        answer_b = pipeline_response
        source_a = "baseline_medgemma"
        source_b = "triple_pillar_pipeline"

    items.append({
        "item_id": patient_id,
        "patient_query": query,
        "answer_a_text": answer_a,
        "answer_b_text": answer_b,
        # Hidden metadata (not shown to participants, used for analysis)
        "_source_a": source_a,
        "_source_b": source_b,
    })

# ── Write output ──
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(items, f, indent=2, ensure_ascii=False)

print(f"[OK] Wrote {len(items)} items to {OUTPUT}")
print(f"   A/B assignment breakdown:")
n_pipe_a = sum(1 for x in items if x["_source_a"] == "triple_pillar_pipeline")
print(f"     Pipeline as A: {n_pipe_a}")
print(f"     Pipeline as B: {len(items) - n_pipe_a}")
