"""Persistence helpers for the Phase I user study."""

import datetime
import json
import os
import pathlib

import pymongo
import streamlit as st


def build_current_payload(session_state) -> dict:
    """Construct the current state payload for the user session."""
    payload = {
        "user_id": session_state.user_id,
        "demographics": session_state.demographics,
        "pre_questionnaire": session_state.pre_questionnaire,
        "votes": session_state.results,
        "post_questionnaire": session_state.post_questionnaire,
        "status": session_state.view,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_items_voted": len(session_state.results),
    }
    if session_state.view == "outro":
        payload["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload["status"] = "completed"
    return payload


def save_results(payload: dict) -> tuple[bool, str]:
    """Attempt to save payload to MongoDB, then fall back to a local file."""
    mongo_uri = st.secrets.get("MONGODB_URI") or os.environ.get("MONGODB_URI")

    if mongo_uri and "<db_password>" not in mongo_uri and "example.mongodb.net" not in mongo_uri:
        try:
            client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=4000)
            db = client.get_database("empathicLLM_study")
            collection = db.get_collection("study_1")
            collection.insert_one(payload)
            print("\n" + "=" * 80)
            print("[DB SUCCESS] Data successfully saved to MongoDB (empathicLLM_study.study_1)")
            print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
            print("=" * 80 + "\n")
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
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
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