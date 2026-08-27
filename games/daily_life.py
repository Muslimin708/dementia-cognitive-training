from pathlib import Path
import random
import streamlit as st
from database import get_recent_events, save_game_result

def render(patient_id):
    if st.button('← Back to Games', key='daily_life_back'):
        st.session_state.selected_game = None; st.rerun()
    events = get_recent_events(patient_id)
    if len(events) < 2:
        st.info('At least two recent events are needed to play this game.'); return
    if st.session_state.daily_life_patient_id != patient_id:
        pool = list(events); random.shuffle(pool)
        st.session_state.daily_life_patient_id = patient_id
        st.session_state.daily_life_question_pool = pool
        st.session_state.daily_life_total_questions = len(pool)
        st.session_state.daily_life_current_event = pool.pop(0)
        st.session_state.daily_life_score = st.session_state.daily_life_attempts = st.session_state.daily_life_total_attempts = 0
        st.session_state.daily_life_first_answered = st.session_state.daily_life_question_completed = st.session_state.daily_life_result_saved = False
    event = st.session_state.daily_life_current_event
    event_id, event_name, _, _, photo_path = event
    total = st.session_state.daily_life_total_questions
    current = total - len(st.session_state.daily_life_question_pool)
    st.subheader('📖 Daily Life Story'); st.write(f'Question {current} of {total}'); st.progress(current / total)
    if Path(photo_path).exists(): st.image(photo_path, width=500)
    choices = [e[1] for e in random.sample([e for e in events if e[0] != event_id], min(3, len(events)-1))] + [event_name]
    random.shuffle(choices)
    for choice in choices:
        if st.button(choice, key=f'daily_{event_id}_{choice}'):
            st.session_state.daily_life_attempts += 1; st.session_state.daily_life_total_attempts += 1
            first = not st.session_state.daily_life_first_answered
            st.session_state.daily_life_first_answered = True
            if choice == event_name:
                if first: st.session_state.daily_life_score += 1
                st.session_state.daily_life_question_completed = True; st.success('Correct! 🎉')
            else: st.error('❌ Not quite. Try again.')
    c1, c2 = st.columns(2); c1.metric('Score', st.session_state.daily_life_score); c2.metric('Attempts', st.session_state.daily_life_attempts)
    if st.session_state.daily_life_question_completed:
        if st.session_state.daily_life_question_pool:
            if st.button('Next Question →', key='daily_next'):
                st.session_state.daily_life_current_event = st.session_state.daily_life_question_pool.pop(0)
                st.session_state.daily_life_attempts = 0; st.session_state.daily_life_first_answered = False; st.session_state.daily_life_question_completed = False; st.rerun()
        else:
            score, attempts = st.session_state.daily_life_score, st.session_state.daily_life_total_attempts
            if not st.session_state.daily_life_result_saved:
                save_game_result(patient_id, 'Daily Life Story', total, score, attempts); st.session_state.daily_life_result_saved = True
            st.success('🎉 Daily Life Story completed!'); st.write(f'Final Score: {score} / {total}'); st.write(f'Total Attempts: {attempts}')
