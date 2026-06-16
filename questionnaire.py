"""
questionnaire.py
================
Pre- and post-study Likert-scale questionnaire views for the Phase-I user study.

Questions are loaded from ``questionnaire_questions.json`` so they can be edited
without touching this file.

Public API
----------
render_pre_questionnaire()   – call from app.py for the pre-study view
render_post_questionnaire()  – call from app.py for the post-study view
"""

import json
import pathlib

import streamlit as st

# ──────────────────────────────────────────────────────────────
# DATA LOADING
# ──────────────────────────────────────────────────────────────
_QUESTIONNAIRE_PATH = pathlib.Path(__file__).parent / "questionnaire_questions.json"


def _load_questionnaire_data() -> dict:
    """Load questionnaire definitions from the external JSON file."""
    with open(_QUESTIONNAIRE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


_DATA = _load_questionnaire_data()

# Build ordered Likert label / value lists from JSON (keys are strings "1"–"5")
_LIKERT_LABELS: list[str] = list(_DATA["likert_scale"].values())
_LIKERT_VALUES: list[int]  = [int(k) for k in _DATA["likert_scale"]]


# ──────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ──────────────────────────────────────────────────────────────
def _render_likert_section(sections: list[dict], storage_key: str) -> dict | None:
    """
    Render all Likert sections and collect answers.

    Parameters
    ----------
    sections:     list of section dicts as defined in the JSON file.
    storage_key:  session-state key whose dict holds previously selected values
                  (used to restore state on Streamlit re-runs).

    Returns
    -------
    dict mapping item keys → integer scores if every item is answered,
    otherwise None (used to block form submission).
    """
    answers: dict[str, int] = {}
    all_answered = True

    for sec in sections:
        # Section header
        desc_html = (
            f' <span class="section-desc">{sec["description"]}</span>'
            if sec.get("description")
            else ""
        )
        st.markdown(
            f'<div class="questionnaire-section">'
            f'<span class="section-title">{sec["section"]}</span>'
            f'{desc_html}</div>',
            unsafe_allow_html=True,
        )

        # One radio row per item
        for item in sec["items"]:
            key   = item["key"]
            label = item["label"]

            current_val = st.session_state[storage_key].get(key)
            try:
                default_index = (
                    _LIKERT_VALUES.index(current_val)
                    if current_val in _LIKERT_VALUES
                    else None
                )
            except ValueError:
                default_index = None

            choice = st.radio(
                label,
                options=_LIKERT_LABELS,
                index=default_index,
                horizontal=False,            # vertical layout for mobile
                key=f"radio_{key}",
            )

            if choice is None:
                all_answered = False
            else:
                answers[key] = _LIKERT_VALUES[_LIKERT_LABELS.index(choice)]

        st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    return answers if all_answered else None


def _scale_legend() -> str:
    """Return a compact inline scale legend string."""
    parts = [f"{v}\u00a0=\u00a0{lbl.split('\u2013', 1)[-1].strip()}"
             for v, lbl in zip(_LIKERT_VALUES, _LIKERT_LABELS)]
    return "&nbsp;·&nbsp;".join(parts)


# ──────────────────────────────────────────────────────────────
# PUBLIC VIEW RENDERERS
# ──────────────────────────────────────────────────────────────
def render_pre_questionnaire() -> None:
    """Render the pre-study questionnaire view."""
    cfg = _DATA["pre"]

    st.markdown(
        f"""
        <div class="study-header">
            <p class="header-label">{cfg["header_label"]}</p>
            <h1>{cfg["title"]}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""{cfg["instructions"]}

**Skala:**  
{_scale_legend()}
"""
    )
    st.divider()

    answers = _render_likert_section(cfg["sections"], "pre_questionnaire")

    st.divider()
    if st.button(cfg["button_label"], type="primary", use_container_width=True, key="pre_submit"):
        if answers is None:
            st.warning("Bitte beantworten Sie alle Fragen, bevor Sie fortfahren.")
        else:
            st.session_state.pre_questionnaire = answers
            st.session_state.view = "evaluation"
            st.rerun()


def render_post_questionnaire() -> None:
    """Render the post-study questionnaire view."""
    cfg = _DATA["post"]

    st.markdown(
        f"""
        <div class="study-header">
            <p class="header-label">{cfg["header_label"]}</p>
            <h1>{cfg["title"]}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""{cfg["instructions"]}

**Skala:**  
{_scale_legend()}
"""
    )
    st.divider()

    answers = _render_likert_section(cfg["sections"], "post_questionnaire")

    st.divider()
    if st.button(cfg["button_label"], type="primary", use_container_width=True, key="post_submit"):
        if answers is None:
            st.warning("Bitte beantworten Sie alle Fragen, bevor Sie fortfahren.")
        else:
            st.session_state.post_questionnaire = answers
            st.session_state.view = "outro"
            st.rerun()
