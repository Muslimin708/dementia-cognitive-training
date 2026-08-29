from pathlib import Path
import uuid

import streamlit as st

from components.face_annotation import render as render_face_annotation
from database import (
    add_event_face_annotation,
    add_family_member,
    add_recent_event,
    delete_family_member,
    delete_recent_event,
    get_family_members,
    get_family_members_detailed,
    get_patient_by_code,
    get_recent_events,
    update_family_member_photo,
    update_family_member_voice,
)


def _save_upload(upload, folder, prefix):
    """Save an uploaded file and return its path."""
    directory = Path(folder)
    directory.mkdir(parents=True, exist_ok=True)

    extension = Path(upload.name).suffix.lower()
    filename = f"{prefix}_{uuid.uuid4().hex}{extension}"
    path = directory / filename
    path.write_bytes(upload.getbuffer())

    return str(path)


def _delete_file(file_path):
    """Delete an uploaded file if it exists."""
    if not file_path:
        return

    path = Path(file_path)
    if path.exists() and path.is_file():
        path.unlink()


def _clear_family_access():
    """Remove the validated patient from the current session."""
    st.session_state.pop("family_patient_id", None)
    st.session_state.pop("family_patient_name", None)
    st.session_state.pop("family_patient_code", None)


def _render_patient_code_access():
    """Validate the patient code issued by nursing staff."""
    st.subheader("Connect to Patient")

    if st.session_state.get("family_patient_id"):
        patient_name = st.session_state["family_patient_name"]
        patient_code = st.session_state["family_patient_code"]

        st.success(f"Connected to patient: {patient_name}")
        st.caption(f"Access code: {patient_code}")

        if st.button(
            "Use a Different Patient Code",
            key="change_family_patient",
        ):
            _clear_family_access()
            st.rerun()

        return True

    with st.form("family_patient_code_form"):
        access_code = st.text_input(
            "Patient access code",
            placeholder="Enter the code provided by nursing staff",
            max_chars=20,
        )

        connect = st.form_submit_button(
            "Connect to Patient",
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
        st.session_state["family_patient_id"] = patient_id
        st.session_state["family_patient_name"] = patient_name
        st.session_state["family_patient_code"] = validated_code
        st.rerun()

    return False


def _render_add_family_member(patient_code):
    """Add a family member to the patient linked by the access code."""
    st.subheader("Add Family Member")

    with st.form(
        "add_family_member_form",
        clear_on_submit=True,
    ):
        name = st.text_input(
            "Family member name",
            placeholder="Enter the family member's full name",
        )

        relationship = st.selectbox(
            "Relationship",
            [
                "Mother",
                "Father",
                "Daughter",
                "Son",
                "Sister",
                "Brother",
                "Spouse",
                "Grandparent",
                "Grandchild",
                "Friend",
                "Caregiver",
                "Other",
            ],
        )

        email = st.text_input(
            "Family member email",
            placeholder="name@example.com",
            help=(
                "This email can later receive reminders to refresh "
                "or add new photos."
            ),
        )

        photo = st.file_uploader(
            "Upload family member photo",
            type=["jpg", "jpeg", "png"],
        )

        voice = st.file_uploader(
            "Upload family member voice recording",
            type=["wav", "mp3", "m4a"],
        )

        save_member = st.form_submit_button(
            "Save Family Member",
            use_container_width=True,
        )

    if not save_member:
        return

    cleaned_name = name.strip()
    cleaned_email = email.strip()

    if not cleaned_name:
        st.error("Please enter the family member's name.")
        return

    if not cleaned_email or "@" not in cleaned_email:
        st.error("Please enter a valid email address.")
        return

    if photo is None:
        st.error("Please upload a family member photo.")
        return

    if voice is None:
        st.error("Please upload a family member voice recording.")
        return

    photo_path = None
    voice_path = None

    try:
        member_id = add_family_member(
            patient_code=patient_code,
            name=cleaned_name,
            relationship=relationship,
            email=cleaned_email,
        )

        photo_path = _save_upload(
            photo,
            "data/photos",
            member_id,
        )
        update_family_member_photo(
            member_id,
            photo_path,
        )

        voice_path = _save_upload(
            voice,
            "data/voice",
            member_id,
        )
        update_family_member_voice(
            member_id,
            voice_path,
        )

        st.success(
            f"{cleaned_name} was added successfully. "
            "A photo-refresh reminder has been scheduled."
        )

    except Exception as error:
        _delete_file(photo_path)
        _delete_file(voice_path)
        if "member_id" in locals():
            try:
                delete_family_member(member_id)
            except Exception:
                pass
        st.error(f"The family member could not be saved: {error}")


def _render_saved_members(patient_id):
    """Show family members and allow their media to be refreshed."""
    st.subheader("Saved Family Members")

    members = get_family_members_detailed(patient_id)

    if not members:
        st.info("No family members have been added for this patient.")
        return

    for member in members:
        (
            member_id,
            name,
            relationship,
            email,
            photo_path,
            photo_added_at,
            photo_updated_at,
            voice_path,
            voice_added_at,
            voice_updated_at,
        ) = member

        with st.container(border=True):
            st.markdown(f"### {name}")
            st.write(f"**Relationship:** {relationship or 'Not provided'}")
            st.write(f"**Email:** {email or 'Not provided'}")

            media_col_1, media_col_2 = st.columns(2)

            with media_col_1:
                st.markdown("#### Photo")

                if photo_path and Path(photo_path).exists():
                    st.image(photo_path, width=220)
                else:
                    st.warning("Photo file is missing.")

                if photo_added_at:
                    st.caption(f"First added: {photo_added_at} UTC")
                if photo_updated_at:
                    st.caption(f"Last updated: {photo_updated_at} UTC")

                replacement_photo = st.file_uploader(
                    "Replace photo",
                    type=["jpg", "jpeg", "png"],
                    key=f"replace_photo_{member_id}",
                )

                if st.button(
                    "Update Photo",
                    key=f"update_photo_{member_id}",
                    use_container_width=True,
                ):
                    if replacement_photo is None:
                        st.error("Select a new photo first.")
                    else:
                        old_photo_path = photo_path
                        new_photo_path = _save_upload(
                            replacement_photo,
                            "data/photos",
                            member_id,
                        )
                        try:
                            update_family_member_photo(
                                member_id,
                                new_photo_path,
                            )
                            if old_photo_path != new_photo_path:
                                _delete_file(old_photo_path)
                            st.success("Photo updated successfully.")
                            st.rerun()
                        except Exception as error:
                            _delete_file(new_photo_path)
                            st.error(f"Photo could not be updated: {error}")

            with media_col_2:
                st.markdown("#### Voice Recording")

                if voice_path and Path(voice_path).exists():
                    st.audio(Path(voice_path).read_bytes())
                else:
                    st.warning("Voice recording is missing.")

                if voice_added_at:
                    st.caption(f"First added: {voice_added_at} UTC")
                if voice_updated_at:
                    st.caption(f"Last updated: {voice_updated_at} UTC")

                replacement_voice = st.file_uploader(
                    "Replace voice recording",
                    type=["wav", "mp3", "m4a"],
                    key=f"replace_voice_{member_id}",
                )

                if st.button(
                    "Update Voice Recording",
                    key=f"update_voice_{member_id}",
                    use_container_width=True,
                ):
                    if replacement_voice is None:
                        st.error("Select a new voice recording first.")
                    else:
                        old_voice_path = voice_path
                        new_voice_path = _save_upload(
                            replacement_voice,
                            "data/voice",
                            member_id,
                        )
                        try:
                            update_family_member_voice(
                                member_id,
                                new_voice_path,
                            )
                            if old_voice_path != new_voice_path:
                                _delete_file(old_voice_path)
                            st.success("Voice recording updated successfully.")
                            st.rerun()
                        except Exception as error:
                            _delete_file(new_voice_path)
                            st.error(
                                "Voice recording could not be updated: "
                                f"{error}"
                            )

            st.divider()

            if st.button(
                f"Delete {name}",
                key=f"delete_member_{member_id}",
                type="secondary",
            ):
                try:
                    delete_family_member(member_id)
                    _delete_file(photo_path)
                    _delete_file(voice_path)
                    st.success(f"{name} was deleted.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Family member could not be deleted: {error}")


def _render_recent_event_form(patient_id):
    """Add a recent event for the currently connected patient."""
    st.subheader("Add Recent Event")

    members = get_family_members(patient_id)

    if not members:
        st.info(
            "Add at least one family member before creating a recent event."
        )
        return

    event_name = st.text_input(
        "Event name",
        key="event_name",
        placeholder="Example: Family birthday celebration",
    )

    event_date = st.date_input(
        "Event date",
        key="event_date",
    )

    description = st.text_area(
        "Description",
        key="event_description",
        placeholder="Describe what happened during the event",
    )

    photo = st.file_uploader(
        "Upload recent event photo",
        type=["jpg", "jpeg", "png"],
        key="event_photo",
    )

    annotations = []

    if photo is not None:
        st.image(
            photo,
            caption="Recent event photo preview",
            use_container_width=True,
        )
        st.markdown("#### Family members in this event")

    selected_member_ids = []

    for member in members:
        member_id, member_name, relationship, _, _ = member

        selected = st.checkbox(
            f"{member_name} ({relationship or 'Relationship not provided'})",
            key=f"event_member_{member_id}",
        )

        if selected:
            selected_member_ids.append(member_id)

    if st.button(
        "Save Recent Event",
        key="save_recent_event",
        use_container_width=True,
    ):
        if not event_name.strip():
            st.error("Please enter an event name.")
            return

        if photo is None:
            st.error("Please upload an event photo.")
            return

        if not selected_member_ids:
            st.error("Select at least one family member in the event.")
            return

        event_photo_path = None

        try:
            event_photo_path = _save_upload(
                photo,
                "data/recent_events",
                patient_id,
            )

            event_id = add_recent_event(
                patient_id=patient_id,
                event_name=event_name.strip(),
                event_date=str(event_date),
                description=description.strip(),
                photo_path=event_photo_path,
                family_member_ids=selected_member_ids,
            )

            for annotation in annotations:
                add_event_face_annotation(
                    event_id=event_id,
                    person_name=annotation.get("person_name", ""),
                    description=annotation.get("description", ""),
                    x=annotation.get("x", 0),
                    y=annotation.get("y", 0),
                    width=annotation.get("width", 0),
                    height=annotation.get("height", 0),
                )

            st.success(
                f"Recent event '{event_name.strip()}' was saved successfully."
            )

        except Exception as error:
            _delete_file(event_photo_path)
            st.error(f"The recent event could not be saved: {error}")


def _render_saved_events(patient_id):
    """Display and delete recent events for the connected patient."""
    st.subheader("Saved Recent Events")

    events = get_recent_events(patient_id)

    if not events:
        st.info("No recent events have been added for this patient.")
        return

    for event in events:
        event_id, name, event_date, description, photo_path = event

        with st.container(border=True):
            st.markdown(f"### 📸 {name}")
            st.write(f"**Date:** {event_date or 'Not provided'}")

            if description:
                st.write(description)

            if photo_path and Path(photo_path).exists():
                st.image(photo_path, width=500)
            else:
                st.warning("Event photo file is missing.")

            if st.button(
                f"Delete event: {name}",
                key=f"delete_event_{event_id}",
            ):
                try:
                    delete_recent_event(event_id)
                    _delete_file(photo_path)
                    st.success(f"Event '{name}' was deleted.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Event could not be deleted: {error}")


def render_family_setup():
    """Render the family portal for the validated patient code."""
    st.header("👪 Family Setup")
    st.write(
        "Enter the patient access code provided by nursing staff. "
        "After validation, you can add family members, photos, voice "
        "recordings, relationships, email addresses, and recent events."
    )

    connected = _render_patient_code_access()

    if not connected:
        st.info(
            "A valid patient access code is required before family "
            "information can be viewed or changed."
        )
        return

    patient_id = st.session_state["family_patient_id"]
    patient_name = st.session_state["family_patient_name"]
    patient_code = st.session_state["family_patient_code"]

    st.divider()
    st.markdown(f"## Family information for {patient_name}")

    add_tab, members_tab, events_tab = st.tabs(
        [
            "➕ Add Family Member",
            "👥 Manage Family Members",
            "📸 Recent Events",
        ]
    )

    with add_tab:
        _render_add_family_member(patient_code)

    with members_tab:
        _render_saved_members(patient_id)

    with events_tab:
        _render_recent_event_form(patient_id)
        st.divider()
        _render_saved_events(patient_id)

    st.divider()
    st.caption(
        "Family information is connected only to the patient identified "
        "by the validated access code. Photo upload and update dates are "
        "stored for the future photo-refresh reminder feature."
    )
