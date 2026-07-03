"""Questionnaire data and low-level helpers for the Phase I user study."""

import json
import pathlib
import urllib.parse

import streamlit as st


_QUESTIONNAIRE_PATH = pathlib.Path(__file__).parent / "questionnaire_questions.json"


def load_questionnaire_data() -> dict:
    """Load questionnaire definitions from the external JSON file."""
    with open(_QUESTIONNAIRE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def scroll_to_top() -> None:
    """Reset the page scroll position after a rerun."""
    scroll_script = """
        <script>
            const scrollTop = () => {
                try {
                    const targets = [
                        window.parent,
                        window.parent.document.documentElement,
                        window.parent.document.body,
                        window.parent.document.querySelector('section.main'),
                        window.parent.document.querySelector('[data-testid="stAppViewContainer"]'),
                        window.parent.document.querySelector('[data-testid="stMainBlockContainer"]'),
                    ];

                    targets.forEach((target) => {
                        if (!target) {
                            return;
                        }
                        if (typeof target.scrollTo === 'function') {
                            target.scrollTo(0, 0);
                        }
                        target.scrollTop = 0;
                    });
                } catch (error) {
                    // Ignore DOM timing issues and retry on the next tick.
                }
            };

            scrollTop();
            setTimeout(scrollTop, 50);
            setTimeout(scrollTop, 150);
            setTimeout(scrollTop, 300);
        </script>
    """
    st.iframe(
        f"data:text/html,{urllib.parse.quote(scroll_script)}",
        height=1,
    )


def build_likert_metadata(data: dict) -> tuple[list[str], list[int]]:
    """Return ordered Likert labels and numeric values from the JSON data."""
    labels = list(data["likert_scale"].values())
    values = [int(key) for key in data["likert_scale"]]
    return labels, values