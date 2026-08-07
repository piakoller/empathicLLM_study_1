"""Rendered pre- and post-study questionnaire views."""

import uuid
import streamlit as st

from questionnaire_data import build_likert_metadata, load_questionnaire_data, scroll_to_top


_DATA = load_questionnaire_data()
_LIKERT_LABELS, _LIKERT_VALUES = build_likert_metadata(_DATA)


def _request_scroll_to_top() -> None:
    st.session_state.scroll_to_top_next_render = True


def _consume_scroll_to_top() -> None:
    if st.session_state.get("scroll_to_top_next_render"):
        st.session_state.scroll_to_top_next_render = False
        scroll_to_top(str(uuid.uuid4()))


def _show_checkmark_animation(storage_key: str):
    if st.session_state.get(f"just_answered_{storage_key}"):
        unique_id = uuid.uuid4().hex
        st.markdown(
            f"""
            <div id="check-{unique_id}" style="position: relative; width: 100%; height: 0; top: 60px; display: flex; justify-content: center; align-items: center; z-index: 999; pointer-events: none;">
                <div style="animation: fadeOutCheck 1.5s forwards; font-size: 6rem; filter: drop-shadow(0px 4px 10px rgba(0,0,0,0.15));">
                    ✅
                </div>
            </div>
            <style>
            @keyframes fadeOutCheck {{
                0% {{ opacity: 0; }}
                20% {{ opacity: 1; }}
                70% {{ opacity: 1; }}
                100% {{ opacity: 0; display: none; }}
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.session_state[f"just_answered_{storage_key}"] = False


def _render_likert_section(sections: list[dict], storage_key: str) -> dict | None:
    """Render all Likert sections and collect answers."""

    # Keys that are only meaningful for patients (emotional/mood state items)
    _PATIENT_ONLY_KEYS = {
        "pre_calm", "pre_tense", "pre_worried", "pre_relaxed",
        "pre_uneasy", "pre_confident", "pre_overwhelmed",
        "post_calm", "post_tense", "post_uneasy",
        "post_confident", "post_overwhelmed",
        "post_recommend",
    }

    flat_items: list[dict] = []
    is_patient = st.session_state.get("role") == "Patient:in"
    for sec in sections:
        for item in sec["items"]:
            # Emotional state & recommendation questions only shown to patients
            if item["key"] in _PATIENT_ONLY_KEYS and not is_patient:
                continue

            flat_items.append(
                {
                    "section": sec["section"],
                    "description": sec.get("description", ""),
                    "key": item["key"],
                    "label": item["label"],
                }
            )

    if not flat_items:
        return None

    cursor_key = f"{storage_key}_cursor"
    completion_key = f"{storage_key}_completed"

    if cursor_key not in st.session_state:
        st.session_state[cursor_key] = 0
        _request_scroll_to_top()
        
    if storage_key not in st.session_state:
        st.session_state[storage_key] = {}

    total_items = len(flat_items)
    raw_idx = int(st.session_state[cursor_key])
    if raw_idx >= total_items:
        current_idx = total_items
    else:
        current_idx = max(0, min(raw_idx, total_items - 1))
    st.session_state[cursor_key] = current_idx

    completion_key = f"{storage_key}_completed"
    completed = bool(st.session_state.get(completion_key, False))

    if current_idx >= total_items:
        completed = True
        st.session_state[completion_key] = True

    if completed:
        scroll_to_top()
        _show_checkmark_animation(storage_key)
        answered_count = sum(
            1 for item in flat_items if st.session_state[storage_key].get(item["key"]) is not None
        )
        st.progress(
            answered_count / total_items,
            text=f"Fragebogen: {answered_count}/{total_items} beantwortet",
        )
        st.markdown("Vielen Dank! Sie haben alle Fragen in diesem Abschnitt beantwortet. Bitte klicken Sie unten, um fortzufahren.")
        return _collect_answers(flat_items, storage_key)

    answered_count = sum(
        1 for item in flat_items if st.session_state[storage_key].get(item["key"]) is not None
    )

    current_item = flat_items[current_idx]
    _show_checkmark_animation(storage_key)

    st.markdown(
        f'<div style="animation: softFadeIn 0.6s ease-out forwards;">'
        f'<div class="caption-text" style="margin-bottom: 0.5rem;">Frage {current_idx + 1} von {total_items}</div>'
        f'<div class="study-header" style="margin-top: 1.2rem; padding: 1.2rem; margin-bottom: 1.5rem;">'
        f'<div class="question-text">{current_item["label"]}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    current_val = st.session_state[storage_key].get(current_item["key"])
    for value, label in zip(_LIKERT_VALUES, _LIKERT_LABELS):
        if st.button(
            str(label),
            key=f"likert_{storage_key}_{current_item['key']}_{value}",
                type="primary" if current_val == value else "secondary",
                use_container_width=True,
            ):
                st.session_state[storage_key][current_item["key"]] = value
                st.session_state[f"just_answered_{storage_key}"] = True
                if current_idx < total_items - 1:
                    st.session_state[cursor_key] = current_idx + 1
                    st.session_state[completion_key] = False
                else:
                    st.session_state[cursor_key] = total_items
                    st.session_state[completion_key] = True
                _request_scroll_to_top()
                st.rerun()

    st.divider()
    if st.button(
        "← Zurück",
        key=f"nav_prev_{storage_key}",
        use_container_width=True,
        disabled=current_idx == 0,
    ):
        st.session_state[cursor_key] = current_idx - 1
        _request_scroll_to_top()
        st.rerun()
    st.caption("Antworten werden automatisch gespeichert. Vorwärts geht es nach der Auswahl, zurück nur mit Zurück.")

    return _collect_answers(flat_items, storage_key)


def _collect_answers(flat_items: list[dict], storage_key: str) -> dict | None:
    answers: dict[str, int] = {}
    all_answered = True
    for item in flat_items:
        value = st.session_state[storage_key].get(item["key"])
        if value is None:
            all_answered = False
            continue
        answers[item["key"]] = int(value)

    return answers if all_answered else None


def _scale_legend() -> str:
    parts = [f"{v}\u00a0=\u00a0{lbl.split('\u2013', 1)[-1].strip()}" for v, lbl in zip(_LIKERT_VALUES, _LIKERT_LABELS)]
    return "&nbsp;·&nbsp;".join(parts)


def render_pre_questionnaire() -> None:
    cfg = _DATA["pre"]

    answers = _render_likert_section(cfg["sections"], "pre_questionnaire")

    if answers is not None:
        st.divider()
        if st.button(cfg["button_label"], type="primary", use_container_width=True, key="pre_submit"):
            st.session_state.pre_questionnaire = answers
            st.session_state.view = "evaluation"
            st.session_state.needs_db_save = True
            _request_scroll_to_top()
            st.rerun()

    _consume_scroll_to_top()


def render_post_questionnaire() -> None:
    cfg = _DATA["post"]

    answers = _render_likert_section(cfg["sections"], "post_questionnaire")

    if answers is not None:
        st.divider()
        if st.button(cfg["button_label"], type="primary", use_container_width=True, key="post_submit"):
            st.session_state.post_questionnaire = answers
            st.session_state.view = "outro"
            st.session_state.needs_db_save = True
            _request_scroll_to_top()
            st.rerun()

    _consume_scroll_to_top()