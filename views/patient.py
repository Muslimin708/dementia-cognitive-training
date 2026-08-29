import streamlit as st

from database import get_family_members, get_patient_by_code
from games import (
    daily_life,
    face_name,
    family_tree,
    history,
    missing_family,
    who_called,
)
from state import initialize_state


def _clear_patient_access():
    """Clear the connected patient and the active game."""
    st.session_state.pop("patient_portal_id", None)
    st.session_state.pop("patient_portal_name", None)
    st.session_state.pop("patient_portal_code", None)
    st.session_state.selected_game = None


def _render_patient_code_access():
    """Allow a patient to connect using the code issued by nursing staff."""
    if st.session_state.get("patient_portal_id"):
        patient_name = st.session_state["patient_portal_name"]

        st.success(f"Connected as: {patient_name}")

        if st.button(
            "Use a Different Patient Code",
            key="change_patient_code",
        ):
            _clear_patient_access()
            st.rerun()

        return True

    st.subheader("Patient Access")
    st.write(
        "Enter the patient access code provided by nursing staff "
        "to open your cognitive-training games."
    )

    with st.form("patient_access_code_form"):
        access_code = st.text_input(
            "Patient access code",
            placeholder="Enter your access code",
            max_chars=20,
            type="password",
        )

        connect = st.form_submit_button(
            "Open Patient Dashboard",
            use_container_width=True,
        )

    if connect:
        patient = get_patient_by_code(access_code)

        if patient is None:
            st.error(
                "The patient access code is invalid or inactive. "
                "Please check the code or contact nursing staff."
            )
            return False

        patient_id, patient_name, validated_code = patient

        st.session_state["patient_portal_id"] = patient_id
        st.session_state["patient_portal_name"] = patient_name
        st.session_state["patient_portal_code"] = validated_code
        st.session_state.selected_game = None
        st.rerun()

    return False


def _return_to_game_menu():
    """Return from an active game to the game-selection screen."""
    st.session_state.selected_game = None
    st.rerun()


def _render_game_menu(patient_name, members):
    """Display the cognitive-training game menu."""
    st.write(f"Welcome, {patient_name}.")
    st.subheader("Cognitive Training")

    if not members:
        st.warning(
            "No family members have been added yet. Ask an authorized "
            "family member to add photos and voice recordings before "
            "starting the family-based games."
        )

    left_column, right_column = st.columns(2)

    buttons = [
        (
            left_column,
            "👤 Face-Name Matching",
            "face_name",
            bool(members),
        ),
        (
            left_column,
            "🔊 Who Called?",
            "who_called",
            bool(members),
        ),
        (
            left_column,
            "🌳 Family Tree Builder",
            "family_tree",
            bool(members),
        ),
        (
            right_column,
            "👤 Missing Family Member",
            "where_is_it",
            bool(members),
        ),
        (
            right_column,
            "📖 Daily Life Story",
            "what_happened",
            True,
        ),
    ]

    for column, label, game_key, enabled in buttons:
        if column.button(
            label,
            use_container_width=True,
            key=f"select_{game_key}",
            disabled=not enabled,
        ):
            st.session_state.selected_game = game_key
            st.rerun()


def _render_selected_game(patient_id, members):
    """Open only the game selected by the connected patient."""
    selected_game = st.session_state.selected_game

    if selected_game is None:
        return

    if st.button(
        "← Back to Cognitive Training",
        key="back_to_patient_game_menu",
    ):
        _return_to_game_menu()

    st.divider()

    if selected_game == "face_name":
        face_name.render(patient_id, members)

    elif selected_game == "who_called":
        who_called.render(patient_id, members)

    elif selected_game == "family_tree":
        family_tree.render(patient_id, members)

    elif selected_game == "where_is_it":
        missing_family.render(patient_id)

    elif selected_game == "what_happened":
        daily_life.render(patient_id)

    else:
        st.error("The selected game is not available.")
        st.session_state.selected_game = None


def render_patient_dashboard():
    """Render the code-protected patient dashboard."""
    initialize_state()

    st.header("Patient Dashboard")

    connected = _render_patient_code_access()

    if not connected:
        st.info(
            "A valid patient access code is required before games "
            "and game history can be accessed."
        )
        return

    patient_id = st.session_state["patient_portal_id"]
    patient_name = st.session_state["patient_portal_name"]
    members = get_family_members(patient_id)

    st.divider()

    if st.session_state.selected_game is None:
        _render_game_menu(patient_name, members)
    else:
        _render_selected_game(patient_id, members)

    st.divider()

    with st.expander("View Game History", expanded=False):
        history.render(patient_id)

    st.caption(
        "This application provides cognitive-training activities. "
        "It is not intended to provide a diagnosis or replace "
        "professional clinical assessment."
    )
