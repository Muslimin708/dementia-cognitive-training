import random
from pathlib import Path

import streamlit as st

from database import save_game_result


GAME_PREFIX = "who_called"
GAME_NAME = "Who Called?"


def initialize_state():
    """
    Create all session-state values required by the game.
    """

    default_values = {
        "who_called_patient_id": None,
        "who_called_question_pool": [],
        "who_called_current_member": None,
        "who_called_voice_choices": [],
        "who_called_total_questions": 0,
        "who_called_score": 0,
        "who_called_attempts": 0,
        "who_called_total_attempts": 0,
        "who_called_first_answered": False,
        "who_called_question_completed": False,
        "who_called_result_saved": False,
        "who_called_rounds_per_member": 1,
    }

    for key, value in default_values.items():
        if key not in st.session_state:
            if isinstance(value, list):
                st.session_state[key] = value.copy()
            else:
                st.session_state[key] = value


def get_eligible_members(family_members):
    """
    Return only family members who have both an available
    photo and an available voice recording.
    """

    eligible_members = []

    for member in family_members:
        (
            member_id,
            member_name,
            relationship,
            photo_path,
            voice_path,
        ) = member

        if not photo_path or not voice_path:
            continue

        photo_file = Path(photo_path)
        voice_file = Path(voice_path)

        if photo_file.exists() and voice_file.exists():
            eligible_members.append(member)

    return eligible_members


def create_question_pool(eligible_members):
    """
    Create and randomize the question pool.
    """

    question_pool = []

    rounds = st.session_state[
        "who_called_rounds_per_member"
    ]

    for member in eligible_members:
        for _ in range(rounds):
            question_pool.append(member)

    random.shuffle(question_pool)

    return question_pool


def create_voice_choices(
    current_member,
    eligible_members,
):
    """
    Create anonymous voice choices.

    The correct person's voice is always included.
    Up to three incorrect voices are added.
    """

    correct_member_id = current_member[0]

    other_members = [
        member
        for member in eligible_members
        if member[0] != correct_member_id
    ]

    random.shuffle(other_members)

    number_of_incorrect_choices = min(
        3,
        len(other_members),
    )

    voice_choices = [
        current_member
    ]

    voice_choices.extend(
        other_members[
            :number_of_incorrect_choices
        ]
    )

    random.shuffle(voice_choices)

    return voice_choices


def start_new_game(
    patient_id,
    eligible_members,
):
    """
    Start or restart the game.
    """

    question_pool = create_question_pool(
        eligible_members
    )

    st.session_state[
        "who_called_patient_id"
    ] = patient_id

    st.session_state[
        "who_called_question_pool"
    ] = question_pool

    st.session_state[
        "who_called_total_questions"
    ] = len(question_pool)

    st.session_state[
        "who_called_score"
    ] = 0

    st.session_state[
        "who_called_attempts"
    ] = 0

    st.session_state[
        "who_called_total_attempts"
    ] = 0

    st.session_state[
        "who_called_first_answered"
    ] = False

    st.session_state[
        "who_called_question_completed"
    ] = False

    st.session_state[
        "who_called_result_saved"
    ] = False

    if question_pool:
        current_member = (
            st.session_state[
                "who_called_question_pool"
            ].pop(0)
        )

        st.session_state[
            "who_called_current_member"
        ] = current_member

        st.session_state[
            "who_called_voice_choices"
        ] = create_voice_choices(
            current_member,
            eligible_members,
        )
    else:
        st.session_state[
            "who_called_current_member"
        ] = None

        st.session_state[
            "who_called_voice_choices"
        ] = []


def load_next_question(eligible_members):
    """
    Load the next family member and new voice choices.
    """

    question_pool = st.session_state[
        "who_called_question_pool"
    ]

    if not question_pool:
        return

    current_member = question_pool.pop(0)

    st.session_state[
        "who_called_current_member"
    ] = current_member

    st.session_state[
        "who_called_voice_choices"
    ] = create_voice_choices(
        current_member,
        eligible_members,
    )

    st.session_state[
        "who_called_attempts"
    ] = 0

    st.session_state[
        "who_called_first_answered"
    ] = False

    st.session_state[
        "who_called_question_completed"
    ] = False


def process_answer(
    selected_member_id,
    correct_member_id,
):
    """
    Process the selected voice.

    One point is awarded only if the first answer is correct.
    """

    if st.session_state[
        "who_called_question_completed"
    ]:
        return

    st.session_state[
        "who_called_attempts"
    ] += 1

    st.session_state[
        "who_called_total_attempts"
    ] += 1

    is_first_answer = not st.session_state[
        "who_called_first_answered"
    ]

    is_correct = (
        selected_member_id
        == correct_member_id
    )

    if is_first_answer:
        st.session_state[
            "who_called_first_answered"
        ] = True

        if is_correct:
            st.session_state[
                "who_called_score"
            ] += 1

    if is_correct:
        st.session_state[
            "who_called_question_completed"
        ] = True

        st.success(
            "Correct! This voice belongs to "
            "the person shown in the photo. 🎉"
        )
    else:
        st.error(
            "That voice does not match the person "
            "in the photo. Listen again and try "
            "another voice."
        )


def show_progress():
    """
    Display question progress and performance metrics.
    """

    total_questions = st.session_state[
        "who_called_total_questions"
    ]

    remaining_questions = len(
        st.session_state[
            "who_called_question_pool"
        ]
    )

    current_question_number = (
        total_questions
        - remaining_questions
    )

    st.write(
        f"Question {current_question_number} "
        f"of {total_questions}"
    )

    if total_questions > 0:
        progress_value = (
            current_question_number
            / total_questions
        )
    else:
        progress_value = 0.0

    st.progress(
        min(
            max(progress_value, 0.0),
            1.0,
        )
    )


def show_metrics():
    """
    Display the current score and attempts.
    """

    score_column, attempts_column = (
        st.columns(2)
    )

    with score_column:
        st.metric(
            "Score",
            st.session_state[
                "who_called_score"
            ],
        )

    with attempts_column:
        st.metric(
            "Attempts for This Question",
            st.session_state[
                "who_called_attempts"
            ],
        )


def show_voice_choices(correct_member_id):
    """
    Display anonymous voice recordings and answer buttons.
    """

    voice_choices = st.session_state[
        "who_called_voice_choices"
    ]

    st.markdown(
        "### Listen to the voice recordings"
    )

    st.write(
        "Select the voice that belongs to the "
        "person shown in the photo."
    )

    for voice_number, member in enumerate(
        voice_choices,
        start=1,
    ):
        (
            member_id,
            member_name,
            relationship,
            photo_path,
            voice_path,
        ) = member

        voice_file = Path(voice_path)

        with st.container(border=True):
            st.markdown(
                f"#### Voice {voice_number}"
            )

            try:
                with open(
                    voice_file,
                    "rb",
                ) as audio_file:
                    audio_bytes = (
                        audio_file.read()
                    )

                st.audio(audio_bytes)

            except OSError:
                st.warning(
                    "This voice recording could "
                    "not be opened."
                )

                continue

            button_disabled = st.session_state[
                "who_called_question_completed"
            ]

            if st.button(
                f"Select Voice {voice_number}",
                key=(
                    "who_called_select_"
                    f"{correct_member_id}_"
                    f"{voice_number}_"
                    f"{member_id}"
                ),
                use_container_width=True,
                disabled=button_disabled,
            ):
                process_answer(
                    selected_member_id=member_id,
                    correct_member_id=(
                        correct_member_id
                    ),
                )


def show_completed_game(
    patient_id,
    correct_member_name,
):
    """
    Save and display the final game result.
    """

    total_questions = st.session_state[
        "who_called_total_questions"
    ]

    final_score = st.session_state[
        "who_called_score"
    ]

    total_attempts = st.session_state[
        "who_called_total_attempts"
    ]

    if total_questions > 0:
        accuracy = (
            final_score
            / total_questions
            * 100
        )
    else:
        accuracy = 0.0

    if not st.session_state[
        "who_called_result_saved"
    ]:
        save_game_result(
            patient_id,
            GAME_NAME,
            total_questions,
            final_score,
            total_attempts,
        )

        st.session_state[
            "who_called_result_saved"
        ] = True

    st.success(
        "🎉 Who Called? game completed!"
    )

    result_column_1, result_column_2 = (
        st.columns(2)
    )

    with result_column_1:
        st.metric(
            "Final Score",
            (
                f"{final_score} / "
                f"{total_questions}"
            ),
        )

        st.metric(
            "First-Attempt Accuracy",
            f"{accuracy:.1f}%",
        )

    with result_column_2:
        st.metric(
            "Total Attempts",
            total_attempts,
        )

        st.metric(
            "Questions Completed",
            total_questions,
        )

    st.caption(
        "The score counts answers that were correct "
        "on the first attempt."
    )


def render(
    patient_id,
    family_members,
):
    """
    Main entry point called by views/patient.py.
    """

    initialize_state()

    if st.button(
        "← Back to Games",
        key="who_called_back_to_games",
    ):
        st.session_state[
            "selected_game"
        ] = None

        st.rerun()

    st.subheader(
        "👤🔊 Who Called?"
    )

    st.write(
        "Look at the family member's photo. "
        "Listen to the voice recordings and choose "
        "the voice that belongs to that person."
    )

    eligible_members = get_eligible_members(
        family_members
    )

    if len(eligible_members) < 2:
        st.warning(
            "At least two family members with both "
            "a photo and a voice recording are needed "
            "to play this game."
        )

        st.info(
            "Go to the Family section and add a photo "
            "and voice recording for at least two "
            "family members."
        )

        return

    if (
        st.session_state[
            "who_called_patient_id"
        ]
        != patient_id
    ):
        start_new_game(
            patient_id,
            eligible_members,
        )

    current_member = st.session_state[
        "who_called_current_member"
    ]

    if current_member is None:
        st.info(
            "No game questions are available."
        )

        return

    (
        correct_member_id,
        correct_member_name,
        correct_relationship,
        correct_photo_path,
        correct_voice_path,
    ) = current_member

    show_progress()

    st.markdown(
        "### Whose voice matches this face?"
    )

    photo_file = Path(
        correct_photo_path
    )

    if photo_file.exists():
        image_column_1, image_column_2, image_column_3 = (
            st.columns([1, 2, 1])
        )

        with image_column_2:
            st.image(
                str(photo_file),
                width=300,
            )
    else:
        st.error(
            "The photo for this question "
            "could not be found."
        )

        return

    st.write(
        "Listen carefully to each voice. "
        "The voice labels are anonymous so that "
        "the answer is not revealed."
    )

    show_voice_choices(
        correct_member_id
    )

    st.divider()

    show_metrics()

    if st.session_state[
        "who_called_question_completed"
    ]:
        st.success(
            f"The correct answer was "
            f"{correct_member_name} "
            f"({correct_relationship})."
        )

        if st.session_state[
            "who_called_question_pool"
        ]:
            if st.button(
                "Next Question →",
                key="who_called_next_question",
                use_container_width=True,
            ):
                load_next_question(
                    eligible_members
                )

                st.rerun()

        else:
            show_completed_game(
                patient_id,
                correct_member_name,
            )

            if st.button(
                "Play Again",
                key="who_called_play_again",
                use_container_width=True,
            ):
                start_new_game(
                    patient_id,
                    eligible_members,
                )

                st.rerun()