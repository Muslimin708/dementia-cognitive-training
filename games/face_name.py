from pathlib import Path
import streamlit as st
from database import save_game_result
from games.common import initialise_member_game, member_choices, answer, progress, metrics, next_member_question

def render(patient_id, members):
    if st.button('← Back to Games', key='face_name_back'):
        st.session_state.selected_game = None; st.rerun()
    if not members:
        st.info('No family members are available yet.'); return
    p = 'face_name'
    initialise_member_game(p, patient_id, members, st.session_state.face_name_rounds_per_member)
    member = st.session_state.face_name_current_member
    _, name, _, photo_path, _ = member
    st.subheader('👤 Face–Name Matching'); progress(p)
    if photo_path and Path(photo_path).exists(): st.image(photo_path, width=300)
    else: st.warning('This family member does not have an available photo.')
    st.write('Who is this person?')
    for choice in member_choices(members, name, 1):
        if st.button(choice, key=f'face_name_{choice}'):
            answer(p, choice == name)
    metrics(p)
    if st.session_state.face_name_question_completed:
        if st.session_state.face_name_question_pool:
            if st.button('Next Question →', key='face_name_next'): next_member_question(p)
        else:
            _finish(patient_id)

def _finish(patient_id):
    total = st.session_state.face_name_total_questions
    score = st.session_state.face_name_score
    attempts = st.session_state.face_name_total_attempts
    if not st.session_state.face_name_result_saved:
        save_game_result(patient_id, 'Face–Name Matching', total, score, attempts)
        st.session_state.face_name_result_saved = True
    st.success('🎉 Face–Name Matching completed!')
    st.write(f'Final Score: {score} / {total}')
    st.write(f'Accuracy: {(score / total * 100) if total else 0:.1f}%')
    st.write(f'Total Attempts: {attempts}')
