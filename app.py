"""Streamlit entry point for the Phase I user study."""

import pathlib
import uuid

import streamlit as st

from study_persistence import save_current_progress
from study_views import render_study_view


st.set_page_config(
    page_title="Phase-I-Nutzerstudie – LLM-Evaluation",
    page_icon="🩺",
    layout="wide",
)

_STYLES_PATH = pathlib.Path(__file__).parent / "styles.css"


def _load_css() -> None:
    """Read the external CSS file and inject it into the Streamlit page."""
    css_text = _STYLES_PATH.read_text(encoding="utf-8")
    
    font_size_px = 22  # Static large font size
    dynamic_css = f"html {{ font-size: {font_size_px}px !important; }}"
    
    st.markdown(f"<style>{css_text}\n{dynamic_css}</style>", unsafe_allow_html=True)


def _initialize_session_state() -> None:
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
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


_initialize_session_state()
_load_css()


if st.session_state.needs_db_save:
    st.session_state.needs_db_save = False
    save_current_progress(st.session_state)


render_study_view(st.session_state)
