"""Questionnaire data and low-level helpers for the Phase I user study."""

import json
import pathlib
import urllib.parse

import streamlit as st
import streamlit.components.v1 as components


_QUESTIONNAIRE_PATH = pathlib.Path(__file__).parent / "questionnaire_questions.json"


def load_questionnaire_data() -> dict:
    """Load questionnaire definitions from the external JSON file."""
    with open(_QUESTIONNAIRE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


_SCROLL_COMP_PATH = pathlib.Path(__file__).parent / "scroll_component"
_scroll_component = components.declare_component("scroll_component", path=str(_SCROLL_COMP_PATH))

def scroll_to_top(scroll_key: str = "") -> None:
    """Reset the page scroll position after a rerun."""
    _scroll_component(key=scroll_key)


def build_likert_metadata(data: dict) -> tuple[list[str], list[int]]:
    """Return ordered Likert labels and numeric values from the JSON data."""
    labels = list(data["likert_scale"].values())
    values = [int(key) for key in data["likert_scale"]]
    return labels, values