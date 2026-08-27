import random
import streamlit as st

def initialise_member_game(prefix, patient_id, members, rounds):
    if st.session_state[f'{prefix}_patient_id'] == patient_id:
        return
    pool = [member for member in members for _ in range(rounds)]
    random.shuffle(pool)
    st.session_state[f'{prefix}_patient_id'] = patient_id
    st.session_state[f'{prefix}_question_pool'] = pool
    st.session_state[f'{prefix}_total_questions'] = len(pool)
    st.session_state[f'{prefix}_current_member'] = pool.pop(0) if pool else None
    st.session_state[f'{prefix}_score'] = 0
    st.session_state[f'{prefix}_attempts'] = 0
    st.session_state[f'{prefix}_total_attempts'] = 0
    st.session_state[f'{prefix}_first_answered'] = False
    st.session_state[f'{prefix}_question_completed'] = False
    st.session_state[f'{prefix}_result_saved'] = False

def next_member_question(prefix):
    pool = st.session_state[f'{prefix}_question_pool']
    st.session_state[f'{prefix}_current_member'] = pool.pop(0)
    st.session_state[f'{prefix}_attempts'] = 0
    st.session_state[f'{prefix}_first_answered'] = False
    st.session_state[f'{prefix}_question_completed'] = False
    st.rerun()

def answer(prefix, is_correct):
    st.session_state[f'{prefix}_attempts'] += 1
    st.session_state[f'{prefix}_total_attempts'] += 1
    first = not st.session_state[f'{prefix}_first_answered']
    if first:
        st.session_state[f'{prefix}_first_answered'] = True
        if is_correct:
            st.session_state[f'{prefix}_score'] += 1
    if is_correct:
        st.session_state[f'{prefix}_question_completed'] = True
        st.success('Correct! 🎉')
    else:
        st.error('❌ Not quite. Try again.')

def member_choices(members, correct_value, field_index):
    values = list(dict.fromkeys(m[field_index] for m in members))
    alternatives = [v for v in values if v != correct_value]
    random.shuffle(alternatives)
    choices = alternatives[:3] + [correct_value]
    random.shuffle(choices)
    return choices

def progress(prefix):
    total = st.session_state[f'{prefix}_total_questions']
    current = total - len(st.session_state[f'{prefix}_question_pool'])
    st.write(f'Question {current} of {total}')
    st.progress(current / total if total else 0)

def metrics(prefix):
    c1, c2 = st.columns(2)
    c1.metric('Score', st.session_state[f'{prefix}_score'])
    c2.metric('Attempts', st.session_state[f'{prefix}_attempts'])
