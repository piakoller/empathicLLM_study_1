"""Rendered pre- and post-study questionnaire views."""

import streamlit as st

from questionnaire_data import build_likert_metadata, load_questionnaire_data, scroll_to_top


_DATA = load_questionnaire_data()
_LIKERT_LABELS, _LIKERT_VALUES = build_likert_metadata(_DATA)


def _render_likert_section(sections: list[dict], storage_key: str) -> dict | None:
    """Render all Likert sections and collect answers."""
    flat_items: list[dict] = []
    for sec in sections:
        for item in sec["items"]:
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

    scroll_to_top()

    cursor_key = f"{storage_key}_cursor"
    if cursor_key not in st.session_state:
        st.session_state[cursor_key] = 0

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
        answered_count = sum(
            1 for item in flat_items if st.session_state[storage_key].get(item["key"]) is not None
        )
        st.progress(
            answered_count / total_items,
            text=f"Fragebogen: {answered_count}/{total_items} beantwortet",
        )
        st.markdown("Sie haben alle Fragen beantwortet. Bitte fahren Sie nun mit der Studie fort.")
        return _collect_answers(flat_items, storage_key)

    answered_count = sum(
        1 for item in flat_items if st.session_state[storage_key].get(item["key"]) is not None
    )
    st.progress(
        answered_count / total_items,
        text=f"Fragebogen: {answered_count}/{total_items} beantwortet",
    )

    nav_col1, nav_col2 = st.columns([1, 2], gap="small")
    with nav_col1:
        if st.button(
            "← Zuruck",
            key=f"nav_prev_{storage_key}",
            use_container_width=True,
            disabled=current_idx == 0,
        ):
            st.session_state[cursor_key] = current_idx - 1
            st.rerun()
    with nav_col2:
        st.caption("Antworten werden automatisch gespeichert. Vorwärts geht es nach der Auswahl, zurück nur mit Zuruck.")

    current_item = flat_items[current_idx]
    desc_html = (
        f' <span class="section-desc">{current_item["description"]}</span>'
        if current_item.get("description")
        else ""
    )
    st.markdown(
        f'<div class="questionnaire-section">'
        f'<span class="section-title">{current_item["section"]}</span>'
        f'{desc_html}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**Frage {current_idx + 1} von {total_items}**")
    st.markdown(f"**{current_item['label']}**")

    current_val = st.session_state[storage_key].get(current_item["key"])
    cols = st.columns(len(_LIKERT_VALUES), gap="small")
    for col, value in zip(cols, _LIKERT_VALUES):
        with col:
            if st.button(
                str(value),
                key=f"likert_{storage_key}_{current_item['key']}_{value}",
                type="primary" if current_val == value else "secondary",
                use_container_width=True,
            ):
                st.session_state[storage_key][current_item["key"]] = value
                if current_idx < total_items - 1:
                    st.session_state[cursor_key] = current_idx + 1
                    st.session_state[completion_key] = False
                else:
                    st.session_state[cursor_key] = total_items
                    st.session_state[completion_key] = True
                st.rerun()

    st.markdown(
        """
        <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #666; margin-top: -10px; margin-bottom: 20px; padding: 0 5px;">
            <span>1 – Gar nicht</span>
            <span>5 – Sehr</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    scroll_to_top()
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
            st.session_state.needs_db_save = True
            st.rerun()


def render_post_questionnaire() -> None:
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
            st.session_state.needs_db_save = True
            st.rerun()