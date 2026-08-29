from pathlib import Path

import streamlit as st

from games.common import (
    answer,
    initialise_member_game,
    member_choices,
    metrics,
    next_member_question,
    progress,
    reset_member_game,
    save_result_once,
    show_final_summary,
)


GAME_PREFIX = "face_name"
GAME_NAME = "Face-Name Matching"
DEFAULT_ROUNDS_PER_MEMBER = 1


def _get_eligible_members(members):
    """Return family members with valid names and available photo files."""
    eligible_members = []

    for member in members or []:
        if not isinstance(member, (tuple, list)) or len(member) < 5:
            continue

        member_id, name, relationship, photo_path, voice_path = member[:5]

        if not name or not str(name).strip():
            continue

        if not photo_path:
            continue

        photo_file = Path(photo_path)

        if not photo_file.exists() or not photo_file.is_file():
            continue

        eligible_members.append(
            (
                member_id,
                str(name).strip(),
                relationship,
                str(photo_file),
                voice_path,
            )
        )

    return eligible_members


def _start_game(
    patient_id,
    eligible_members,
    force_restart=False,
):
    """Initialize or restart Face-Name Matching."""
    rounds_per_member = st.session_state.get(
        "face_name_rounds_per_member",
        DEFAULT_ROUNDS_PER_MEMBER,
    )

    try:
        rounds_per_member = max(1, int(rounds_per_member))
    except (TypeError, ValueError):
        rounds_per_member = DEFAULT_ROUNDS_PER_MEMBER

    initialise_member_game(
        prefix=GAME_PREFIX,
        patient_id=patient_id,
        members=eligible_members,
        rounds=rounds_per_member,
        force_restart=force_restart,
    )


def _show_current_question(eligible_members):
    """Display the current photo and stable name choices."""
    current_member = st.session_state.get(
        "face_name_current_member"
    )

    if current_member is None:
        st.info("No Face-Name Matching questions are available.")
        return

    (
        member_id,
        correct_name,
        relationship,
        photo_path,
        _,
    ) = current_member

    progress(GAME_PREFIX)

    photo_file = Path(photo_path)

    if not photo_file.exists() or not photo_file.is_file():
        st.error(
            "The photo for this question is no longer available. "
            "Ask an authorized family member to update the photo."
        )
        return

    _, image_column, _ = st.columns([1, 2, 1])

    with image_column:
        st.image(
            str(photo_file),
            caption="Who is this person?",
            use_container_width=True,
        )

    st.markdown("### Select the correct name")

    choices = member_choices(
        members=eligible_members,
        correct_value=correct_name,
        field_index=1,
        prefix=GAME_PREFIX,
        maximum_choices=4,
    )

    question_completed = st.session_state.get(
        "face_name_question_completed",
        False,
    )

    for choice_number, choice in enumerate(choices, start=1):
        if st.button(
            choice,
            key=(
                f"face_name_choice_{member_id}_"
                f"{choice_number}_{choice}"
            ),
            use_container_width=True,
            disabled=question_completed,
        ):
            answer(
                prefix=GAME_PREFIX,
                is_correct=(choice == correct_name),
            )
            st.rerun()

    metrics(GAME_PREFIX)

    if st.session_state.get(
        "face_name_question_completed",
        False,
    ):
        if relationship:
            correct_answer = f"{correct_name} ({relationship})"
        else:
            correct_answer = correct_name

        st.success(f"The correct answer is {correct_answer}.")


def _show_question_navigation(
    patient_id,
    eligible_members,
):
    """Show the next-question control or final summary."""
    question_completed = st.session_state.get(
        "face_name_question_completed",
        False,
    )

    if not question_completed:
        return

    question_pool = st.session_state.get(
        "face_name_question_pool",
        [],
    )

    if question_pool:
        if st.button(
            "Next Question →",
            key="face_name_next_question",
            use_container_width=True,
        ):
            if next_member_question(GAME_PREFIX):
                st.rerun()
        return

    try:
        save_result_once(
            prefix=GAME_PREFIX,
            patient_id=patient_id,
            game_name=GAME_NAME,
        )
    except Exception as error:
        st.error(f"The game result could not be saved: {error}")
        return

    show_final_summary(
        prefix=GAME_PREFIX,
        game_name=GAME_NAME,
    )

    if st.button(
        "Play Again",
        key="face_name_play_again",
        use_container_width=True,
    ):
        reset_member_game(GAME_PREFIX)
        _start_game(
            patient_id=patient_id,
            eligible_members=eligible_members,
            force_restart=True,
        )
        st.rerun()


def render(patient_id, members):
    """Render Face-Name Matching for the authenticated patient."""
    st.subheader("👤 Face-Name Matching")
    st.write(
        "Look at the family member's photo and select the correct name."
    )

    eligible_members = _get_eligible_members(members)

    if len(eligible_members) < 2:
        st.warning(
            "At least two family members with available photos are "
            "needed to play this game."
        )
        st.info(
            "An authorized family member can add or update photos in "
            "the Family Setup section."
        )
        return

    _start_game(
        patient_id=patient_id,
        eligible_members=eligible_members,
    )

    _show_current_question(eligible_members)

    _show_question_navigation(
        patient_id=patient_id,
        eligible_members=eligible_members,
    )