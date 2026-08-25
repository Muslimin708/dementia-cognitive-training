import mimetypes
import random
import uuid
from pathlib import Path
from nursing_dashboard import show_nursing_dashboard
import streamlit as st

from database import (
    create_database,
    add_patient,
    get_patient_id,
    get_all_patients,
    add_family_member,
    update_family_member_photo,
    update_family_member_voice,
    get_family_members,
    delete_family_member,
    save_memory_score,
    get_memory_scores,
    save_recognition_result,
    get_recognition_results,
)


# ============================================================
# APPLICATION CONSTANTS
# ============================================================

APP_TITLE = "Dementia Cognitive Training App"

PHOTO_DIRECTORY = Path("data/photos")
VOICE_DIRECTORY = Path("data/voice")

PHOTO_EXTENSIONS = ["jpg", "jpeg", "png"]
VOICE_EXTENSIONS = ["wav", "mp3", "m4a"]

MAX_PHOTO_SIZE_MB = 10
MAX_VOICE_SIZE_MB = 25


# ============================================================
# INITIAL SETUP
# ============================================================

create_database()

PHOTO_DIRECTORY.mkdir(parents=True, exist_ok=True)
VOICE_DIRECTORY.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalize_name(name):
    """Remove unnecessary spaces from a name."""

    if not name:
        return ""

    return " ".join(name.strip().split())


def uploaded_file_size_mb(uploaded_file):
    """Return the uploaded file size in megabytes."""

    if uploaded_file is None:
        return 0

    return uploaded_file.size / (1024 * 1024)


def save_uploaded_file(uploaded_file, directory, record_id):
    """Save an uploaded file and return its local path."""

    directory.mkdir(parents=True, exist_ok=True)

    extension = Path(uploaded_file.name).suffix.lower()

    unique_filename = (
        f"{record_id}_{uuid.uuid4().hex}{extension}"
    )

    file_path = directory / unique_filename

    with open(file_path, "wb") as output_file:
        output_file.write(uploaded_file.getbuffer())

    return str(file_path)


def display_photo(photo_path, caption=None, width=300):
    """Display a locally stored photo."""

    if not photo_path:
        st.info("No photo has been uploaded.")
        return

    photo_file = Path(photo_path)

    if not photo_file.exists():
        st.warning("The photo file could not be found.")
        return

    st.image(
        str(photo_file),
        caption=caption,
        width=width,
    )


def display_audio(voice_path):
    """Display a locally stored voice recording."""

    if not voice_path:
        st.info("No voice recording has been uploaded.")
        return

    voice_file = Path(voice_path)

    if not voice_file.exists():
        st.warning("The voice recording could not be found.")
        return

    mime_type, _ = mimetypes.guess_type(str(voice_file))

    with open(voice_file, "rb") as audio_file:
        audio_data = audio_file.read()

    if mime_type:
        st.audio(
            audio_data,
            format=mime_type,
        )
    else:
        st.audio(audio_data)


def get_patient_options():
    """
    Return patients as a dictionary:

    {
        patient_id: patient_name
    }
    """

    patients = get_all_patients()

    return {
        patient_id: patient_name
        for patient_id, patient_name in patients
    }


def create_or_get_patient(patient_name):
    """Return an existing patient ID or create a patient."""

    clean_name = normalize_name(patient_name)

    patient_id = get_patient_id(clean_name)

    if patient_id is None:
        patient_id = add_patient(clean_name)

    return patient_id


def calculate_recognition_statistics(results):
    """Calculate statistics from recognition results."""

    total_attempts = len(results)

    correct_answers = sum(
        1
        for _, correct, _ in results
        if correct == 1
    )

    incorrect_answers = total_attempts - correct_answers

    if total_attempts > 0:
        accuracy = (
            correct_answers / total_attempts
        ) * 100
    else:
        accuracy = 0

    return (
        total_attempts,
        correct_answers,
        incorrect_answers,
        accuracy,
    )


def calculate_memory_statistics(memory_scores):
    """Calculate statistics from memory exercise scores."""

    if not memory_scores:
        return 0, 0, 0

    numeric_scores = [
        score
        for score, _ in memory_scores
    ]

    latest_score = numeric_scores[0]
    highest_score = max(numeric_scores)

    average_score = (
        sum(numeric_scores) / len(numeric_scores)
    )

    return (
        latest_score,
        highest_score,
        average_score,
    )


def reset_recognition_question():
    """Remove the current recognition question."""

    keys_to_remove = [
        "recognition_patient_id",
        "recognition_member_id",
        "recognition_options",
        "recognition_submitted",
        "recognition_feedback",
    ]

    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]


def create_recognition_question(patient_id, family_members):
    """Create a random family-recognition question."""

    eligible_members = [
        member
        for member in family_members
        if member[3] and Path(member[3]).exists()
    ]

    if not eligible_members:
        return False

    selected_member = random.choice(eligible_members)

    correct_member_id = selected_member[0]
    correct_name = selected_member[1]

    all_names = list(
        dict.fromkeys(
            member[1]
            for member in family_members
        )
    )

    incorrect_names = [
        name
        for name in all_names
        if name != correct_name
    ]

    random.shuffle(incorrect_names)

    answer_options = [
        correct_name,
        *incorrect_names[:3],
    ]

    random.shuffle(answer_options)

    st.session_state["recognition_patient_id"] = (
        patient_id
    )

    st.session_state["recognition_member_id"] = (
        correct_member_id
    )

    st.session_state["recognition_options"] = (
        answer_options
    )

    st.session_state["recognition_submitted"] = False
    st.session_state["recognition_feedback"] = None

    return True


def get_current_recognition_member(family_members):
    """Return the family member used in the current question."""

    selected_member_id = st.session_state.get(
        "recognition_member_id"
    )

    for member in family_members:
        if member[0] == selected_member_id:
            return member

    return None


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🧠 Navigation")

role = st.sidebar.radio(
    "Select your role",
    [
        "Patient",
        "Family",
        "Nursing Staff",
    ],
)

st.sidebar.divider()

st.sidebar.caption(
    "This prototype stores information locally "
    "in an SQLite database and local data folders."
)


# ============================================================
# MAIN HEADER
# ============================================================

st.title("🧠 Dementia Cognitive Training App")

st.write(
    "A digital cognitive training prototype for "
    "supporting early dementia care."
)


# ============================================================
# PATIENT DASHBOARD
# ============================================================

if role == "Patient":
    st.header("Patient Dashboard")

    patient_options = get_patient_options()

    if not patient_options:
        st.info(
            "No patient has been registered. "
            "A family member must first add a patient "
            "and at least one family member."
        )

    else:
        selected_patient_id = st.selectbox(
            "Select patient",
            options=list(patient_options.keys()),
            format_func=lambda patient_id: (
                patient_options[patient_id]
            ),
            key="patient_dashboard_patient",
        )

        selected_patient_name = patient_options[
            selected_patient_id
        ]

        previous_patient_id = st.session_state.get(
            "recognition_patient_id"
        )

        if (
            previous_patient_id is not None
            and previous_patient_id != selected_patient_id
        ):
            reset_recognition_question()

        st.success(
            f"Welcome, {selected_patient_name}."
        )

        recognition_tab, memory_tab = st.tabs(
            [
                "Family Recognition",
                "Memory Exercise",
            ]
        )

        # ====================================================
        # FAMILY RECOGNITION GAME
        # ====================================================

        with recognition_tab:
            st.subheader("Who Is This?")

            st.write(
                "Look at the photograph, listen to the "
                "voice recording if available, and select "
                "the correct family member."
            )

            family_members = get_family_members(
                selected_patient_id
            )

            members_with_photos = [
                member
                for member in family_members
                if member[3] and Path(member[3]).exists()
            ]

            if not members_with_photos:
                st.info(
                    "No family photographs are available "
                    "for this patient."
                )

            else:
                if (
                    "recognition_member_id"
                    not in st.session_state
                ):
                    create_recognition_question(
                        selected_patient_id,
                        family_members,
                    )

                current_member = (
                    get_current_recognition_member(
                        family_members
                    )
                )

                if current_member is None:
                    reset_recognition_question()

                    create_recognition_question(
                        selected_patient_id,
                        family_members,
                    )

                    st.rerun()

                (
                    current_member_id,
                    current_name,
                    current_relationship,
                    current_photo_path,
                    current_voice_path,
                ) = current_member

                question_col_1, question_col_2 = (
                    st.columns([2, 1])
                )

                with question_col_1:
                    display_photo(
                        current_photo_path,
                        caption="Who is this person?",
                        width=400,
                    )

                with question_col_2:
                    st.markdown("### Listen")

                    if current_voice_path:
                        display_audio(
                            current_voice_path
                        )
                    else:
                        st.info(
                            "No voice recording is available."
                        )

                answer_options = st.session_state.get(
                    "recognition_options",
                    [],
                )

                answer_key = (
                    f"recognition_answer_"
                    f"{selected_patient_id}_"
                    f"{current_member_id}"
                )

                selected_answer = st.radio(
                    "Select the person's name",
                    options=answer_options,
                    index=None,
                    key=answer_key,
                )

                already_submitted = st.session_state.get(
                    "recognition_submitted",
                    False,
                )

                if st.button(
                    "Submit Answer",
                    type="primary",
                    disabled=already_submitted,
                    key="submit_recognition_answer",
                ):
                    if selected_answer is None:
                        st.warning(
                            "Please select an answer."
                        )

                    else:
                        is_correct = (
                            selected_answer
                            == current_name
                        )

                        save_recognition_result(
                            selected_patient_id,
                            current_member_id,
                            is_correct,
                        )

                        st.session_state[
                            "recognition_submitted"
                        ] = True

                        st.session_state[
                            "recognition_feedback"
                        ] = (
                            is_correct
                        )

                        st.rerun()

                feedback = st.session_state.get(
                    "recognition_feedback"
                )

                if feedback is True:
                    st.success(
                        f"Correct! This is {current_name}, "
                        f"your "
                        f"{current_relationship.lower()}."
                    )

                elif feedback is False:
                    st.error(
                        f"The correct answer is "
                        f"{current_name}, your "
                        f"{current_relationship.lower()}."
                    )

                if st.session_state.get(
                    "recognition_submitted",
                    False,
                ):
                    if st.button(
                        "Next Question",
                        type="primary",
                        key="next_recognition_question",
                    ):
                        if answer_key in st.session_state:
                            del st.session_state[answer_key]

                        reset_recognition_question()

                        create_recognition_question(
                            selected_patient_id,
                            family_members,
                        )

                        st.rerun()

        # ====================================================
        # MEMORY EXERCISE
        # ====================================================

        with memory_tab:
            st.subheader("Simple Memory Exercise")

            st.write(
                "Memorize the three words below. "
                "Then enter how many words you remembered."
            )

            memory_words = [
                "Garden",
                "Window",
                "Coffee",
            ]

            word_col_1, word_col_2, word_col_3 = (
                st.columns(3)
            )

            with word_col_1:
                st.info(memory_words[0])

            with word_col_2:
                st.info(memory_words[1])

            with word_col_3:
                st.info(memory_words[2])

            with st.form(
                "memory_score_form",
                clear_on_submit=True,
            ):
                remembered_words = st.number_input(
                    "Number of words remembered",
                    min_value=0,
                    max_value=3,
                    value=0,
                    step=1,
                )

                memory_submit = (
                    st.form_submit_button(
                        "Save Memory Score",
                        type="primary",
                    )
                )

            if memory_submit:
                save_memory_score(
                    selected_patient_id,
                    int(remembered_words),
                )

                st.success(
                    f"Memory score saved: "
                    f"{int(remembered_words)} out of 3."
                )


# ============================================================
# FAMILY DASHBOARD
# ============================================================

elif role == "Family":
    st.header("Family Dashboard")

    st.write(
        "Register patients and add photographs and voice "
        "recordings of their family members."
    )

    add_tab, manage_tab = st.tabs(
        [
            "Add Family Member",
            "Manage Family Members",
        ]
    )

    # ========================================================
    # ADD FAMILY MEMBER
    # ========================================================

    with add_tab:
        st.subheader("Add Family Member")

        with st.form(
            "add_family_member_form",
            clear_on_submit=True,
        ):
            patient_name = st.text_input(
                "Patient name",
                placeholder=(
                    "Enter the patient's full name"
                ),
            )

            family_member_name = st.text_input(
                "Family member name",
                placeholder=(
                    "Enter the family member's full name"
                ),
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

            photo = st.file_uploader(
                "Upload family member photo",
                type=PHOTO_EXTENSIONS,
            )

            voice = st.file_uploader(
                "Upload family member voice recording",
                type=VOICE_EXTENSIONS,
            )

            save_family_member_button = (
                st.form_submit_button(
                    "Save Family Member",
                    type="primary",
                )
            )

        if save_family_member_button:
            clean_patient_name = normalize_name(
                patient_name
            )

            clean_family_member_name = normalize_name(
                family_member_name
            )

            photo_extension = (
                Path(photo.name)
                .suffix.lower()
                .lstrip(".")
                if photo is not None
                else ""
            )

            voice_extension = (
                Path(voice.name)
                .suffix.lower()
                .lstrip(".")
                if voice is not None
                else ""
            )

            if not clean_patient_name:
                st.error(
                    "Please enter the patient's name."
                )

            elif not clean_family_member_name:
                st.error(
                    "Please enter the family member's name."
                )

            elif photo is None:
                st.error(
                    "Please upload a family member photo."
                )

            elif voice is None:
                st.error(
                    "Please upload a voice recording."
                )

            elif photo_extension not in PHOTO_EXTENSIONS:
                st.error(
                    "The selected photo type is not supported."
                )

            elif voice_extension not in VOICE_EXTENSIONS:
                st.error(
                    "The selected voice file type "
                    "is not supported."
                )

            elif (
                uploaded_file_size_mb(photo)
                > MAX_PHOTO_SIZE_MB
            ):
                st.error(
                    f"The photo must be smaller than "
                    f"{MAX_PHOTO_SIZE_MB} MB."
                )

            elif (
                uploaded_file_size_mb(voice)
                > MAX_VOICE_SIZE_MB
            ):
                st.error(
                    f"The voice recording must be smaller "
                    f"than {MAX_VOICE_SIZE_MB} MB."
                )

            else:
                family_member_id = None
                saved_photo_path = None
                saved_voice_path = None

                try:
                    patient_id = create_or_get_patient(
                        clean_patient_name
                    )

                    family_member_id = add_family_member(
                        patient_id,
                        clean_family_member_name,
                        relationship,
                    )

                    saved_photo_path = save_uploaded_file(
                        photo,
                        PHOTO_DIRECTORY,
                        family_member_id,
                    )

                    update_family_member_photo(
                        family_member_id,
                        saved_photo_path,
                    )

                    saved_voice_path = save_uploaded_file(
                        voice,
                        VOICE_DIRECTORY,
                        family_member_id,
                    )

                    update_family_member_voice(
                        family_member_id,
                        saved_voice_path,
                    )

                    st.success(
                        f"{clean_family_member_name} was "
                        f"successfully added for "
                        f"{clean_patient_name}."
                    )

                    preview_col_1, preview_col_2 = (
                        st.columns(2)
                    )

                    with preview_col_1:
                        display_photo(
                            saved_photo_path,
                            caption=clean_family_member_name,
                            width=300,
                        )

                    with preview_col_2:
                        st.markdown(
                            "#### Voice Recording"
                        )

                        display_audio(
                            saved_voice_path
                        )

                except Exception as error:
                    if saved_photo_path:
                        saved_photo_file = Path(
                            saved_photo_path
                        )

                        if saved_photo_file.exists():
                            saved_photo_file.unlink()

                    if saved_voice_path:
                        saved_voice_file = Path(
                            saved_voice_path
                        )

                        if saved_voice_file.exists():
                            saved_voice_file.unlink()

                    if family_member_id is not None:
                        try:
                            delete_family_member(
                                family_member_id
                            )
                        except Exception:
                            pass

                    st.error(
                        "The family member could not "
                        "be saved."
                    )

                    st.exception(error)

    # ========================================================
    # MANAGE FAMILY MEMBERS
    # ========================================================

    with manage_tab:
        st.subheader("Saved Family Members")

        patient_options = get_patient_options()

        if not patient_options:
            st.info(
                "No patients have been registered."
            )

        else:
            selected_family_patient_id = st.selectbox(
                "Select patient",
                options=list(patient_options.keys()),
                format_func=lambda patient_id: (
                    patient_options[patient_id]
                ),
                key="family_manage_patient",
            )

            family_members = get_family_members(
                selected_family_patient_id
            )

            if not family_members:
                st.info(
                    "No family members have been added "
                    "for this patient."
                )

            else:
                for member in family_members:
                    (
                        member_id,
                        member_name,
                        member_relationship,
                        photo_path,
                        voice_path,
                    ) = member

                    with st.container(border=True):
                        st.markdown(
                            f"### {member_name}"
                        )

                        st.write(
                            f"**Relationship:** "
                            f"{member_relationship}"
                        )

                        member_col_1, member_col_2 = (
                            st.columns([1, 1])
                        )

                        with member_col_1:
                            display_photo(
                                photo_path,
                                caption=member_name,
                                width=250,
                            )

                        with member_col_2:
                            st.markdown(
                                "#### Voice Recording"
                            )

                            display_audio(voice_path)

                        delete_key = (
                            f"confirm_delete_{member_id}"
                        )

                        if delete_key not in st.session_state:
                            st.session_state[
                                delete_key
                            ] = False

                        delete_confirmation_visible = (
                            st.session_state[delete_key]
                        )

                        if not delete_confirmation_visible:
                            if st.button(
                                f"Delete {member_name}",
                                key=(
                                    f"delete_request_"
                                    f"{member_id}"
                                ),
                            ):
                                st.session_state[
                                    delete_key
                                ] = True

                                st.rerun()

                        else:
                            st.warning(
                                f"Are you sure you want to "
                                f"delete {member_name}?"
                            )

                            confirm_col, cancel_col = (
                                st.columns(2)
                            )

                            with confirm_col:
                                if st.button(
                                    "Yes, delete",
                                    type="primary",
                                    key=(
                                        f"delete_confirm_"
                                        f"{member_id}"
                                    ),
                                ):
                                    try:
                                        delete_family_member(
                                            member_id
                                        )

                                        if (
                                            delete_key
                                            in st.session_state
                                        ):
                                            del st.session_state[
                                                delete_key
                                            ]

                                        st.success(
                                            f"{member_name} "
                                            f"was deleted."
                                        )

                                        st.rerun()

                                    except Exception as error:
                                        st.error(
                                            "This family member "
                                            "could not be deleted."
                                        )

                                        st.exception(error)

                            with cancel_col:
                                if st.button(
                                    "Cancel",
                                    key=(
                                        f"delete_cancel_"
                                        f"{member_id}"
                                    ),
                                ):
                                    st.session_state[
                                        delete_key
                                    ] = False

                                    st.rerun()


# ============================================================
# NURSING STAFF DASHBOARD
# ============================================================

elif role == "Nursing Staff":
    show_nursing_dashboard()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Prototype application. It is not a medical diagnostic "
    "tool and should not replace professional medical care."
)