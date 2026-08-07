"""Data loading helpers for the Monadic Phase I user study."""

import json
import pathlib
import random

_BASE_DIR = pathlib.Path(__file__).parent
_ROOT_QUESTIONS_PATH = _BASE_DIR / "questions.json"


def _load_json_file(path: pathlib.Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _normalize_items(items: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        required_keys = {"item_id", "patient_query", "answer_text"}
        if not required_keys.issubset(item):
            continue

        normalized.append(item)

    if not normalized:
        raise ValueError("No valid monadic study items found in questions.json")

    return normalized


def load_questions() -> list[dict]:
    """Load monadic evaluation items from questions.json."""
    if _ROOT_QUESTIONS_PATH.exists():
        return _normalize_items(_load_json_file(_ROOT_QUESTIONS_PATH))
    raise FileNotFoundError(f"Missing {_ROOT_QUESTIONS_PATH}. Please run python build_questions.py first.")