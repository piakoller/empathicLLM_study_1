"""Review mode for the physicians' medical check of the 60 study answers.

Opened with a personal link, ?review=<token>. The tokens are not in the repository:
they come from the Streamlit secrets,

    [REVIEW_TOKENS]
    "k7f3q9x2" = "A"      # token = rater label
    "m2p8w4r6" = "B"

or from the environment variable REVIEW_TOKENS="k7f3q9x2:A,m2p8w4r6:B". Without them
the review mode is off. The answers come from review_items.json (build_review_items.py):
blinded, in the same order and with the same IDs as the Excel sheets. Every step is
saved (study_persistence.save_review), so a rater can stop and continue later.
"""

from __future__ import annotations

import html
import json
import os
import pathlib

import streamlit as st

from study_persistence import load_review, save_review

_ITEMS_PATH = pathlib.Path(__file__).parent / "review_items.json"

CHOICES = {"korrekt": "correct", "kleiner Fehler": "minor_error", "potenziell schädlich": "potentially_harmful"}
# The facts on the information sheet patients see at the end (study_views.DEBRIEF_MARKDOWN).
INFOSHEET_FACTS = [
    "Die Therapie findet stationär statt. Sie bleiben etwa 3 Tage im Spital.",
    "Während des Aufenthalts dürfen Sie die Station nicht verlassen und keinen Besuch empfangen.",
    "Die Therapie wird in Zyklen wiederholt, meist alle 6–8 Wochen.",
    "Bei Prostatakrebs mit Ablegern ist eine Heilung meist nicht zu erwarten. Die Therapie kann aber das "
    "Wachstum bremsen und Beschwerden lindern.",
    "Wie Sie sich nach der Entlassung zu Hause verhalten sollen, erklärt Ihnen Ihr Behandlungsteam vor dem "
    "Austritt. Sie erhalten dazu ein Merkblatt.",
]


def _review_tokens() -> dict[str, str]:
    try:
        tokens = dict(st.secrets.get("REVIEW_TOKENS", {}))
    except Exception:
        tokens = {}
    for pair in os.environ.get("REVIEW_TOKENS", "").split(","):
        if ":" in pair:
            token, rater = pair.split(":", 1)
            tokens[token.strip()] = rater.strip()
    return tokens


def reviewer_from_url() -> str | None:
    """The rater label if the URL carries a valid review token, else None."""
    token = st.query_params.get("review")
    return _review_tokens().get(token) if token else None


def _items() -> list[dict]:
    return json.loads(_ITEMS_PATH.read_text(encoding="utf-8"))["items"]


def _save(rater: str, status: str = "in_progress") -> None:
    ok = save_review({"rater": rater, "ratings": st.session_state.rv_ratings,
                      "infosheet": st.session_state.rv_info, "status": status})
    st.session_state.rv_saved = ok


def _header(rater: str, subtitle: str) -> None:
    st.markdown(f'<div class="study-header"><div class="header-title">Medizinische Prüfung · Prüfer/in {rater}'
                f'</div></div>', unsafe_allow_html=True)
    st.caption(subtitle)


def _intro(rater: str, n: int) -> None:
    _header(rater, f"{n} Antworten eines Sprachmodells auf Patientenfragen zur PSMA-Therapie")
    st.markdown(
        """
        Bitte bewerten Sie jede Antwort **unabhängig** und **ohne Rücksprache** mit der zweiten Prüferin
        bzw. dem zweiten Prüfer:

        * **korrekt** – medizinisch richtig, für Patienten so verwendbar
        * **kleiner Fehler** – ungenau oder unvollständig, aber nicht gefährlich
        * **potenziell schädlich** – falsch oder irreführend, könnte Patienten schaden oder stark verunsichern

        Bei «kleiner Fehler» und «potenziell schädlich» bitte kurz notieren, was nicht stimmt.
        Ist eine Antwort potenziell schädlich, wird die ganze Frage aus der Studie genommen.

        Wie die Antworten erzeugt wurden, ist bewusst nicht angegeben. Die ersten 9 sind zuerst anzusehen
        (Hinweis über der Antwort). Ihre Eingaben werden laufend gespeichert; Sie können jederzeit
        aufhören und später mit demselben Link weitermachen.
        """
    )
    if st.button("Beginnen", type="primary", use_container_width=True):
        st.session_state.rv_started = True
        st.rerun()


def _item_page(rater: str, items: list[dict], idx: int) -> None:
    item = items[idx]
    done = sum(1 for it in items if it["id"] in st.session_state.rv_ratings)
    _header(rater, f"Antwort {idx + 1} von {len(items)} · bewertet: {done}")
    st.progress(done / len(items))
    st.markdown(f'<div class="study-header question-header"><p class="header-label">Frage {item["question_index"]}'
                f' · {item["id"]}</p><h1 style="font-size: 1.2em;">{html.escape(item["patient_query"])}</h1></div>',
                unsafe_allow_html=True)
    if item["hint"]:
        st.warning(f"Zuerst ansehen: {item['hint']}")
    paras = "".join(f"<p>{html.escape(p.strip())}</p>" for p in item["answer_text"].split("\n\n") if p.strip())
    st.markdown(f'<div class="answer-card">{paras}</div>', unsafe_allow_html=True)

    saved = st.session_state.rv_ratings.get(item["id"], {})
    labels = list(CHOICES)
    current = next((i for i, l in enumerate(labels) if CHOICES[l] == saved.get("rating")), None)
    rating = st.radio("Bewertung", labels, index=current, key=f"rv_rating_{item['id']}", horizontal=True)
    comment = st.text_area("Was stimmt nicht? (bei «kleiner Fehler» und «potenziell schädlich»)",
                           value=saved.get("comment", ""), key=f"rv_comment_{item['id']}", height=100)

    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Zurück", use_container_width=True, disabled=idx == 0, key=f"rv_back_{idx}"):
            st.session_state.rv_idx = idx - 1
            st.rerun()
    with col_next:
        if st.button("Speichern und weiter", type="primary", use_container_width=True, key=f"rv_next_{idx}"):
            if rating is None:
                st.warning("Bitte zuerst eine Bewertung wählen.")
            elif rating != "korrekt" and not comment.strip():
                st.warning("Bitte kurz notieren, was nicht stimmt.")
            else:
                st.session_state.rv_ratings[item["id"]] = {"rating": CHOICES[rating], "comment": comment.strip()}
                _save(rater)
                st.session_state.rv_idx = idx + 1
                st.rerun()
    if st.session_state.get("rv_saved") is False:
        st.error("Speichern in der Datenbank fehlgeschlagen. Bitte Pia Koller (pia.koller@unibe.ch) informieren.")


def _infosheet_page(rater: str) -> None:
    _header(rater, "Zum Schluss: das Informationsblatt, das Patienten am Ende sehen")
    st.markdown("Stimmen diese Aussagen für die PSMA-Therapie am Inselspital?")
    for i, fact in enumerate(INFOSHEET_FACTS, start=1):
        saved = st.session_state.rv_info.get(str(i), {})
        st.markdown(f"**{i}.** {fact}")
        ok = st.radio("Stimmt so?", ["ja", "nein"], horizontal=True, key=f"rv_info_ok_{i}",
                      index={"ja": 0, "nein": 1}.get(saved.get("ok")))
        fix = st.text_input("Korrektur", value=saved.get("correction", ""), key=f"rv_info_fix_{i}",
                            label_visibility="collapsed", placeholder="Korrektur (falls nein)")
        if ok:
            st.session_state.rv_info[str(i)] = {"ok": ok, "correction": fix.strip()}
        st.divider()
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Zurück zu den Antworten", use_container_width=True):
            st.session_state.rv_idx = len(_items()) - 1
            st.rerun()
    with col_next:
        if st.button("Prüfung abschliessen", type="primary", use_container_width=True):
            if len(st.session_state.rv_info) < len(INFOSHEET_FACTS):
                st.warning("Bitte alle Aussagen mit ja oder nein beantworten.")
            else:
                _save(rater, status="completed")
                st.session_state.rv_finished = True
                st.rerun()


def _done_page(rater: str, items: list[dict]) -> None:
    _header(rater, "Vielen Dank!")
    counts = {label: sum(1 for r in st.session_state.rv_ratings.values() if r["rating"] == code)
              for label, code in CHOICES.items()}
    st.success("Ihre Prüfung ist gespeichert." if st.session_state.get("rv_saved")
               else "Ihre Prüfung ist abgeschlossen.")
    st.markdown("  \n".join(f"**{label}:** {n}" for label, n in counts.items()))
    missing = [it["id"] for it in items if it["id"] not in st.session_state.rv_ratings]
    if missing:
        st.warning(f"Noch nicht bewertet: {', '.join(missing)}")
    if st.button("Bewertungen nochmals ansehen", use_container_width=True):
        st.session_state.rv_finished = False
        st.session_state.rv_idx = 0
        st.rerun()


def render_review(rater: str) -> None:
    items = _items()
    ss = st.session_state
    if "rv_ratings" not in ss:
        record = load_review(rater) or {}
        ss.rv_ratings = record.get("ratings", {})
        ss.rv_info = record.get("infosheet", {})
        ss.rv_finished = record.get("status") == "completed"
        ss.rv_started = bool(ss.rv_ratings)
        # continue at the first answer not yet rated
        ss.rv_idx = next((i for i, it in enumerate(items) if it["id"] not in ss.rv_ratings), len(items))
    if ss.rv_finished:
        _done_page(rater, items)
    elif not ss.rv_started:
        _intro(rater, len(items))
    elif ss.rv_idx < len(items):
        _item_page(rater, items, ss.rv_idx)
    else:
        _infosheet_page(rater)
