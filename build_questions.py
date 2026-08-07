"""
build_questions.py (Monadic Evaluation Version)
==============================================
Builds monadic (single-answer per page) evaluation items for the Streamlit user study UI.

Loads the latest 6-run benchmark suite results (Direct Empathy RAG, Clinical Only RAG, Two Stage RAG)
and outputs a randomized sequence of single-answer evaluation items into questions.json.

Usage:
    python build_questions.py [--include-twostage]

Output:
    questions.json  (in the user_study_monadic directory)
"""

import argparse
import json
import pathlib
import random
import re

BASE_DIR = pathlib.Path(__file__).resolve().parent
BENCHMARK_RESULTS_DIR = BASE_DIR.parent / "uq_medgemma_benchmark" / "results"
OUTPUT_QUESTIONS_JSON = BASE_DIR / "questions.json"


def strip_verbal_confidence(text: str) -> str:
    """Removes trailing VERBAL_CONFIDENCE tags from generated text."""
    if not text:
        return ""
    marker = "VERBAL_CONFIDENCE:"
    if marker in text:
        text = text.split(marker, 1)[0]
    return text.strip()


def get_latest_result_file(pattern: str) -> pathlib.Path:
    """Finds the most recent result file matching pattern in uq_medgemma_benchmark/results/."""
    matching = sorted(BENCHMARK_RESULTS_DIR.glob(pattern))
    if not matching:
        raise FileNotFoundError(f"No result files matching '{pattern}' in {BENCHMARK_RESULTS_DIR}")
    return matching[-1]


def extract_answer(item: dict) -> str:
    """Extracts final answer text from a benchmark question item."""
    gen_meta = item.get("generation_meta", {})
    if isinstance(gen_meta, dict) and gen_meta.get("final_answer"):
        return strip_verbal_confidence(str(gen_meta["final_answer"]))
    
    candidates = item.get("candidates", [])
    if candidates:
        return strip_verbal_confidence(str(candidates[0]))
    
    return ""


def main():
    parser = argparse.ArgumentParser(description="Build Monadic questions.json for Streamlit User Study")
    parser.add_argument(
        "--max-items",
        type=int,
        default=20,
        help="Maximum total items to present to user (default: 20)",
    )
    parser.add_argument(
        "--include-twostage",
        action="store_true",
        help="Include Two Stage RAG run alongside Direct Empathy and Clinical Only RAG",
    )
    args = parser.parse_args()

    file_empathy = get_latest_result_file("uq_tradeoff_direct_empathy_20*.json")
    file_clinical = get_latest_result_file("uq_tradeoff_clinical_only_20*.json")

    print(f"[LOAD] Empathy: {file_empathy.name}")
    print(f"[LOAD] Clinical: {file_clinical.name}")

    with open(file_empathy, "r", encoding="utf-8") as f:
        data_emp = json.load(f).get("results", [])
    with open(file_clinical, "r", encoding="utf-8") as f:
        data_cli = json.load(f).get("results", [])

    map_emp = {item["question"].strip(): item for item in data_emp if item.get("question")}
    map_cli = {item["question"].strip(): item for item in data_cli if item.get("question")}

    all_questions = list(map_emp.keys())
    random.seed(42)
    random.shuffle(all_questions)

    # Balance 50/50: half questions get Direct Empathy, half get Clinical Only
    monadic_items = []
    half = len(all_questions) // 2

    for idx, q_text in enumerate(all_questions[:args.max_items], start=1):
        if idx <= half:
            cond_label = "Direct Empathy (RAG)"
            item_src = map_emp[q_text]
        else:
            cond_label = "Clinical Only (RAG)"
            item_src = map_cli[q_text]

        ans_text = extract_answer(item_src)
        if not ans_text:
            continue

        cond_slug = "EMPATHY" if "Empathy" in cond_label else "CLINICAL"
        monadic_items.append({
            "item_id": f"MONADIC_Q{idx:02d}_{cond_slug}",
            "question_index": idx,
            "patient_query": q_text,
            "answer_text": ans_text,
            "_condition": cond_label,
        })

    # Final shuffle so conditions are intermingled
    random.shuffle(monadic_items)

    with open(OUTPUT_QUESTIONS_JSON, "w", encoding="utf-8") as f:
        json.dump(monadic_items, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Successfully generated {len(monadic_items)} monadic evaluation items (max cap: {args.max_items}) -> {OUTPUT_QUESTIONS_JSON.name}")
    n_emp = sum(1 for item in monadic_items if "Empathy" in item["_condition"])
    print(f"   Breakdown: {n_emp} Direct Empathy, {len(monadic_items) - n_emp} Clinical Only.")


if __name__ == "__main__":
    main()
