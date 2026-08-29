import random

import streamlit as st

from database import save_game_result


def _key(prefix, name):
    """Build a consistent Streamlit session-state key."""
    return f"{prefix}_{name}"


def _copy_value(value):
    """Return a safe copy for mutable default values."""
    if isinstance(value, list):
        return value.copy()
    if isinstance(value, dict):
        return value.copy()
    if isinstance(value, set):
        return value.copy()
    return value


def ensure_member_game_state(prefix):
    """Create all shared state values required by a member-based game."""
    defaults = {
        "patient_id": None,
        "source_signature": None,
        "question_pool": [],
        "total_questions": 0,
        "current_member": None,
        "current_choices": [],
        "score": 0,
        "attempts": 0,
        "total_attempts": 0,
        "first_answered": False,
        "question_completed": False,
        "result_saved": False,
    }

    for name, default in defaults.items():
        state_key = _key(prefix, name)
        if state_key not in st.session_state:
            st.session_state[state_key] = _copy_value(default)


def build_member_signature(members):
    """
    Build a stable signature for the current family-member source data.

    The signature changes if a member is added or removed, or if the
    member tuple changes because media or relationship data was updated.
    """
    normalized_members = []

    for member in members or []:
        if isinstance(member, dict):
            normalized = tuple(
                sorted(
                    (str(key), str(value))
                    for key, value in member.items()
                )
            )
        elif isinstance(member, (list, tuple)):
            normalized = tuple(str(value) for value in member)
        else:
            normalized = (str(member),)

        normalized_members.append(normalized)

    return tuple(sorted(normalized_members, key=repr))


def reset_member_game(prefix):
    """Remove all session-state values belonging to one game prefix."""
    prefix_text = f"{prefix}_"

    for state_key in list(st.session_state.keys()):
        if state_key.startswith(prefix_text):
            del st.session_state[state_key]

    ensure_member_game_state(prefix)


def initialise_member_game(
    prefix,
    patient_id,
    members,
    rounds=1,
    force_restart=False,
):
    """
    Initialize or restart a member-based game.

    The game restarts when:
    - the patient changes,
    - the available member data changes,
    - force_restart is True.

    Returns True when a new game was initialized and False when the
    existing session remains valid.
    """
    ensure_member_game_state(prefix)

    safe_rounds = max(1, int(rounds or 1))
    members = list(members or [])
    source_signature = build_member_signature(members)

    same_patient = (
        st.session_state.get(_key(prefix, "patient_id")) == patient_id
    )
    same_source = (
        st.session_state.get(_key(prefix, "source_signature"))
        == source_signature
    )

    if same_patient and same_source and not force_restart:
        return False

    question_pool = [
        member
        for member in members
        for _ in range(safe_rounds)
    ]
    random.shuffle(question_pool)

    st.session_state[_key(prefix, "patient_id")] = patient_id
    st.session_state[_key(prefix, "source_signature")] = source_signature
    st.session_state[_key(prefix, "question_pool")] = question_pool
    st.session_state[_key(prefix, "total_questions")] = len(question_pool)
    st.session_state[_key(prefix, "current_member")] = (
        question_pool.pop(0) if question_pool else None
    )
    st.session_state[_key(prefix, "current_choices")] = []
    st.session_state[_key(prefix, "score")] = 0
    st.session_state[_key(prefix, "attempts")] = 0
    st.session_state[_key(prefix, "total_attempts")] = 0
    st.session_state[_key(prefix, "first_answered")] = False
    st.session_state[_key(prefix, "question_completed")] = False
    st.session_state[_key(prefix, "result_saved")] = False

    return True


def next_member_question(prefix):
    """
    Load the next question safely.

    Returns True when another question was loaded and False when the
    question pool is empty. The caller decides whether to call st.rerun().
    """
    ensure_member_game_state(prefix)
    pool = st.session_state[_key(prefix, "question_pool")]

    if not pool:
        st.session_state[_key(prefix, "current_member")] = None
        st.session_state[_key(prefix, "current_choices")] = []
        return False

    st.session_state[_key(prefix, "current_member")] = pool.pop(0)
    st.session_state[_key(prefix, "current_choices")] = []
    st.session_state[_key(prefix, "attempts")] = 0
    st.session_state[_key(prefix, "first_answered")] = False
    st.session_state[_key(prefix, "question_completed")] = False

    return True


def answer(prefix, is_correct):
    """
    Record one answer.

    A score point is awarded only when the first attempt for the current
    question is correct. Further clicks are ignored after completion.

    Returns True for a correct answer, False for an incorrect answer,
    and None when the question was already complete.
    """
    ensure_member_game_state(prefix)

    if st.session_state[_key(prefix, "question_completed")]:
        return None

    st.session_state[_key(prefix, "attempts")] += 1
    st.session_state[_key(prefix, "total_attempts")] += 1

    is_first_attempt = not st.session_state[
        _key(prefix, "first_answered")
    ]

    if is_first_attempt:
        st.session_state[_key(prefix, "first_answered")] = True
        if is_correct:
            st.session_state[_key(prefix, "score")] += 1

    if is_correct:
        st.session_state[_key(prefix, "question_completed")] = True
        st.success("Correct! 🎉")
        return True

    st.error("Not quite. Try again.")
    return False


def member_choices(
    members,
    correct_value,
    field_index,
    prefix=None,
    maximum_choices=4,
):
    """
    Create choices containing the correct value and unique alternatives.

    Pass prefix to freeze the choices in session state for the current
    question. The optional prefix keeps this function compatible with the
    existing face_name.py until that file is updated.
    """
    maximum_choices = max(1, int(maximum_choices or 1))

    if prefix:
        ensure_member_game_state(prefix)
        cached_choices = st.session_state.get(
            _key(prefix, "current_choices"),
            [],
        )
        if cached_choices:
            return cached_choices

    values = []

    for member in members or []:
        try:
            value = member[field_index]
        except (IndexError, KeyError, TypeError):
            continue

        if value is not None and value not in values:
            values.append(value)

    alternatives = [
        value for value in values if value != correct_value
    ]
    random.shuffle(alternatives)

    choices = alternatives[: maximum_choices - 1]
    choices.append(correct_value)
    random.shuffle(choices)

    if prefix:
        st.session_state[_key(prefix, "current_choices")] = choices

    return choices


def progress(prefix):
    """Display the current question number and progress bar."""
    ensure_member_game_state(prefix)

    total = st.session_state[_key(prefix, "total_questions")]
    remaining = len(st.session_state[_key(prefix, "question_pool")])

    if total <= 0:
        current = 0
        progress_value = 0.0
    else:
        current = total - remaining
        progress_value = current / total

    st.write(f"Question {current} of {total}")
    st.progress(min(max(progress_value, 0.0), 1.0))


def metrics(prefix):
    """Display score, current attempts, and total attempts."""
    ensure_member_game_state(prefix)

    score_column, attempts_column, total_attempts_column = st.columns(3)

    score_column.metric(
        "First-Attempt Score",
        st.session_state[_key(prefix, "score")],
    )
    attempts_column.metric(
        "Attempts This Question",
        st.session_state[_key(prefix, "attempts")],
    )
    total_attempts_column.metric(
        "Total Attempts",
        st.session_state[_key(prefix, "total_attempts")],
    )


def calculate_accuracy(score, total_questions):
    """Calculate a percentage safely."""
    if not total_questions:
        return 0.0
    return score / total_questions * 100


def save_result_once(prefix, patient_id, game_name):
    """
    Save a completed game exactly once.

    Returns True if a new database record was written and False if this
    game session had already been saved.
    """
    ensure_member_game_state(prefix)

    if st.session_state[_key(prefix, "result_saved")]:
        return False

    total_questions = st.session_state[_key(prefix, "total_questions")]
    score = st.session_state[_key(prefix, "score")]
    total_attempts = st.session_state[_key(prefix, "total_attempts")]

    save_game_result(
        patient_id=patient_id,
        game_name=game_name,
        total_questions=total_questions,
        score=score,
        total_attempts=total_attempts,
    )

    st.session_state[_key(prefix, "result_saved")] = True
    return True


def show_final_summary(prefix, game_name):
    """Display a consistent final summary for a completed game."""
    ensure_member_game_state(prefix)

    total_questions = st.session_state[_key(prefix, "total_questions")]
    score = st.session_state[_key(prefix, "score")]
    total_attempts = st.session_state[_key(prefix, "total_attempts")]
    accuracy = calculate_accuracy(score, total_questions)

    st.success(f"🎉 {game_name} completed!")

    score_column, accuracy_column, attempts_column = st.columns(3)
    score_column.metric("Final Score", f"{score} / {total_questions}")
    accuracy_column.metric("First-Attempt Accuracy", f"{accuracy:.1f}%")
    attempts_column.metric("Total Attempts", total_attempts)

    st.caption(
        "The score counts questions answered correctly on the first attempt."
    )