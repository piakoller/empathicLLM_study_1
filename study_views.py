"""Streamlit view rendering for the Phase I user study."""

import datetime
import html as html_module
import json
import uuid

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
            "timestamp": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
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

        Sie werden **{num_questions} Patientenfragen** zum Thema PSMA-gerichtete
        Theranostik bei Prostatakrebs sehen. Zu jeder Frage erhalten Sie
        zwei Antworten in separaten Tabs.

        Ihre Aufgabe: **Wählen Sie die Antwort, die Sie für hilfreicher,
        genauer und angemessener halten** – oder geben Sie an, dass beide
        gleich gut bzw. unzureichend sind.
        
        **Hinweis:** Die Antworten sind lediglich Vorschläge. Wenn Sie weitere Fragen haben, konsultieren Sie bitte Ihren Arzt.
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
        options=[">35", "36–45", "46–55", "56–65", "66–75", "76-85", "86+"],
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
            "started_at": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
        }
        session_state.mock_data = load_questions()
        session_state.question_idx = 0
        session_state.results = []
        session_state.view = "pre_questionnaire"
        session_state.needs_db_save = True
        _request_scroll_to_top(session_state)
        st.rerun()
    _consume_scroll_to_top(session_state)


@st.dialog("📝 Antwort A")
def show_answer_a(text: str):
    st.markdown(
        f'<div class="answer-card answer-a">'
        f'<div class="answer-text">{text}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.button("❌ Schliessen", use_container_width=True, key="close_a"):
        st.rerun()

@st.dialog("📝 Antwort B")
def show_answer_b(text: str):
    st.markdown(
        f'<div class="answer-card answer-b">'
        f'<div class="answer-text">{text}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.button("❌ Schliessen", use_container_width=True, key="close_b"):
        st.rerun()


def _render_evaluation(session_state) -> None:
    items = session_state.mock_data
    idx = session_state.question_idx
    item = items[idx]
    total = len(items)

    if session_state.question_start_time is None:
        session_state.question_start_time = datetime.datetime.now(datetime.timezone.utc)

    progress_fraction = idx / total
    st.progress(progress_fraction, text=f"Frage {idx + 1} von {total}")

    escaped_a = html_module.escape(item["answer_a_text"]).replace("\n", "<br>")
    escaped_b = html_module.escape(item["answer_b_text"]).replace("\n", "<br>")

    st.markdown(
        f"""
        <div class="study-header">
            <p class="header-label">Die Patientenfrage</p>
            <h1>{item["patient_query"]}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    colA, colB = st.columns(2)
    with colA:
        if st.button("🔍 Antwort A", use_container_width=True, key=f"btn_read_a_{idx}"):
            show_answer_a(escaped_a)
    with colB:
        if st.button("🔍 Antwort B", use_container_width=True, key=f"btn_read_b_{idx}"):
            show_answer_b(escaped_b)

    st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)
    st.markdown('<div style="font-weight: bold; font-size: 1.1em; margin-bottom: 0.5rem; text-align: center;">Ihre Bewertung:</div>', unsafe_allow_html=True)

    col_vote1, col_vote2 = st.columns(2, gap="small")
    with col_vote1:
        if st.button("✅ Antwort A\nist besser", key=f"vote_a_{idx}", use_container_width=True):
            _record_vote(session_state, "A")
            st.rerun()
    with col_vote2:
        if st.button("✅ Antwort B\nist besser", key=f"vote_b_{idx}", use_container_width=True):
            _record_vote(session_state, "B")
            st.rerun()

    col_tie1, col_tie2 = st.columns(2, gap="small")
    with col_tie1:
        if st.button("🤝 Beide gleich\ngut", key=f"vote_tie_good_{idx}", use_container_width=True):
            _record_vote(session_state, "TIE_GOOD")
            st.rerun()
    with col_tie2:
        if st.button("👎 Beide unzureichend", key=f"vote_tie_bad_{idx}", use_container_width=True):
            _record_vote(session_state, "TIE_BAD")
            st.rerun()

    components.html(
        """
        <script>
        // Force re-render: UUID_PLACEHOLDER
        const parent = window.parent.document;
        if (!parent.getElementById("custom-btn-styles")) {
            const style = parent.createElement("style");
            style.id = "custom-btn-styles";
            style.innerHTML = `
                button.btn-a-custom {
                    background-color: #e0f2fe !important;
                    border-color: #0284c7 !important;
                    color: #0c4a6e !important;
                }
                button.btn-a-custom:hover {
                    background-color: #bae6fd !important;
                }
                button.btn-b-custom {
                    background-color: #f3e8ff !important;
                    border-color: #9333ea !important;
                    color: #581c87 !important;
                }
                button.btn-b-custom:hover {
                    background-color: #e9d5ff !important;
                }
            `;
            parent.head.appendChild(style);
        }
        
        const buttons = parent.querySelectorAll('button');
        buttons.forEach(btn => {
            const text = btn.innerText;
            if (text.includes("Antwort A")) {
                btn.classList.add("btn-a-custom");
            }
            if (text.includes("Antwort B")) {
                btn.classList.add("btn-b-custom");
            }
        });
        </script>
        """.replace("UUID_PLACEHOLDER", str(uuid.uuid4())),
        height=0,
    )

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