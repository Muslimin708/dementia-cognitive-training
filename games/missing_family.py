from pathlib import Path
import random

import streamlit as st
from PIL import Image, ImageFilter, UnidentifiedImageError

from database import (
    get_event_face_annotations,
    get_recent_events,
    save_game_result,
)


GAME_PREFIX = "missing_family"
GAME_NAME = "Missing Family Member"
MAXIMUM_CHOICES = 4


def _key(name):
    """Build a consistent Streamlit session-state key."""
    return f"{GAME_PREFIX}_{name}"


def _ensure_state():
    """Create all session-state values required by the game."""
    defaults = {
        "patient_id": None,
        "source_signature": None,
        "question_pool": [],
        "total_questions": 0,
        "current_event": None,
        "current_annotation": None,
        "current_choices": [],
        "score": 0,
        "attempts": 0,
        "total_attempts": 0,
        "first_answered": False,
        "question_completed": False,
        "result_saved": False,
        "last_feedback": None,
    }

    for name, default in defaults.items():
        state_key = _key(name)
        if state_key not in st.session_state:
            st.session_state[state_key] = (
                default.copy() if isinstance(default, list) else default
            )


def _normalise_annotation(annotation):
    """Validate and normalize one face-annotation database row."""
    if not isinstance(annotation, (tuple, list)) or len(annotation) < 7:
        return None

    annotation_id, person_name, description, x, y, width, height = annotation[:7]

    if not person_name or not str(person_name).strip():
        return None

    try:
        x = float(x)
        y = float(y)
        width = float(width)
        height = float(height)
    except (TypeError, ValueError):
        return None

    if width <= 0 or height <= 0:
        return None

    return (
        annotation_id,
        str(person_name).strip(),
        description,
        x,
        y,
        width,
        height,
    )


def _get_eligible_events(patient_id):
    """Return patient events with valid images and usable annotations."""
    eligible_events = []

    for event in get_recent_events(patient_id) or []:
        if not isinstance(event, (tuple, list)) or len(event) < 5:
            continue

        event_id, event_name, event_date, description, photo_path = event[:5]

        if not photo_path:
            continue

        photo_file = Path(photo_path)
        if not photo_file.exists() or not photo_file.is_file():
            continue

        annotations = []
        for annotation in get_event_face_annotations(event_id) or []:
            normalised = _normalise_annotation(annotation)
            if normalised is not None:
                annotations.append(normalised)

        unique_names = {annotation[1] for annotation in annotations}
        if not annotations or len(unique_names) < 2:
            continue

        eligible_events.append(
            {
                "event": (
                    event_id,
                    event_name or "Recent Event",
                    event_date,
                    description,
                    str(photo_file),
                ),
                "annotations": annotations,
            }
        )

    return eligible_events


def _build_source_signature(eligible_events):
    """Detect changes to events, photos, or annotations."""
    signature = []

    for item in eligible_events:
        event = item["event"]
        annotations = item["annotations"]
        annotation_signature = tuple(
            sorted(tuple(str(value) for value in annotation) for annotation in annotations)
        )
        signature.append(
            (
                str(event[0]),
                str(event[1]),
                str(event[4]),
                annotation_signature,
            )
        )

    return tuple(sorted(signature, key=repr))


def _create_choices(current_annotation, annotations):
    """Create stable, unique answer choices for one question."""
    correct_name = current_annotation[1]
    alternative_names = []

    for annotation in annotations:
        name = annotation[1]
        if name != correct_name and name not in alternative_names:
            alternative_names.append(name)

    random.shuffle(alternative_names)
    choices = alternative_names[: MAXIMUM_CHOICES - 1] + [correct_name]
    random.shuffle(choices)
    return choices


def _load_question(event_item):
    """Load one event and choose one annotated person to hide."""
    annotations = event_item["annotations"]
    current_annotation = random.choice(annotations)

    st.session_state[_key("current_event")] = event_item
    st.session_state[_key("current_annotation")] = current_annotation
    st.session_state[_key("current_choices")] = _create_choices(
        current_annotation,
        annotations,
    )
    st.session_state[_key("attempts")] = 0
    st.session_state[_key("first_answered")] = False
    st.session_state[_key("question_completed")] = False
    st.session_state[_key("last_feedback")] = None


def _start_new_game(patient_id, eligible_events):
    """Start or restart a complete game session."""
    question_pool = list(eligible_events)
    random.shuffle(question_pool)
    current_event = question_pool.pop(0) if question_pool else None

    st.session_state[_key("patient_id")] = patient_id
    st.session_state[_key("source_signature")] = _build_source_signature(
        eligible_events
    )
    st.session_state[_key("question_pool")] = question_pool
    st.session_state[_key("total_questions")] = len(eligible_events)
    st.session_state[_key("score")] = 0
    st.session_state[_key("attempts")] = 0
    st.session_state[_key("total_attempts")] = 0
    st.session_state[_key("first_answered")] = False
    st.session_state[_key("question_completed")] = False
    st.session_state[_key("result_saved")] = False
    st.session_state[_key("last_feedback")] = None

    if current_event is None:
        st.session_state[_key("current_event")] = None
        st.session_state[_key("current_annotation")] = None
        st.session_state[_key("current_choices")] = []
    else:
        _load_question(current_event)


def _load_next_question():
    """Load the next event safely."""
    question_pool = st.session_state[_key("question_pool")]

    if not question_pool:
        return False

    _load_question(question_pool.pop(0))
    return True


def _coordinate_box(annotation, image_width, image_height):
    """
    Convert annotation coordinates into a clamped Pillow crop box.

    Current contract: x and y are normalized center coordinates, while
    width and height are normalized face dimensions. Pixel values are
    also accepted as a fallback when a value is greater than 1.
    """
    _, _, _, x, y, width, height = annotation

    center_x = x * image_width if 0 <= x <= 1 else x
    center_y = y * image_height if 0 <= y <= 1 else y
    face_width = width * image_width if 0 < width <= 1 else width
    face_height = height * image_height if 0 < height <= 1 else height

    left = max(0, int(round(center_x - face_width / 2)))
    top = max(0, int(round(center_y - face_height / 2)))
    right = min(image_width, int(round(center_x + face_width / 2)))
    bottom = min(image_height, int(round(center_y + face_height / 2)))

    if right <= left or bottom <= top:
        raise ValueError("The selected face annotation has invalid coordinates.")

    return left, top, right, bottom


def _create_hidden_face_image(photo_path, annotation):
    """Load the event photo and blur the selected annotated region."""
    photo_file = Path(photo_path)

    if not photo_file.exists() or not photo_file.is_file():
        raise FileNotFoundError("The event photo could not be found.")

    with Image.open(photo_file) as source_image:
        image = source_image.convert("RGB")

    image_width, image_height = image.size
    box = _coordinate_box(annotation, image_width, image_height)
    region = image.crop(box)

    blur_radius = max(8, int(min(region.size) * 0.18))
    hidden_region = region.filter(ImageFilter.GaussianBlur(blur_radius))
    image.paste(hidden_region, box[:2])

    return image


def _show_progress():
    """Display question progress and scoring metrics."""
    total = st.session_state[_key("total_questions")]
    remaining = len(st.session_state[_key("question_pool")])
    current = total - remaining
    progress_value = current / total if total else 0.0

    st.write(f"Question {current} of {total}")
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


def _process_answer(selected_name, correct_name):
    """Score the selected answer, counting only first-attempt success."""
    if st.session_state[_key("question_completed")]:
        return None

    st.session_state[_key("attempts")] += 1
    st.session_state[_key("total_attempts")] += 1

    first_attempt = not st.session_state[_key("first_answered")]
    st.session_state[_key("first_answered")] = True
    is_correct = selected_name == correct_name

    if is_correct:
        if first_attempt:
            st.session_state[_key("score")] += 1
        st.session_state[_key("question_completed")] = True

    return is_correct


def _save_result_once(patient_id):
    """Save exactly one game-result row for the completed session."""
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
    """Save and display the final game summary."""
    try:
        _save_result_once(patient_id)
    except Exception as error:
        st.error(f"The game result could not be saved: {error}")
        return

    total = st.session_state[_key("total_questions")]
    score = st.session_state[_key("score")]
    attempts = st.session_state[_key("total_attempts")]
    accuracy = score / total * 100 if total else 0.0

    st.success(f"🎉 {GAME_NAME} completed!")

    score_column, accuracy_column, attempts_column = st.columns(3)
    score_column.metric("Final Score", f"{score} / {total}")
    accuracy_column.metric("First-Attempt Accuracy", f"{accuracy:.1f}%")
    attempts_column.metric("Total Attempts", attempts)

    st.caption(
        "The score counts questions answered correctly on the first attempt."
    )

    if st.button(
        "Play Again",
        key="missing_family_play_again",
        use_container_width=True,
    ):
        _start_new_game(patient_id, eligible_events)
        st.rerun()


def render(patient_id):
    """Render Missing Family Member for the authenticated patient."""
    _ensure_state()

    st.subheader("👤 Missing Family Member")
    st.write(
        "Look at the event photo. One annotated person has been hidden. "
        "Choose the name of the hidden person."
    )

    try:
        eligible_events = _get_eligible_events(patient_id)
    except Exception as error:
        st.error(f"Annotated recent events could not be loaded: {error}")
        return

    if not eligible_events:
        st.warning(
            "No playable event photos are available. At least one event "
            "must have an existing photo and two named face annotations."
        )
        return

    source_signature = _build_source_signature(eligible_events)

    if (
        st.session_state[_key("patient_id")] != patient_id
        or st.session_state[_key("source_signature")] != source_signature
        or st.session_state[_key("current_event")] is None
    ):
        _start_new_game(patient_id, eligible_events)

    current_item = st.session_state[_key("current_event")]
    current_annotation = st.session_state[_key("current_annotation")]

    if current_item is None or current_annotation is None:
        st.info("No question is currently available.")
        return

    event_id, event_name, event_date, _, photo_path = current_item["event"]
    correct_name = current_annotation[1]

    _show_progress()
    st.markdown(f"### Event: {event_name}")

    if event_date:
        st.caption(f"Event date: {event_date}")

    try:
        hidden_image = _create_hidden_face_image(
            photo_path,
            current_annotation,
        )
    except (FileNotFoundError, UnidentifiedImageError, OSError, ValueError) as error:
        st.error(f"The event photo could not be prepared: {error}")
        return

    _, image_column, _ = st.columns([1, 3, 1])
    with image_column:
        st.image(
            hidden_image,
            caption="Who is hidden in the blurred area?",
            use_container_width=True,
        )

    choices = st.session_state[_key("current_choices")]
    question_completed = st.session_state[_key("question_completed")]

    selected_name = st.radio(
        "Who is missing from this picture?",
        options=choices,
        key=f"missing_family_choice_{event_id}_{current_annotation[0]}",
        disabled=question_completed,
    )

    if st.button(
        "Check Answer",
        key=f"missing_family_check_{event_id}_{current_annotation[0]}",
        type="primary",
        use_container_width=True,
        disabled=question_completed,
    ):
        is_correct = _process_answer(selected_name, correct_name)

        if is_correct:
            st.session_state[_key("last_feedback")] = "correct"
        else:
            st.session_state[_key("last_feedback")] = "incorrect"

        st.rerun()

    feedback = st.session_state.get(_key("last_feedback"))
    if feedback == "incorrect" and not question_completed:
        st.error("Not quite. Look at the blurred area and try again.")

    if st.session_state[_key("question_completed")]:
        st.success(f"Correct! The hidden person was {correct_name}. 🎉")
        st.session_state.pop(_key("last_feedback"), None)

        if st.session_state[_key("question_pool")]:
            if st.button(
                "Next Question →",
                key="missing_family_next_question",
                use_container_width=True,
            ):
                if _load_next_question():
                    st.session_state.pop(_key("last_feedback"), None)
                    st.rerun()
        else:
            _show_final_summary(patient_id, eligible_events)
