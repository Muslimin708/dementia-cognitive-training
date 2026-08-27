import streamlit as st
from database import save_game_result
from games.common import initialise_member_game, member_choices, answer, progress, metrics, next_member_question

def render(patient_id, members):
    if st.button('← Back to Games', key='family_tree_back'):
        st.session_state.selected_game = None; st.rerun()
    if not members:
        st.info('No family members are available yet.'); return
    p = 'family_tree'
    initialise_member_game(p, patient_id, members, st.session_state.family_tree_rounds_per_member)
    _, name, relationship, _, _ = st.session_state.family_tree_current_member
    st.subheader('🌳 Family Tree Builder'); progress(p)
    st.write(f"What is {name}'s relationship to you?")
    for choice in member_choices(members, relationship, 2):
        if st.button(choice, key=f'family_tree_{choice}'):
            answer(p, choice == relationship)
    metrics(p)
    if st.session_state.family_tree_question_completed:
        if st.session_state.family_tree_question_pool:
            if st.button('Next Question →', key='family_tree_next'): next_member_question(p)
        else: _finish(patient_id)

def _finish(patient_id):
    total, score, attempts = st.session_state.family_tree_total_questions, st.session_state.family_tree_score, st.session_state.family_tree_total_attempts
    if not st.session_state.family_tree_result_saved:
        save_game_result(patient_id, 'Family Tree Builder', total, score, attempts); st.session_state.family_tree_result_saved = True
    st.success('🎉 Family Tree Builder completed!')
    st.write(f'Final Score: {score} / {total}')
    st.write(f'Accuracy: {(score / total * 100) if total else 0:.1f}%')
    st.write(f'Total Attempts: {attempts}')
