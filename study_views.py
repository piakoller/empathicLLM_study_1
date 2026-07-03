"""Streamlit view rendering for the Phase I user study."""

import datetime
import html as html_module
import json
import uuid

import streamlit as st

from questionnaire import render_post_questionnaire, render_pre_questionnaire
from study_data import load_questions
from study_persistence import build_current_payload, save_current_progress


def _scroll_to_top() -> None:
    """Scroll the Streamlit app to the top using st.iframe."""
    st.iframe(
        f"<script> /* {uuid.uuid4()} */ "
        "window.scrollTo(0,0);"
        "try{window.parent.scrollTo(0,0);}catch(e){}"
        "try{"
        "var m=window.parent.document.querySelector('[data-testid=\"stAppViewContainer\"]');"
        "if(m)m.scrollTop=0;"
        "var b=window.parent.document.querySelector('[data-testid=\"block-container\"]');"
        "if(b)b.scrollTop=0;"
        "}catch(e){}"
        "</script>",
        height=1,
    )


def _record_vote(session_state, vote_label: str) -> None:
    """Store the vote for the current item including response time, then advance."""
    item = session_state.mock_data[session_state.question_idx]

    response_time_s = None
    if session_state.question_start_time is not None:
        delta = datetime.datetime.now(datetime.timezone.utc) - session_state.question_start_time
        response_time_s = round(delta.total_seconds(), 2)

    session_state.results.append(
        {
            "user_id": session_state.user_id,
            "item_id": item["item_id"],
            "vote": vote_label,
            "response_time_s": response_time_s,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    )

    next_idx = session_state.question_idx + 1
    if next_idx >= len(session_state.mock_data):
        session_state.view = "post_questionnaire"
    else:
        session_state.question_idx = next_idx

    session_state.question_start_time = None
    session_state.needs_db_save = True


def _render_onboarding(session_state) -> None:
    st.markdown(
        """
        <div class="study-header">
            <p class="header-label">Phase I · Nutzerstudie</p>
            <h1>🩺 LLM-Evaluation in der klinischen Theranostik</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        Willkommen und vielen Dank für Ihre Teilnahme!

        Sie werden **20 Patientenfragen** zum Thema PSMA-gerichtete
        Theranostik bei Prostatakrebs sehen. Zu jeder Frage erhalten Sie
        zwei anonymisierte, modellgenerierte Antworten in separaten Tabs.

        Ihre Aufgabe: **Wählen Sie die Antwort, die Sie für hilfreicher,
        genauer und angemessener halten** – oder geben Sie an, dass beide
        gleich gut bzw. unzureichend sind.

        Bevor wir beginnen, bitten wir Sie um einige kurze Angaben.
        """
    )

    st.divider()
    st.subheader("📋 Angaben zu Ihrer Person")

    role = st.selectbox(
        "Ihre berufliche Rolle",
        options=["Patient:in", "Arzt/Ärztin", "Psycholog:in"],
        index=None,
        placeholder="Bitte auswählen…",
    )

    age = st.selectbox(
        "Ihre Altersgruppe",
        options=["18–25", "26–35", "36–45", "46–55", "56–65", "66–75", "76+"],
        index=None,
        placeholder="Bitte auswählen…",
    )

    gender = st.selectbox(
        "Geschlecht",
        options=["Männlich", "Weiblich", "Divers", "Keine Angabe"],
        index=None,
        placeholder="Bitte auswählen…",
    )

    st.markdown("")

    if st.button("🚀  Studie starten", type="primary", use_container_width=True):
        if not role or not age or not gender:
            st.warning("Bitte füllen Sie alle Felder aus, bevor Sie beginnen.")
            return

        session_state.demographics = {
            "user_id": session_state.user_id,
            "role": role,
            "age_range": age,
            "gender": gender,
            "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        session_state.mock_data = load_questions()
        session_state.question_idx = 0
        session_state.results = []
        session_state.view = "pre_questionnaire"
        session_state.needs_db_save = True
        st.rerun()


def _render_evaluation(session_state) -> None:
    items = session_state.mock_data
    idx = session_state.question_idx
    item = items[idx]
    total = len(items)

    if session_state.get("_scroll_top"):
        session_state._scroll_top = False
        _scroll_to_top()

    if session_state.question_start_time is None:
        session_state.question_start_time = datetime.datetime.now(datetime.timezone.utc)

    progress_fraction = idx / total
    st.progress(progress_fraction, text=f"Frage {idx + 1} von {total}")

    st.markdown(
        f"""
        <div class="study-header">
            <p class="header-label">🗣️ Patientenfrage</p>
            <h1>{item["patient_query"]}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="tab-hint">'
        "👆 Wechseln Sie zwischen den Tabs, um beide Antworten zu lesen."
        "</p>",
        unsafe_allow_html=True,
    )

    tab_a, tab_b = st.tabs(["📝 Antwort A", "📝 Antwort B"])

    escaped_a = html_module.escape(item["answer_a_text"]).replace("\n", "<br>")
    escaped_b = html_module.escape(item["answer_b_text"]).replace("\n", "<br>")

    with tab_a:
        st.markdown(
            f'<div class="answer-card answer-a">'
            f'<div class="answer-text">{escaped_a}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    with tab_b:
        st.markdown(
            f'<div class="answer-card answer-b">'
            f'<div class="answer-text">{escaped_b}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown('<div class="vote-section-label">Ihre Bewertung:</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="small")
    with col1:
        if st.button("✅ Antwort A ist besser", key=f"vote_a_{idx}", use_container_width=True):
            _record_vote(session_state, "A")
            session_state._scroll_top = True
            st.rerun()
    with col2:
        if st.button("✅ Antwort B ist besser", key=f"vote_b_{idx}", use_container_width=True):
            _record_vote(session_state, "B")
            session_state._scroll_top = True
            st.rerun()

    col3, col4 = st.columns(2, gap="small")
    with col3:
        if st.button("🤝 Beide gleich gut", key=f"vote_tie_good_{idx}", use_container_width=True):
            _record_vote(session_state, "TIE_GOOD")
            session_state._scroll_top = True
            st.rerun()
    with col4:
        if st.button("👎 Beide unzureichend", key=f"vote_tie_bad_{idx}", use_container_width=True):
            _record_vote(session_state, "TIE_BAD")
            session_state._scroll_top = True
            st.rerun()


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

    st.download_button(
        label="📥  Ergebnisse als JSON herunterladen",
        data=json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        file_name=f"study_results_{session_state.user_id[:8]}.json",
        mime="application/json",
        use_container_width=True,
    )

    with st.expander("📦 Erhobene Daten (Verifikation)"):
        st.json(payload, expanded=True)

    st.caption(
        "ℹ️ Der JSON-Block dient der Entwicklungsverifikation und "
        "wird entfernt, sobald die Datenbank angebunden ist."
    )


def render_study_view(session_state) -> None:
    if session_state.view == "onboarding":
        _render_onboarding(session_state)
    elif session_state.view == "pre_questionnaire":
        render_pre_questionnaire()
    elif session_state.view == "evaluation":
        _render_evaluation(session_state)
    elif session_state.view == "post_questionnaire":
        render_post_questionnaire()
    elif session_state.view == "outro":
        _render_outro(session_state)