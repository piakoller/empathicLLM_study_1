"""Streamlit entry point for the Phase I user study."""

import pathlib
import uuid

import streamlit as st

from study_data import items_from_ids
from study_persistence import load_progress, save_current_progress
from study_views import render_study_view
from review_view import render_review, reviewer_from_url


st.set_page_config(
    page_title="Phase-I-Nutzerstudie – LLM-Evaluation",
    page_icon="🩺",
    layout="wide",
)

_STYLES_PATH = pathlib.Path(__file__).parent / "styles.css"


def _load_css() -> None:
    """Read the external CSS file and inject it into the Streamlit page."""
    css_text = _STYLES_PATH.read_text(encoding="utf-8")
    
    font_size_px = 18  # Static large font size
    dynamic_css = f"html {{ font-size: {font_size_px}px !important; }}"
    
    st.markdown(f"<style>{css_text}\n{dynamic_css}</style>", unsafe_allow_html=True)


def _restore_progress(record: dict) -> None:
    """Put a saved record back into the session after a page reload."""
    ss = st.session_state
    ss.demographics = record.get("demographics") or {}
    ss.role = ss.demographics.get("role")
    ss.pre_questionnaire = record.get("pre_questionnaire") or {}
    ss.results = record.get("votes") or []
    ss.post_questionnaire = record.get("post_questionnaire") or {}
    try:
        ss.mock_data = items_from_ids(record.get("assigned_items") or [])
    except (KeyError, ValueError):
        ss.mock_data = []  # bundle changed since the record was saved
    status = record.get("status")
    if status == "completed":
        ss.view = "outro"
        ss.db_save_status = (True, "")  # already saved; do not save again
    elif ss.mock_data and status in ("pre_questionnaire", "evaluation", "post_questionnaire"):
        ss.view = status
        ss.question_idx = min(len(ss.results), len(ss.mock_data) - 1)
    # otherwise the participant starts over under the same id


def _initialize_session_state() -> None:
    if "user_id" not in st.session_state:
        # The id lives in the URL (?pid=…), so a reload continues the same
        # participant instead of starting a new one and using up a slot.
        pid = st.query_params.get("pid")
        try:
            pid = str(uuid.UUID(pid)) if pid else None
        except ValueError:
            pid = None
        st.session_state.user_id = pid or str(uuid.uuid4())
        st.query_params["pid"] = st.session_state.user_id
        record = load_progress(pid) if pid else None
        if record:
            _restore_progress(record)
    if "view" not in st.session_state:
        st.session_state.view = "onboarding"
    if "question_idx" not in st.session_state:
        st.session_state.question_idx = 0
    if "results" not in st.session_state:
        st.session_state.results = []
    if "demographics" not in st.session_state:
        st.session_state.demographics = {}
    if "mock_data" not in st.session_state:
        st.session_state.mock_data = []
    if "db_save_status" not in st.session_state:
        st.session_state.db_save_status = None
    if "pre_questionnaire" not in st.session_state:
        st.session_state.pre_questionnaire = {}
    if "post_questionnaire" not in st.session_state:
        st.session_state.post_questionnaire = {}
    if "question_start_time" not in st.session_state:
        st.session_state.question_start_time = None
    if "needs_db_save" not in st.session_state:
        st.session_state.needs_db_save = False


# Physicians' medical check: a personal link (?review=<token>) opens the review mode
# instead of the study; it never touches the participant data.
_rater = reviewer_from_url()
if _rater:
    _load_css()
    render_review(_rater)
    st.stop()

_initialize_session_state()
_load_css()


if st.session_state.needs_db_save:
    st.session_state.needs_db_save = False
    save_current_progress(st.session_state)


render_study_view(st.session_state)
