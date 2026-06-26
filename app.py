"""
Phase I User Study – 2AFC Head-to-Head Evaluation (Mobile-First)
================================================================
A Streamlit application for evaluating Large Language Model (LLM)
responses in a clinical (theranostics / PSMA) context using a
Two-Alternative Forced Choice (2AFC) paradigm.

Mobile-first design optimized for smartphone access via QR code.
Uses st.tabs to prevent order bias on small screens.

Run with:
    streamlit run app.py

To load your own questions, edit ``questions.json``. Each item needs:
    {
      "item_id":        "ITEM_001",
      "patient_query":  "Die Patientenfrage …",
      "answer_a_text":  "Antwort A …",
      "answer_b_text":  "Antwort B …"
    }
"""

import streamlit as st
import datetime
import json
import pathlib
import os
import uuid
import html as html_module
import pymongo


# ──────────────────────────────────────────────────────────────
# 1. PAGE CONFIGURATION (Mobile-First)
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Phase-I-Nutzerstudie – LLM-Evaluation",
    page_icon="🩺",
    layout="wide",
)


# ──────────────────────────────────────────────────────────────
# 2. LOAD EXTERNAL STYLESHEET
# ──────────────────────────────────────────────────────────────
_STYLES_PATH = pathlib.Path(__file__).parent / "styles.css"

def _load_css() -> None:
    """Read the external CSS file and inject it into the Streamlit page."""
    css_text = _STYLES_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)

_load_css()


# ──────────────────────────────────────────────────────────────
# 3. EVALUATION DATA (loaded from external JSON)
# ──────────────────────────────────────────────────────────────
_QUESTIONS_PATH = pathlib.Path(__file__).parent / "questions.json"

def load_questions() -> list[dict]:
    """
    Load evaluation items from the external JSON file.

    The file should be a JSON **array** of objects.  Each object must
    contain at least the following keys:

        item_id        – unique identifier string (e.g. "ITEM_001")
        patient_query  – the clinical question shown to the participant
        answer_a_text  – first model answer (plain text, newlines ok)
        answer_b_text  – second model answer

    Simply replace ``questions.json`` with your own data; no code changes
    are needed as long as the key names stay the same.
    """
    with open(_QUESTIONS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# ──────────────────────────────────────────────────────────────
# 3b. DATABASE PERSISTENCE (MongoDB with local JSON fallback)
# ──────────────────────────────────────────────────────────────
def save_results(payload: dict) -> tuple[bool, str]:
    """
    Attempt to save *payload* to MongoDB.
    If the URI is not configured or the upload fails, fall back to
    appending to a local ``fallback_results.json`` file.
    Returns ``(success, message)``.
    """
    # 1. Attempt MongoDB upload
    mongo_uri = st.secrets.get("MONGODB_URI") or os.environ.get("MONGODB_URI")

    if mongo_uri and "<db_password>" not in mongo_uri and "example.mongodb.net" not in mongo_uri:
        try:
            client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=4000)
            db = client.get_database("empathicLLM_study")
            collection = db.get_collection("study_1")
            collection.insert_one(payload)
            print("\n" + "="*80)
            print("[DB SUCCESS] Data successfully saved to MongoDB (empathicLLM_study.study_1)")
            print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
            print("="*80 + "\n")
            return True, "Daten erfolgreich in MongoDB gespeichert!"
        except Exception as e:
            err_msg = str(e)
    else:
        err_msg = "MongoDB-Verbindungszeichenfolge nicht konfiguriert."

    # 2. Local fallback
    try:
        fallback_path = pathlib.Path(__file__).parent / "fallback_results.json"

        existing_data: list = []
        if fallback_path.exists():
            try:
                with open(fallback_path, "r", encoding="utf-8") as fh:
                    existing_data = json.load(fh)
                    if not isinstance(existing_data, list):
                        existing_data = []
            except Exception:
                existing_data = []

        existing_data.append(payload)
        with open(fallback_path, "w", encoding="utf-8") as fh:
            json.dump(existing_data, fh, indent=2, ensure_ascii=False, default=str)

        print("\n" + "!"*80)
        print(f"[DB WARNING] MongoDB connection failed. Saved payload locally to 'fallback_results.json'.")
        print(f"Error detail: {err_msg}")
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        print("!"*80 + "\n")

        return False, (
            f"MongoDB nicht verbunden ({err_msg}). "
            "Daten wurden lokal in 'fallback_results.json' gesichert."
        )
    except Exception as local_err:
        print("\n" + "X"*80)
        print("[DB ERROR] CRITICAL: Failed to save to MongoDB AND local fallback failed.")
        print(f"MongoDB Error: {err_msg}")
        print(f"Local Error: {local_err}")
        print("X"*80 + "\n")
        return False, f"Speicherfehler: MongoDB – {err_msg} | Lokal – {local_err}"


# ──────────────────────────────────────────────────────────────
# 4. SESSION STATE INITIALISATION
# ──────────────────────────────────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "view" not in st.session_state:
    st.session_state.view = "onboarding"       # onboarding → pre_questionnaire → evaluation → post_questionnaire → outro
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


# ──────────────────────────────────────────────────────────────
# 4b. AUTO-PERSISTENCE ON STATE CHANGES
# ──────────────────────────────────────────────────────────────
def build_current_payload() -> dict:
    """Constructs the current state payload for the user session."""
    payload = {
        "user_id": st.session_state.user_id,
        "demographics": st.session_state.demographics,
        "pre_questionnaire": st.session_state.pre_questionnaire,
        "votes": st.session_state.results,
        "post_questionnaire": st.session_state.post_questionnaire,
        "status": st.session_state.view,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_items_voted": len(st.session_state.results),
    }
    if st.session_state.view == "outro":
        payload["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload["status"] = "completed"
    return payload


def save_current_progress() -> None:
    """Helper to build and save/update the current state of progress to the database."""
    payload = build_current_payload()
    success, msg = save_results(payload)
    st.session_state.db_save_status = (success, msg)


if st.session_state.needs_db_save:
    st.session_state.needs_db_save = False
    save_current_progress()


# ──────────────────────────────────────────────────────────────
# 5. HELPER – record a vote & advance
# ──────────────────────────────────────────────────────────────
def _record_vote(vote_label: str) -> None:
    """Store the vote for the current item including response time, then advance."""
    item = st.session_state.mock_data[st.session_state.question_idx]

    # Calculate response time (seconds)
    response_time_s = None
    if st.session_state.question_start_time is not None:
        delta = (
            datetime.datetime.now(datetime.timezone.utc)
            - st.session_state.question_start_time
        )
        response_time_s = round(delta.total_seconds(), 2)

    st.session_state.results.append(
        {
            "user_id": st.session_state.user_id,
            "item_id": item["item_id"],
            "vote": vote_label,
            "response_time_s": response_time_s,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    )

    next_idx = st.session_state.question_idx + 1
    if next_idx >= len(st.session_state.mock_data):
        # All evaluation questions answered → go to post-questionnaire
        # (Change to "outro" if you want to skip the post-questionnaire.)
        st.session_state.view = "post_questionnaire"
    else:
        st.session_state.question_idx = next_idx

    # Reset start time so the next question gets a fresh timestamp
    st.session_state.question_start_time = None

    # Request a DB save on the next rerun
    st.session_state.needs_db_save = True


# ══════════════════════════════════════════════════════════════
# 6. VIEW RENDERING
# ══════════════════════════════════════════════════════════════


# ── VIEW 1: ONBOARDING ────────────────────────────────────────
def _render_onboarding() -> None:
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

        Sie werden **11 Patientenfragen** zum Thema PSMA-gerichtete
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

    # ── Single-column layout for mobile ──
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

    st.markdown("")  # visual spacer

    if st.button("🚀  Studie starten", type="primary", use_container_width=True):
        # Validation
        if not role or not age or not gender:
            st.warning("Bitte füllen Sie alle Felder aus, bevor Sie beginnen.")
            return

        st.session_state.demographics = {
            "user_id": st.session_state.user_id,
            "role": role,
            "age_range": age,
            "gender": gender,
            "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        st.session_state.mock_data = load_questions()
        st.session_state.question_idx = 0
        st.session_state.results = []
        # Go to pre-questionnaire first.
        # (Change to "evaluation" to skip the pre-questionnaire.)
        st.session_state.view = "pre_questionnaire"
        st.session_state.needs_db_save = True
        st.rerun()


# ── VIEW 2: EVALUATION (Tabbed – prevents order bias) ────────
def _render_evaluation() -> None:
    items = st.session_state.mock_data
    idx = st.session_state.question_idx
    item = items[idx]
    total = len(items)

    # Start the response-time clock for this question (set only once)
    if st.session_state.question_start_time is None:
        st.session_state.question_start_time = datetime.datetime.now(
            datetime.timezone.utc
        )

    # ── Progress indicator ──
    progress_fraction = idx / total
    st.progress(progress_fraction, text=f"Frage {idx + 1} von {total}")

    # ── Patient query as header ──
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

    # ── Tabbed answer view (prevents order bias on small screens) ──
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

    # ── Voting action bar (2 × 2 grid, compact for mobile) ──
    st.markdown(
        '<div class="vote-section-label">Ihre Bewertung:</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="small")
    with col1:
        if st.button(
            "✅ Antwort A ist besser",
            key=f"vote_a_{idx}",
            use_container_width=True,
        ):
            _record_vote("A")
            st.rerun()
    with col2:
        if st.button(
            "✅ Antwort B ist besser",
            key=f"vote_b_{idx}",
            use_container_width=True,
        ):
            _record_vote("B")
            st.rerun()

    col3, col4 = st.columns(2, gap="small")
    with col3:
        if st.button(
            "🤝 Beide gleich gut",
            key=f"vote_tie_good_{idx}",
            use_container_width=True,
        ):
            _record_vote("TIE_GOOD")
            st.rerun()
    with col4:
        if st.button(
            "👎 Beide unzureichend",
            key=f"vote_tie_bad_{idx}",
            use_container_width=True,
        ):
            _record_vote("TIE_BAD")
            st.rerun()


# ──────────────────────────────────────────────────────────────
# QUESTIONNAIRE VIEWS (pre & post – loaded from separate module)
# ──────────────────────────────────────────────────────────────
from questionnaire import render_pre_questionnaire, render_post_questionnaire


# ── VIEW 3: OUTRO (Thank-You Screen) ─────────────────────────
def _render_outro() -> None:
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

    # ── Build final payload ──
    payload = build_current_payload()

    # ── Persist to DB (if not already done, though it should be) ──
    if st.session_state.db_save_status is None:
        save_current_progress()

    success, msg = st.session_state.db_save_status
    if success:
        st.success(f"✅ {msg}")
    else:
        st.warning(f"⚠️ {msg}")

    # ── Download button so researcher can grab results locally ──
    st.download_button(
        label="📥  Ergebnisse als JSON herunterladen",
        data=json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        file_name=f"study_results_{st.session_state.user_id[:8]}.json",
        mime="application/json",
        use_container_width=True,
    )

    with st.expander("📦 Erhobene Daten (Verifikation)"):
        st.json(payload, expanded=True)

    st.caption(
        "ℹ️ Der JSON-Block dient der Entwicklungsverifikation und "
        "wird entfernt, sobald die Datenbank angebunden ist."
    )


# ──────────────────────────────────────────────────────────────
# 7. ROUTER
# ──────────────────────────────────────────────────────────────
_VIEWS = {
    "onboarding":         _render_onboarding,
    "pre_questionnaire":  render_pre_questionnaire,
    "evaluation":         _render_evaluation,
    "post_questionnaire": render_post_questionnaire,
    "outro":              _render_outro,
}

_VIEWS[st.session_state.view]()
