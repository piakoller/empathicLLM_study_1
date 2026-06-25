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

            st.markdown(f"**{label}**")

            current_val = st.session_state[storage_key].get(key)

            # Render as full-width touch tiles. Streamlit's segmented_control
            # uses unstable internal markup, so explicit columns are safer here.
            cols = st.columns(len(_LIKERT_VALUES), gap="small")
            for col, value in zip(cols, _LIKERT_VALUES):
                with col:
                    if st.button(
                        str(value),
                        key=f"likert_{storage_key}_{key}_{value}",
                        type="primary" if current_val == value else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state[storage_key][key] = value
                        current_val = value
                        st.rerun()
            
            # Text labels for extremes
            st.markdown(
                """
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #666; margin-top: -10px; margin-bottom: 20px; padding: 0 5px;">
                    <span>1 – Gar nicht</span>
                    <span>5 – Sehr</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if current_val is None:
                all_answered = False
            else:
                answers[key] = int(current_val)

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
    
    st.progress(0.2, text="Schritt 1: Pre-Evaluation")

    st.markdown(
        f"""
        <div class="study-header">
            <p class="header-label">{cfg["header_label"]}</p>
            <h1>{cfg["title"]}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"{cfg['instructions']}")
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
    
    st.progress(0.9, text="Schritt 3: Post-Evaluation")

    st.markdown(
        f"""
        <div class="study-header">
            <p class="header-label">{cfg["header_label"]}</p>
            <h1>{cfg["title"]}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"{cfg['instructions']}")
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
