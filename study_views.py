"""Streamlit view rendering for the Monadic (Single-Answer per Page) Phase I user study."""

import datetime
import html
import html as html_module
import json
import uuid
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

from questionnaire import render_post_questionnaire, render_pre_questionnaire
from study_data import load_questions, n_questions
from study_persistence import participant_count, save_current_progress, study_date
from questionnaire_data import scroll_to_top


# Participant information, disclaimer and debrief: docs/STUDY_START_TEXTS_DRAFT.md.
CONTACT_TEXT = """Fragen zur Studie: Pia Koller · [pia.koller@unibe.ch](mailto:pia.koller@unibe.ch)

Fragen zu Ihrer Behandlung: Ihr Behandlungsteam der Nuklearmedizin."""
CONTACT_MARKDOWN = "#### ✉️ Kontakt\n" + CONTACT_TEXT

# Decision question after each answer (stored as decision_code).
# "zur", not "für": the question must not presume the decision.
PATIENT_DECISION_QUESTION = "Wie wirkt diese Antwort auf Ihre Entscheidung zur PSMA-Therapie?"
PATIENT_DECISION_OPTIONS = {          # label -> code: +2 much more certain … -2 much less certain
    "Ich fühle mich deutlich sicherer.": 2,
    "Ich fühle mich etwas sicherer.": 1,
    "Unverändert.": 0,
    "Ich fühle mich etwas unsicherer.": -1,
    "Ich fühle mich deutlich unsicherer.": -2,
}
DOCTOR_DECISION_QUESTION = "Würden Sie diese Antwort einer Patientin oder einem Patienten so mitgeben?"
DOCTOR_DECISION_OPTIONS = {
    "Ja, so wie sie ist.": "as_is",
    "Ja, aber mit Änderungen.": "with_changes",
    "Nein.": "no",
}

UNCERTAIN_HINT = ("Wenn Sie nach dem Lesen unsicher sind, sprechen Sie bitte mit Ihrem Behandlungsteam "
                  "der Nuklearmedizin. Die Texte in dieser Studie ersetzen kein ärztliches Gespräch.")


def left_uncertain(session_state) -> bool:
    """True if the patient rated at least two answers as making them less certain, or answered
    any SURE item with "Nein" after the answers (SURE score below 4 = decisional conflict)."""
    less_certain = sum(1 for r in session_state.results
                       if isinstance(r.get("ratings", {}).get("decision_code"), int)
                       and r["ratings"]["decision_code"] < 0)
    post = session_state.post_questionnaire or {}
    return less_certain >= 2 or any(post.get(f"post_sure_{k}") == 0 for k in "sure")


ANSWER_DISCLAIMER = "Computer-generierter Text – kann Fehler enthalten. Keine ärztliche Auskunft."

# The facts must be confirmed by the nuclear medicine physicians before the pilot.
DEBRIEF_MARKDOWN = """Die Antworten, die Sie gelesen haben, stammen von einem Computerprogramm. Wir haben
verschiedene Arten verglichen, solche Antworten zu schreiben. Einige Antworten können
ungenau oder unvollständig gewesen sein.

#### Wichtige Informationen zur PSMA-Therapie am Inselspital
* Die Therapie findet stationär statt. Sie bleiben etwa 3 Tage im Spital.
* Während des Aufenthalts dürfen Sie die Station nicht verlassen und keinen Besuch empfangen.
* Die Therapie wird in Zyklen wiederholt, meist alle 6–8 Wochen.
* Bei Prostatakrebs mit Ablegern ist eine Heilung meist nicht zu erwarten. Die Therapie
  kann aber das Wachstum bremsen und Beschwerden lindern.
* Wie Sie sich nach der Entlassung zu Hause verhalten sollen, erklärt Ihnen Ihr
  Behandlungsteam vor dem Austritt. Sie erhalten dazu ein Merkblatt.

Wenn beim Lesen Fragen oder Sorgen entstanden sind, sprechen Sie bitte mit Ihrem
Behandlungsteam der Nuklearmedizin."""


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
            "condition_key": item.get("condition", "unknown"),
            "ratings": ratings,
            "response_time_s": response_time_s,
            "timestamp": study_date(),
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
            <div class="header-title">Herzlich willkommen!</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    num_questions = n_questions()
    # About 1–1.5 minutes per answer, questionnaires included: 10 answers give
    # 10–15 minutes, the figure printed on flyer and poster (27 Oct 2026).
    minutes_low, minutes_high = round(num_questions * 1.0), round(num_questions * 1.5)
    # The essentials stay visible; the details open on demand, so the page is
    # short on a phone but nothing from the participant information is dropped.
    st.markdown(
            f"""
            Wir untersuchen, wie verständlich und hilfreich Antworten eines Computerprogramms
            auf Fragen zur **PSMA-Therapie bei Prostatakrebs** sind. Sie lesen
            **{num_questions} kurze Antworten** und wählen jeweils aus, wie sie auf Sie wirken.
            Dauer: etwa **{minutes_low}–{minutes_high} Minuten**.

            * **Die Texte können Fehler enthalten** und sind keine ärztliche Auskunft.
            * **Freiwillig und anonym:** Sie können jederzeit aufhören. Wir fragen nicht nach Ihrem Namen.
            """
    )

    with st.expander("💡 Ihre Aufgabe"):
        st.markdown(
            """
            1. **Lesen Sie jede Antwort aufmerksam durch.**
            2. **Wählen Sie mit einem Klick diejenige Aussage aus**, die Ihr Gefühl und Ihre Wahrnehmung beim Lesen am besten beschreibt.

            * **Kein Zeitdruck:** Sie können sich so viel Zeit nehmen, wie Sie möchten.
            * **Keine falschen Antworten:** Es zählt ausschliesslich Ihre persönliche Erfahrung.

            Teilnehmen können Patientinnen und Patienten sowie Ärztinnen und Ärzte; Ihre Rolle wählen Sie im nächsten Schritt.
            """
        )
    with st.expander("⚠️ Hinweise zu den Texten"):
        st.markdown(
            """
            * Die Texte wurden von einem Computerprogramm (einem sogenannten Sprachmodell) geschrieben
              und können Fehler enthalten. Richten Sie Ihre Behandlung nicht nach diesen Texten.
            * Fragen zu Ihrer eigenen Behandlung beantwortet Ihr Behandlungsteam der Nuklearmedizin.
            * Am Ende erhalten Sie die wichtigsten Informationen zur PSMA-Therapie am Inselspital.
            """
        )
    with st.expander("🔒 Freiwilligkeit und Datenschutz"):
        st.markdown(
            """
            * Die Teilnahme ist freiwillig. Ob Sie teilnehmen, hat keinen Einfluss auf Ihre Behandlung.
            * Sie können jederzeit aufhören, ohne Angabe von Gründen.
            * Wir fragen nicht nach Ihrem Namen, Ihrer E-Mail-Adresse oder Ihrem Geburtsdatum.
              Ihre Antworten können Ihnen nicht zugeordnet werden.
            * Die Studie läuft über einen externen Anbieter (Streamlit) mit Servern in den USA.
              Dieser verarbeitet technisch Ihre IP-Adresse. Wir speichern sie nicht und erhalten sie nicht.
            * Weil die Daten anonym sind, können wir Ihre Antworten nachträglich nicht löschen.
              Was Sie bis zu einem Abbruch eingegeben haben, kann deshalb in die Auswertung eingehen.
            """
        )
    with st.expander("✉️ Kontakt"):
        st.markdown(CONTACT_TEXT)

    st.markdown("Mit «Weiter» bestätigen Sie, dass Sie diese Informationen zur Kenntnis genommen haben und teilnehmen möchten.")

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
            "started_at": study_date(),
        }
        session_state.role = role
        # Counted before this participant's own record is saved (needs_db_save below).
        session_state.mock_data = load_questions(session_state.user_id, slot=participant_count(role, session_state.get("test_run", False)))
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
        <div class="study-header question-header">
            <p class="header-label">Die Frage</p>
            <h1 style="font-size: 1.25em; line-height: 1.4;">{item["patient_query"]}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # The answer as its own white card, matching the flyer panel. Rendered as
    # explicit paragraphs rather than through st.container(border=True): the
    # bordered container's wrapper carries no stable class to style, and the
    # answers contain no markdown syntax (checked across all 40 texts: no #, *,
    # _, backticks, pipes or raw HTML), so escaping and splitting on the blank
    # line reproduces them exactly.
    _paras = "".join(
        f"<p>{html.escape(par.strip())}</p>"
        for par in item["answer_text"].split("\n\n") if par.strip()
    )
    st.caption(f"ℹ️ {ANSWER_DISCLAIMER}")
    st.markdown(f'<div class="answer-card">{_paras}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Welche Aussage beschreibt Ihre Wahrnehmung dieser Antwort am besten?")
    st.markdown("Bitte wählen Sie **genau eine Aussage** aus, die am ehesten zutrifft:")

    is_doctor = session_state.get("role") == "Arzt/Ärztin"

    if is_doctor:
        statement_options = [
            "A) Medizinisch korrekt, empathisch und hervorragend für das Patientengespräch geeignet.",
            "B) Medizinisch präzise und sachlich, aber klinisch eher kühl oder distanziert formuliert.",
            "C) Sprachlich zu komplex oder mit zu viel Fachjargon für Laien-Patienten besetzt.",
            "D) Medizinisch bedenklich, unvollständig oder potenziell verunsichernd für den Patienten.",
        ]
    else:
        statement_options = [
            "A) Die Antwort informiert mich klar, nimmt mir die Sorge und gibt mir ein gutes Gefühl.",
            "B) Die Antwort ist rein sachlich und informativ, wirkt auf mich aber etwas kühl.",
            "C) Die Antwort ist mir zu kompliziert geschrieben und enthält zu viele Fachwörter.",
            "D) Die Antwort verunsichert mich eher oder macht mir Angst vor der Therapie.",
        ]

    selected_statement = st.radio(
        "Ihre Einschätzung:",
        options=statement_options,
        index=None,
        key=f"stmt_{idx}",
        label_visibility="collapsed",
    )

    # Second question: does the answer change the decision? Patients rate their own
    # certainty about the therapy (many are already in it, so "for/against" would not
    # fit); clinicians rate whether they would hand the answer to a patient.
    st.markdown("<br>", unsafe_allow_html=True)
    decision_options = DOCTOR_DECISION_OPTIONS if is_doctor else PATIENT_DECISION_OPTIONS
    st.markdown("### " + (DOCTOR_DECISION_QUESTION if is_doctor else PATIENT_DECISION_QUESTION))
    selected_decision = st.radio(
        "Entscheidung:",
        options=list(decision_options),
        index=None,
        key=f"dec_{idx}",
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Weiter", type="primary", use_container_width=True, key=f"next_{idx}",
                 disabled=not (selected_statement and selected_decision)):
        statement_code = "other"
        if any(term in selected_statement for term in ["informiert mich klar", "hervorragend"]):
            statement_code = "empathic_informative"
        elif "sachlich" in selected_statement:
            statement_code = "clinical_factual"
        elif any(term in selected_statement for term in ["kompliziert", "komplex"]):
            statement_code = "too_complex"
        elif any(term in selected_statement for term in ["verunsichert", "bedenklich"]):
            statement_code = "causes_anxiety"

        ratings_dict = {
            "selected_statement": selected_statement,
            "statement_code": statement_code,
            "decision_answer": selected_decision,
            "decision_code": decision_options[selected_decision],
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

    # Clinicians get the thanks and the contact; the debrief is written for patients.
    if session_state.get("role") != "Arzt/Ärztin":
        # The data are anonymous, so nobody can follow up later: a patient who came out of
        # the study less certain is pointed to the care team here, on screen.
        if left_uncertain(session_state):
            st.warning(UNCERTAIN_HINT)
        st.markdown(DEBRIEF_MARKDOWN)
        st.divider()
    st.markdown(CONTACT_MARKDOWN)
    st.divider()

    if session_state.db_save_status is None:
        save_current_progress(session_state)

    # Participants see a neutral line either way; the technical detail of a failed
    # save goes to the server log only (study_persistence.save_results).
    success, _ = session_state.db_save_status
    if success:
        st.success("Ihre Antworten wurden gespeichert. Sie können dieses Fenster jetzt schliessen.")
    else:
        st.info("Sie können dieses Fenster jetzt schliessen.")


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