"""Persistence helpers for the Phase I user study."""

import datetime
import json
import os
import pathlib
from zoneinfo import ZoneInfo

import pymongo
import streamlit as st


def study_date() -> str:
    """Today's date in Zurich, the only absolute time the study stores.

    Clock times of participation could be matched against clinic appointments in
    a small single-site sample; durations (response_time_s) are measured in
    memory and need no clock time.
    """
    return datetime.datetime.now(ZoneInfo("Europe/Zurich")).date().isoformat()


def build_current_payload(session_state) -> dict:
    """Construct the current state payload for the user session."""
    payload = {
        "user_id": session_state.user_id,
        "demographics": session_state.demographics,
        "pre_questionnaire": session_state.pre_questionnaire,
        "votes": session_state.results,
        "post_questionnaire": session_state.post_questionnaire,
        "status": session_state.view,
        "updated_at": study_date(),
        "total_items_voted": len(session_state.results),
        # The assigned items in presentation order, so a reload can restore them
        # (the slot that chose them has moved on by then).
        "assigned_items": [item["item_id"] for item in session_state.mock_data],
    }
    if session_state.view == "outro":
        payload["completed_at"] = study_date()
        payload["status"] = "completed"
    return payload


def _mongo_uri() -> str | None:
    """The connection string, from secrets.toml or the environment.

    `st.secrets.get(...)` does not merely return None when there is no
    secrets.toml — it raises (StreamlitSecretNotFoundError), which took down the
    whole save path: the `os.environ` lookup and the local-file fallback below
    never ran. On a machine that has the file this never showed; on a fresh
    deployment the app died right after the demographics page, before the first
    rating was collected. The file is gitignored, so a clone is exactly that
    case.
    """
    try:
        uri = st.secrets.get("MONGODB_URI")
    except Exception:
        uri = None
    return uri or os.environ.get("MONGODB_URI")


def _uri_configured(mongo_uri: str | None) -> bool:
    return bool(mongo_uri) and "<db_password>" not in mongo_uri and "example.mongodb.net" not in mongo_uri


def _collection(mongo_uri: str):
    client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=4000)
    return client.get_database("empathicLLM_study").get_collection("study_1")


def participant_count(role: str) -> int | None:
    """Number of earlier participants with this role: the slot that balances the
    question assignment (study_data.assign_items). None without a database, so
    the assignment falls back to the user_id hash."""
    mongo_uri = _mongo_uri()
    if not _uri_configured(mongo_uri):
        return None
    try:
        return _collection(mongo_uri).count_documents({"demographics.role": role})
    except Exception as exc:
        print(f"[DB WARNING] participant count failed, using the user_id hash: {exc}")
        return None


def load_progress(user_id: str) -> dict | None:
    """The saved record of this participant, or None (no database, nothing saved yet)."""
    mongo_uri = _mongo_uri()
    if not _uri_configured(mongo_uri):
        return None
    try:
        return _collection(mongo_uri).find_one({"user_id": user_id}, {"_id": 0})
    except Exception as exc:
        print(f"[DB WARNING] could not load progress, starting fresh: {exc}")
        return None


def save_results(payload: dict) -> tuple[bool, str]:
    """Attempt to save payload to MongoDB, then fall back to a local file."""
    mongo_uri = _mongo_uri()

    if _uri_configured(mongo_uri):
        try:
            collection = _collection(mongo_uri)

            # Replace existing record for this user or insert a new one
            collection.replace_one(
                {"user_id": payload["user_id"]},
                payload,
                upsert=True
            )
            
            # Status only: the payload itself must not end up in the host's logs.
            print(f"[DB SUCCESS] saved to MongoDB (empathicLLM_study.study_1), "
                  f"status={payload['status']}, items={payload['total_items_voted']}")
            return True, "Daten erfolgreich in MongoDB gespeichert!"
        except Exception as exc:
            err_msg = str(exc)
    else:
        err_msg = "MongoDB-Verbindungszeichenfolge nicht konfiguriert."

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

        print("\n" + "!" * 80)
        print("[DB WARNING] MongoDB connection failed. Saved payload locally to 'fallback_results.json'.")
        print(f"Error detail: {err_msg}")
        print("!" * 80 + "\n")

        return False, (
            f"MongoDB nicht verbunden ({err_msg}). "
            "Daten wurden lokal in 'fallback_results.json' gesichert."
        )
    except Exception as local_err:
        print("\n" + "X" * 80)
        print("[DB ERROR] CRITICAL: Failed to save to MongoDB AND local fallback failed.")
        print(f"MongoDB Error: {err_msg}")
        print(f"Local Error: {local_err}")
        print("X" * 80 + "\n")
        return False, f"Speicherfehler: MongoDB – {err_msg} | Lokal – {local_err}"


def save_current_progress(session_state) -> tuple[bool, str]:
    """Build and persist the current user-session payload."""
    payload = build_current_payload(session_state)
    success, msg = save_results(payload)
    session_state.db_save_status = (success, msg)
    return success, msg