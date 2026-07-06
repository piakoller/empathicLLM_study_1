"""Data loading helpers for the Phase I user study."""

import json
import pathlib
import random


_BASE_DIR = pathlib.Path(__file__).parent
_DATA_DIR = _BASE_DIR / "data"
_QUESTIONS_PATH = _DATA_DIR / "psma_sample_questions.json"
_ROOT_QUESTIONS_PATH = _BASE_DIR / "questions.json"


def _load_json_file(path: pathlib.Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load_question_texts() -> list[str]:
    data = _load_json_file(_QUESTIONS_PATH)

    if isinstance(data, dict):
        if "psma_therapy" in data:
            raw_items = data["psma_therapy"]
        elif "questions" in data:
            raw_items = data["questions"]
        else:
            raise ValueError(f"Unsupported question bank structure in {_QUESTIONS_PATH}")
    elif isinstance(data, list):
        raw_items = data
    else:
        raise ValueError(f"Unsupported question bank structure in {_QUESTIONS_PATH}")

    questions: list[str] = []
    for item in raw_items:
        if isinstance(item, str):
            question = item.strip()
        elif isinstance(item, dict):
            question = str(item.get("patient_query") or item.get("question") or "").strip()
        else:
            question = ""

        if question:
            questions.append(question)

    if not questions:
        raise ValueError(f"No questions found in {_QUESTIONS_PATH}")

    return questions


def _load_benchmark_rows() -> list[dict]:
    benchmark_paths = sorted(_DATA_DIR.glob("uq_benchmark_*.json"))
    if not benchmark_paths:
        raise FileNotFoundError(f"No benchmark files found in {_DATA_DIR}")

    benchmark_data = _load_json_file(benchmark_paths[-1])
    if isinstance(benchmark_data, dict):
        rows = benchmark_data.get("results", [])
    elif isinstance(benchmark_data, list):
        rows = benchmark_data
    else:
        raise ValueError(f"Unsupported benchmark structure in {benchmark_paths[-1]}")

    return [row for row in rows if isinstance(row, dict) and row.get("question")]


def _normalize_items(items: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        required_keys = {"item_id", "patient_query", "answer_a_text", "answer_b_text"}
        if not required_keys.issubset(item):
            continue

        normalized.append(item)

    if not normalized:
        raise ValueError("No valid study items found")

    return normalized


def _strip_verbal_confidence(text: str) -> str:
    """Remove inline confidence annotations from generated answers."""
    marker = "VERBAL_CONFIDENCE:"
    if marker not in text:
        return text.strip()
    return text.split(marker, 1)[0].rstrip()


def load_questions() -> list[dict]:
    """Load evaluation items from data files, with a root-level fallback."""
    try:
        question_texts = _load_question_texts()
        benchmark_rows = _load_benchmark_rows()
        benchmark_by_question = {
            row["question"].strip(): row
            for row in benchmark_rows
            if row.get("question")
        }

        items: list[dict] = []
        for index, question in enumerate(question_texts, start=1):
            benchmark_row = benchmark_by_question.get(question)
            if benchmark_row is None:
                raise ValueError(f"No benchmark answers found for question: {question}")

            if "answer_a_text" in benchmark_row and "answer_b_text" in benchmark_row:
                answer_a_text = _strip_verbal_confidence(str(benchmark_row["answer_a_text"]))
                answer_b_text = _strip_verbal_confidence(str(benchmark_row["answer_b_text"]))
                source_a = benchmark_row.get("_source_a", "answer_a")
                source_b = benchmark_row.get("_source_b", "answer_b")
            else:
                candidates = benchmark_row.get("candidates", [])
                if len(candidates) < 2:
                    raise ValueError(f"Need at least two candidate answers for question: {question}")
                answer_a_text = _strip_verbal_confidence(str(candidates[0]))
                answer_b_text = _strip_verbal_confidence(str(candidates[1]))
                source_a = "candidate_1"
                source_b = "candidate_2"

            if random.choice([True, False]):
                answer_a_text, answer_b_text = answer_b_text, answer_a_text
                source_a, source_b = source_b, source_a

            items.append(
                {
                    "item_id": benchmark_row.get("item_id", f"PSMA_BENCH_{index:02d}"),
                    "patient_query": question,
                    "answer_a_text": answer_a_text,
                    "answer_b_text": answer_b_text,
                    "_source_a": source_a,
                    "_source_b": source_b,
                }
            )

        return _normalize_items(items)
    except Exception:
        if _ROOT_QUESTIONS_PATH.exists():
            return _normalize_items(_load_json_file(_ROOT_QUESTIONS_PATH))
        raise