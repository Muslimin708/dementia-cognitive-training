from pathlib import Path
import random

import streamlit as st
from streamlit_sortables import sort_items

from database import save_game_result


GAME_PREFIX = "family_tree"
GAME_NAME = "Family Tree Builder"


def _key(name):
    return f"{GAME_PREFIX}_{name}"


def _ensure_state():
    defaults = {
        "patient_id": None,
        "source_signature": None,
        "members": [],
        "board_items": [],
        "board_version": 0,
        "score": 0,
        "total_questions": 0,
        "total_attempts": 0,
        "checked": False,
        "result_saved": False,
        "feedback": [],
    }

    for name, default in defaults.items():
        state_key = _key(name)
        if state_key not in st.session_state:
            st.session_state[state_key] = (
                default.copy() if isinstance(default, list) else default
            )


def _get_eligible_members(members):
    """Normalize the five-column family-member tuples from database.py."""
    eligible = []

    for member in members or []:
        if isinstance(member, dict):
            member_id = member.get("id")
            name = member.get("name")
            relationship = member.get("relationship") or member.get("relation")
            photo_path = member.get("photo_path") or member.get("photo")
        elif isinstance(member, (tuple, list)) and len(member) >= 5:
            member_id, name, relationship, photo_path, _ = member[:5]
        else:
            continue

        if member_id is None or not name or not relationship:
            continue

        eligible.append(
            {
                "id": int(member_id),
                "name": str(name).strip(),
                "relationship": str(relationship).strip(),
                "photo_path": str(photo_path) if photo_path else None,
            }
        )

    return eligible


def _source_signature(members):
    return tuple(
        sorted(
            (
                member["id"],
                member["name"],
                member["relationship"],
                member["photo_path"] or "",
            )
            for member in members
        )
    )


def _name_card(member):
    """Create a unique draggable label, even when names are duplicated."""
    return f'{member["name"]} [#{member["id"]}]'


def _slot_header(member, position):
    """Create a unique target header, even for repeated relationships."""
    return f'{position}. {member["relationship"]}'


def _create_board(members):
    shuffled_members = list(members)
    random.shuffle(shuffled_members)

    board = [
        {
            "header": "Family member cards",
            "items": [_name_card(member) for member in shuffled_members],
        }
    ]

    for position, member in enumerate(members, start=1):
        board.append(
            {
                "header": _slot_header(member, position),
                "items": [],
            }
        )

    return board


def _start_game(patient_id, members, force=False):
    signature = _source_signature(members)

    same_patient = st.session_state[_key("patient_id")] == patient_id
    same_source = st.session_state[_key("source_signature")] == signature

    if same_patient and same_source and not force:
        return

    st.session_state[_key("patient_id")] = patient_id
    st.session_state[_key("source_signature")] = signature
    st.session_state[_key("members")] = members
    st.session_state[_key("board_items")] = _create_board(members)
    st.session_state[_key("board_version")] += 1
    st.session_state[_key("score")] = 0
    st.session_state[_key("total_questions")] = len(members)
    st.session_state[_key("total_attempts")] = 0
    st.session_state[_key("checked")] = False
    st.session_state[_key("result_saved")] = False
    st.session_state[_key("feedback")] = []


def _show_member_photos(members):
    """Render image files with st.image instead of displaying encoded text."""
    st.markdown("### Family members")
    st.caption("Review the photos, then drag each name to a relationship slot.")

    columns = st.columns(min(4, max(1, len(members))))

    for index, member in enumerate(members):
        with columns[index % len(columns)]:
            photo_path = member["photo_path"]

            if photo_path:
                photo_file = Path(photo_path)
                if photo_file.exists() and photo_file.is_file():
                    st.image(
                        str(photo_file),
                        caption=member["name"],
                        use_container_width=True,
                    )
                else:
                    st.warning(f'Photo unavailable for {member["name"]}.')
            else:
                st.info(f'No photo for {member["name"]}.')


def _validate_board(board, members):
    """Validate one dragged name in each relationship target."""
    if not board or len(board) != len(members) + 1:
        return None, "The drag board is incomplete. Please restart the game."

    source_cards = board[0].get("items", [])
    target_containers = board[1:]

    if source_cards:
        return None, "Drag every family-member card into a relationship slot."

    invalid_slots = [
        container.get("header", "Relationship")
        for container in target_containers
        if len(container.get("items", [])) != 1
    ]

    if invalid_slots:
        return None, (
            "Each relationship slot must contain exactly one name. "
            "Please correct: " + ", ".join(invalid_slots)
        )

    feedback = []
    score = 0

    for member, container in zip(members, target_containers):
        selected_card = container["items"][0]
        correct_card = _name_card(member)
        is_correct = selected_card == correct_card

        if is_correct:
            score += 1

        feedback.append(
            {
                "relationship": member["relationship"],
                "selected": selected_card.rsplit(" [#", 1)[0],
                "correct": member["name"],
                "is_correct": is_correct,
            }
        )

    return (score, feedback), None


def _save_result_once(patient_id):
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


def _show_results(patient_id, members):
    score = st.session_state[_key("score")]
    total = st.session_state[_key("total_questions")]
    attempts = st.session_state[_key("total_attempts")]
    accuracy = score / total * 100 if total else 0.0

    try:
        _save_result_once(patient_id)
    except Exception as error:
        st.error(f"The game result could not be saved: {error}")
        return

    st.success("Family Tree Builder completed!")

    score_column, accuracy_column, attempts_column = st.columns(3)
    score_column.metric("Final Score", f"{score} / {total}")
    accuracy_column.metric("Accuracy", f"{accuracy:.1f}%")
    attempts_column.metric("Submitted Attempts", attempts)

    st.markdown("### Answer review")

    for item in st.session_state[_key("feedback")]:
        if item["is_correct"]:
            st.success(
                f'{item["selected"]} was correctly matched to '
                f'{item["relationship"]}.'
            )
        else:
            st.error(
                f'For {item["relationship"]}, you selected '
                f'{item["selected"]}. The correct name was '
                f'{item["correct"]}.'
            )

    if st.button(
        "Play Again",
        key="family_tree_play_again",
        use_container_width=True,
    ):
        _start_game(patient_id, members, force=True)
        st.rerun()


def render(patient_id, members):
    """Render a functional drag-and-drop Family Tree Builder game."""
    _ensure_state()

    st.subheader("🌳 Family Tree Builder")
    st.write(
        "Drag each family-member name from the card area into the "
        "matching relationship slot."
    )

    eligible_members = _get_eligible_members(members)

    if len(eligible_members) < 2:
        st.warning(
            "At least two family members with names and relationships "
            "are needed to play this game."
        )
        return

    _start_game(patient_id, eligible_members)

    stored_members = st.session_state[_key("members")]

    if st.session_state[_key("checked")]:
        _show_member_photos(stored_members)
        _show_results(patient_id, stored_members)
        return

    control_column, spacer_column = st.columns([1, 3])

    with control_column:
        if st.button(
            "Restart Game",
            key="family_tree_restart",
            use_container_width=True,
        ):
            _start_game(patient_id, eligible_members, force=True)
            st.rerun()

    _show_member_photos(stored_members)

    st.markdown("### Drag and match")
    st.caption(
        "Drag one name into each relationship slot. You can move a card "
        "again before checking your answers."
    )

    custom_style = """
    .sortable-component {
        font-family: Arial, sans-serif;
        font-size: 17px;
    }
    .sortable-container {
        background: #f8fafc;
        border: 2px solid #cbd5e1;
        border-radius: 12px;
        padding: 10px;
        min-width: 190px;
    }
    .sortable-container-header {
        color: #1e3a8a;
        font-weight: 700;
    }
    .sortable-item {
        background: #ffffff;
        border: 2px solid #3b82f6;
        border-radius: 9px;
        color: #1e3a8a;
        font-weight: 600;
        padding: 10px;
        margin: 7px 0;
        cursor: grab;
    }
    """

    board = sort_items(
        st.session_state[_key("board_items")],
        multi_containers=True,
        direction="horizontal",
        custom_style=custom_style,
        key=(
            f'family_tree_board_'
            f'{st.session_state[_key("board_version")]}'
        ),
    )

    st.session_state[_key("board_items")] = board

    if st.button(
        "Check Answers",
        key="family_tree_check_answers",
        type="primary",
        use_container_width=True,
    ):
        validation_result, validation_error = _validate_board(
            board,
            stored_members,
        )

        if validation_error:
            st.error(validation_error)
            return

        score, feedback = validation_result
        st.session_state[_key("score")] = score
        st.session_state[_key("total_attempts")] += 1
        st.session_state[_key("feedback")] = feedback
        st.session_state[_key("checked")] = True
        st.rerun()
