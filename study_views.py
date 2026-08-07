"""Streamlit view rendering for the Monadic (Single-Answer per Page) Phase I user study."""

import datetime
import html as html_module
import json
import uuid
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

from questionnaire import render_post_questionnaire, render_pre_questionnaire
from study_data import load_questions
from study_persistence import build_current_payload, save_current_progress
from questionnaire_data import scroll_to_top


def _request_scroll_to_top(session_state) -> None:
    session_state.scroll_to_top_next_render = True


def _consume_scroll_to_top(session_state) -> None:
    if session_state.get("scroll_to_top_next_render"):
        session_state.scroll_to_top_next_render = False
        scroll_to_top(str(uuid.uuid4()))


def _record_ratings(session_state, ratings: dict) -> None:
    """Store the monadic ratings for the current item including response time, then advance."""
    item = session_state.mock_data[session_state.question_idx]

    response_time_s = None
    if session_state.question_start_time is not None:
        delta = datetime.datetime.now(ZoneInfo("Europe/Zurich")) - session_state.question_start_time
        response_time_s = round(delta.total_seconds(), 2)

    session_state.results.append(
        {
            "user_id": session_state.user_id,
            "item_id": item["item_id"],
            "condition": item.get("_condition", "unknown"),
            "ratings": ratings,
            "response_time_s": response_time_s,
            "timestamp": datetime.datetime.now(ZoneInfo("Europe/Zurich")).isoformat(),
        }
    )

    next_idx = session_state.question_idx + 1
    if next_idx >= len(session_state.mock_data):
        session_state.view = "post_questionnaire"
    else:
        session_state.question_idx = next_idx

    session_state.question_start_time = None
    session_state.needs_db_save = True
    _request_scroll_to_top(session_state)


def _render_onboarding(session_state) -> None:
    st.markdown(
        """
        <div class="study-header">
            <div class="header-title">Evaluation von Patientenantworten</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    num_questions = len(load_questions())
    st.markdown(
        f"""
        Willkommen und vielen Dank für Ihre Teilnahme!

        In dieser Studie sehen Sie **{num_questions} Antworten** auf typische Patientenfragen zum Thema PSMA-gerichtete Theranostik bei Prostatakrebs.

        Ihre Aufgabe ist ganz einfach: **Lesen Sie jede Antwort aufmerksam durch und wählen Sie anschließend mit einem Klick diejenige Aussage aus, die Ihr Gefühl und Ihre Wahrnehmung beim Lesen am besten beschreibt.**

        *Hinweis für Smartphones:* Sie müssen keine Zahlen eingeben oder Regler verschieben. Ein einfacher Tipp auf die passende Aussage genügt.
        
        **Hinweis:** Die generierten Antworten sind lediglich Vorschläge im Rahmen unserer Forschung. Konsultieren Sie bei medizinischen Fragen stets Ihren behandelnden Arzt.
        """
    )

    st.markdown("")

    if st.button("Weiter", type="primary", use_container_width=True):
        session_state.view = "demographics"
        _request_scroll_to_top(session_state)
        st.rerun()
    _consume_scroll_to_top(session_state)


def _render_demographics(session_state) -> None:
    st.markdown(
        """
        <div class="study-header">
            <div class="header-title">Angaben zu Ihrer Person</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("Bevor wir beginnen, bitten wir Sie um einige kurze Angaben.")
    st.divider()

    role = st.selectbox(
        "Ihre Rolle",
        options=["Patient:in", "Arzt/Ärztin"],
        index=None,
        placeholder="Bitte auswählen…",
    )

    age = st.selectbox(
        "Ihre Altersgruppe",
        options=["<35", "35-45", "46-55", "56-65", "66-75", "76-85", "86+"],
        index=None,
        placeholder="Bitte auswählen…",
    )

    gender = st.selectbox(
        "Geschlecht",
        options=["Männlich", "Weiblich", "Divers", "Keine Angabe"],
        index=None,
        placeholder="Bitte auswählen…",
    )

    if st.button("Weiter", type="primary", use_container_width=True):
        if not role or not age or not gender:
            st.warning("Bitte füllen Sie alle Felder aus, bevor Sie beginnen.")
            return

        session_state.demographics = {
            "user_id": session_state.user_id,
            "role": role,
            "age_range": age,
            "gender": gender,
            "started_at": datetime.datetime.now(ZoneInfo("Europe/Zurich")).isoformat(),
        }
        session_state.role = role
        session_state.mock_data = load_questions()
        session_state.question_idx = 0
        session_state.results = []
        session_state.view = "pre_questionnaire"
        session_state.needs_db_save = True
        _request_scroll_to_top(session_state)
        st.rerun()
    _consume_scroll_to_top(session_state)


def _render_evaluation(session_state) -> None:
    items = session_state.mock_data
    idx = session_state.question_idx
    item = items[idx]
    total = len(items)

    if session_state.question_start_time is None:
        session_state.question_start_time = datetime.datetime.now(ZoneInfo("Europe/Zurich"))

    # Print current item condition to Python terminal console (once per item)
    if session_state.get("last_printed_item_idx") != idx:
        session_state.last_printed_item_idx = idx
        cond = item.get("_condition", "unknown")
        q_preview = item.get("patient_query", "")[:45]
        print(f"[STUDY MONADIC] Item {idx + 1}/{total} | Condition: {cond} | ID: {item.get('item_id')} | Query: '{q_preview}...'")

    progress_fraction = idx / total
    st.progress(progress_fraction, text=f"Antwort {idx + 1} von {total}")

    # Question Header
    st.markdown(
        f"""
        <div class="study-header">
            <p class="header-label">Die Frage</p>
            <h1 style="font-size: 1.25em; line-height: 1.4;">{item["patient_query"]}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Display answer text with full Markdown rendering (bolding, lists, headings)
    with st.container(border=True):
        st.markdown(item["answer_text"])

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Welche Aussage beschreibt Ihre Wahrnehmung dieser Antwort am besten?")
    st.markdown("Bitte wählen Sie **genau eine Aussage** aus, die am ehesten zutrifft:")

    statement_options = [
        "🟢 A) Die Antwort informiert mich klar, nimmt mir die Sorge und gibt mir ein gutes Gefühl.",
        "🔵 B) Die Antwort ist rein sachlich und informativ, wirkt auf mich aber etwas kühl.",
        "🟡 C) Die Antwort ist mir zu kompliziert geschrieben und enthält zu viele Fachwörter.",
        "🔴 D) Die Antwort verunsichert mich eher oder macht mir Angst vor der Therapie.",
    ]

    selected_statement = st.radio(
        "Ihre Einschätzung:",
        options=statement_options,
        index=None,
        key=f"stmt_{idx}",
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Nächste Antwort bewerten ➡️", type="primary", use_container_width=True, key=f"btn_next_{idx}"):
        if not selected_statement:
            st.warning("Bitte wählen Sie zuerst eine Aussage aus, bevor Sie fortfahren.")
            return

        statement_code = "other"
        if "informiert mich klar" in selected_statement:
            statement_code = "empathic_informative"
        elif "sachlich" in selected_statement:
            statement_code = "clinical_factual"
        elif "kompliziert" in selected_statement:
            statement_code = "too_complex"
        elif "verunsichert" in selected_statement:
            statement_code = "causes_anxiety"

        ratings_dict = {
            "selected_statement": selected_statement,
            "statement_code": statement_code,
        }
        _record_ratings(session_state, ratings_dict)
        _request_scroll_to_top(session_state)
        st.rerun()

    _consume_scroll_to_top(session_state)


def _render_outro(session_state) -> None:
    st.markdown(
        """
        <div class="outro-card">
            <h2>🎉 Vielen Dank!</h2>
            <p>
                Ihre Bewertung ist abgeschlossen. Wir danken Ihnen herzlich
                für Ihre Zeit und Ihren Beitrag zu dieser Forschung.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    payload = build_current_payload(session_state)

    if session_state.db_save_status is None:
        save_current_progress(session_state)

    success, msg = session_state.db_save_status
    if success:
        st.success(f"✅ {msg}")
    else:
        st.warning(f"⚠️ {msg}")

    with st.expander("Erhobene Daten (Verifikation)"):
        st.json(payload, expanded=True)


def render_study_view(session_state) -> None:
    if session_state.view == "onboarding":
        _render_onboarding(session_state)
    elif session_state.view == "demographics":
        _render_demographics(session_state)
    elif session_state.view == "pre_questionnaire":
        render_pre_questionnaire()
    elif session_state.view == "evaluation":
        _render_evaluation(session_state)
    elif session_state.view == "post_questionnaire":
        render_post_questionnaire()
    elif session_state.view == "outro":
        _render_outro(session_state)