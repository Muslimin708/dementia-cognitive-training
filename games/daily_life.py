from pathlib import Path
import random

import streamlit as st

from database import get_recent_events, save_game_result


GAME_PREFIX = "daily_life"
GAME_NAME = "Daily Life Story"
MAXIMUM_CHOICES = 4


def _key(name):
    return f"{GAME_PREFIX}_{name}"


def _ensure_state():
    """Create all session-state values required by the game."""
    defaults = {
        "patient_id": None,
        "source_signature": None,
        "question_pool": [],
        "total_questions": 0,
        "current_event": None,
        "current_choices": [],
        "score": 0,
        "attempts": 0,
        "total_attempts": 0,
        "first_answered": False,
        "question_completed": False,
        "result_saved": False,
    }

    for name, default in defaults.items():
        state_key = _key(name)
        if state_key not in st.session_state:
            if isinstance(default, list):
                st.session_state[state_key] = default.copy()
            else:
                st.session_state[state_key] = default


def _get_eligible_events(patient_id):
    """Return this patient's events that have a valid name and photo."""
    eligible_events = []

    for event in get_recent_events(patient_id) or []:
        if not isinstance(event, (tuple, list)) or len(event) < 5:
            continue

        event_id, event_name, event_date, description, photo_path = event[:5]

        if not event_name or not str(event_name).strip():
            continue

        if not photo_path:
            continue

        photo_file = Path(photo_path)

        if not photo_file.exists() or not photo_file.is_file():
            continue

        eligible_events.append(
            (
                event_id,
                str(event_name).strip(),
                event_date,
                description,
                str(photo_file),
            )
        )

    return eligible_events


def _build_source_signature(events):
    """Detect changes to the patient's event records."""
    return tuple(
        sorted(
            (
                str(event[0]),
                str(event[1]),
                str(event[2]),
                str(event[3]),
                str(event[4]),
            )
            for event in events
        )
    )


def _create_choices(current_event, eligible_events):
    """Create and randomize choices once for the current question."""
    correct_event_id = current_event[0]

    alternatives = [
        event
        for event in eligible_events
        if event[0] != correct_event_id
    ]
    random.shuffle(alternatives)

    choices = [current_event]
    choices.extend(alternatives[: MAXIMUM_CHOICES - 1])
    random.shuffle(choices)

    return choices


def _start_new_game(patient_id, eligible_events):
    """Start or restart a Daily Life Story session."""
    question_pool = list(eligible_events)
    random.shuffle(question_pool)

    current_event = question_pool.pop(0) if question_pool else None

    st.session_state[_key("patient_id")] = patient_id
    st.session_state[_key("source_signature")] = (
        _build_source_signature(eligible_events)
    )
    st.session_state[_key("question_pool")] = question_pool
    st.session_state[_key("total_questions")] = len(eligible_events)
    st.session_state[_key("current_event")] = current_event
    st.session_state[_key("current_choices")] = (
        _create_choices(current_event, eligible_events)
        if current_event
        else []
    )
    st.session_state[_key("score")] = 0
    st.session_state[_key("attempts")] = 0
    st.session_state[_key("total_attempts")] = 0
    st.session_state[_key("first_answered")] = False
    st.session_state[_key("question_completed")] = False
    st.session_state[_key("result_saved")] = False


def _load_next_question(eligible_events):
    """Load the next event and generate stable choices for it."""
    question_pool = st.session_state[_key("question_pool")]

    if not question_pool:
        return False

    current_event = question_pool.pop(0)

    st.session_state[_key("current_event")] = current_event
    st.session_state[_key("current_choices")] = _create_choices(
        current_event,
        eligible_events,
    )
    st.session_state[_key("attempts")] = 0
    st.session_state[_key("first_answered")] = False
    st.session_state[_key("question_completed")] = False

    return True


def _show_progress():
    """Show progress and performance for the current session."""
    total_questions = st.session_state[_key("total_questions")]
    remaining_questions = len(
        st.session_state[_key("question_pool")]
    )
    current_question = total_questions - remaining_questions

    st.write(f"Question {current_question} of {total_questions}")

    progress_value = (
        current_question / total_questions
        if total_questions > 0
        else 0.0
    )
    st.progress(min(max(progress_value, 0.0), 1.0))

    score_column, attempts_column, total_attempts_column = st.columns(3)

    score_column.metric(
        "First-Attempt Score",
        st.session_state[_key("score")],
    )
    attempts_column.metric(
        "Attempts This Question",
        st.session_state[_key("attempts")],
    )
    total_attempts_column.metric(
        "Total Attempts",
        st.session_state[_key("total_attempts")],
    )


def _process_answer(selected_event_id, correct_event_id):
    """Check an answer and award a point only on the first attempt."""
    if st.session_state[_key("question_completed")]:
        return

    st.session_state[_key("attempts")] += 1
    st.session_state[_key("total_attempts")] += 1

    is_first_attempt = not st.session_state[_key("first_answered")]
    st.session_state[_key("first_answered")] = True

    if selected_event_id == correct_event_id:
        if is_first_attempt:
            st.session_state[_key("score")] += 1

        st.session_state[_key("question_completed")] = True
  


def _save_result_once(patient_id):
    """Save exactly one result for the completed session."""
    if st.session_state[_key("result_saved")]:
        return

    save_game_result(
        patient_id=patient_id,
        game_name=GAME_NAME,
        total_questions=st.session_state[_key("total_questions")],
        score=st.session_state[_key("score")],
        total_attempts=st.session_state[_key("total_attempts")],
    )

    st.session_state[_key("result_saved")] = True


def _show_final_summary(patient_id, eligible_events):
    """Save and show the completed game result."""
    _save_result_once(patient_id)

    total_questions = st.session_state[_key("total_questions")]
    score = st.session_state[_key("score")]
    total_attempts = st.session_state[_key("total_attempts")]

    accuracy = (
        score / total_questions * 100
        if total_questions > 0
        else 0.0
    )

    st.success(f"🎉 {GAME_NAME} completed!")

    score_column, accuracy_column, attempts_column = st.columns(3)
    score_column.metric("Final Score", f"{score} / {total_questions}")
    accuracy_column.metric("First-Attempt Accuracy", f"{accuracy:.1f}%")
    attempts_column.metric("Total Attempts", total_attempts)

    st.caption(
        "The score counts questions answered correctly on the first attempt."
    )

    if st.button(
        "Play Again",
        key="daily_life_play_again",
        use_container_width=True,
    ):
        _start_new_game(patient_id, eligible_events)
        st.rerun()


def render(patient_id):
    """Render Daily Life Story for the authenticated patient."""
    _ensure_state()

    st.subheader("📖 Daily Life Story")
    st.write(
        "Look at the event photo and choose the event that matches it."
    )

    try:
        eligible_events = _get_eligible_events(patient_id)
    except Exception as error:
        st.error(f"Recent events could not be loaded: {error}")
        return

    if len(eligible_events) < 2:
        st.warning(
            "At least two recent events with available photos are "
            "needed to play this game."
        )
        st.info(
            "An authorized family member can add event photos in "
            "the Family Setup section."
        )
        return

    source_signature = _build_source_signature(eligible_events)

    if (
        st.session_state[_key("patient_id")] != patient_id
        or st.session_state[_key("source_signature")] != source_signature
        or st.session_state[_key("current_event")] is None
    ):
        _start_new_game(patient_id, eligible_events)

    current_event = st.session_state[_key("current_event")]

    if current_event is None:
        st.info("No event questions are available.")
        return

    (
        correct_event_id,
        correct_event_name,
        event_date,
        event_description,
        photo_path,
    ) = current_event

    _show_progress()

    photo_file = Path(photo_path)

    if not photo_file.exists():
        st.error(
            "The image for this event is no longer available. "
            "Ask a family member to update the event photo."
        )
        return

    _, image_column, _ = st.columns([1, 3, 1])

    with image_column:
        st.image(
            str(photo_file),
            caption="Which event does this photo show?",
            use_container_width=True,
        )

    choices = st.session_state[_key("current_choices")]
    question_completed = st.session_state[_key("question_completed")]

    for choice_number, choice in enumerate(choices, start=1):
        choice_event_id = choice[0]
        choice_event_name = choice[1]

        duplicate_name_count = sum(
            1
            for item in choices
            if item[1] == choice_event_name
        )

        if duplicate_name_count > 1:
            choice_label = (
                f"{choice_event_name} "
                f"({choice[2] or 'Date not provided'})"
            )
        else:
            choice_label = choice_event_name

        if st.button(
            choice_label,
            key=(
                f"daily_life_choice_{correct_event_id}_"
                f"{choice_event_id}_{choice_number}"
            ),
            use_container_width=True,
            disabled=question_completed,
        ):
            was_correct = choice_event_id == correct_event_id

            _process_answer(
                selected_event_id=choice_event_id,
                correct_event_id=correct_event_id,
            )

            if was_correct:
                st.success("Correct! 🎉")
            else:
                st.error("Not quite. Look at the photo and try again.")

            st.rerun()

    if st.session_state[_key("question_completed")]:
        st.success(f"The event was: {correct_event_name}")

        if event_date:
            st.write(f"**Event date:** {event_date}")

        if event_description:
            st.write(f"**Event description:** {event_description}")

        if st.session_state[_key("question_pool")]:
            if st.button(
                "Next Question →",
                key="daily_life_next_question",
                use_container_width=True,
            ):
                if _load_next_question(eligible_events):
                    st.rerun()
        else:
            _show_final_summary(patient_id, eligible_events)
