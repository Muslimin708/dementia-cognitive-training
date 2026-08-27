import streamlit as st

DEFAULTS = {
    'selected_game': None,
    'face_name_patient_id': None, 'face_name_score': 0, 'face_name_attempts': 0,
    'face_name_total_attempts': 0, 'face_name_first_answered': False,
    'face_name_question_completed': False, 'face_name_rounds_per_member': 2,
    'face_name_question_pool': [], 'face_name_total_questions': 0,
    'face_name_current_member': None, 'face_name_result_saved': False,
    'who_called_patient_id': None, 'who_called_score': 0, 'who_called_attempts': 0,
    'who_called_total_attempts': 0, 'who_called_first_answered': False,
    'who_called_question_completed': False, 'who_called_rounds_per_member': 2,
    'who_called_question_pool': [], 'who_called_total_questions': 0,
    'who_called_current_member': None, 'who_called_result_saved': False,
    'family_tree_patient_id': None, 'family_tree_score': 0, 'family_tree_attempts': 0,
    'family_tree_total_attempts': 0, 'family_tree_first_answered': False,
    'family_tree_question_completed': False, 'family_tree_rounds_per_member': 1,
    'family_tree_question_pool': [], 'family_tree_total_questions': 0,
    'family_tree_current_member': None, 'family_tree_result_saved': False,
    'missing_family_patient_id': None, 'missing_family_question_pool': [],
    'missing_family_total_questions': 0, 'missing_family_current_event': None,
    'missing_family_person': None, 'missing_family_score': 0,
    'missing_family_attempts': 0, 'missing_family_total_attempts': 0,
    'missing_family_first_answered': False, 'missing_family_answered': False,
    'daily_life_patient_id': None, 'daily_life_score': 0, 'daily_life_attempts': 0,
    'daily_life_total_attempts': 0, 'daily_life_first_answered': False,
    'daily_life_question_completed': False, 'daily_life_question_pool': [],
    'daily_life_total_questions': 0, 'daily_life_current_event': None,
    'daily_life_result_saved': False,
}

def initialize_state():
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, list) else value

def reset_prefix(prefix: str):
    for key, value in DEFAULTS.items():
        if key.startswith(prefix):
            st.session_state[key] = value.copy() if isinstance(value, list) else value
