import streamlit as st
from database import get_all_patients, get_family_members
from state import initialize_state
from games import face_name, who_called, family_tree, missing_family, daily_life, history

def render_patient_dashboard():
    initialize_state(); st.header('Patient Dashboard')
    patients = get_all_patients()
    if not patients:
        st.warning('No patients found.'); return
    options = {p[1]: p[0] for p in patients}
    name = st.selectbox('Select patient', list(options))
    patient_id = options[name]; members = get_family_members(patient_id)
    if st.session_state.selected_game is None:
        st.write('Welcome to your cognitive training.'); st.subheader('Cognitive Training')
        c1,c2 = st.columns(2)
        buttons = [(c1,'👤 Face–Name Matching','face_name'),(c1,'🔊 Who Called?','who_called'),(c1,'🌳 Family Tree Builder','family_tree'),(c2,'👤 Missing Family Member','where_is_it'),(c2,'📖 Daily Life Story','what_happened')]
        for col,label,key in buttons:
            if col.button(label, use_container_width=True, key=f'select_{key}'):
                st.session_state.selected_game = key; st.rerun()
    elif st.session_state.selected_game == 'face_name': face_name.render(patient_id, members)
    elif st.session_state.selected_game == 'who_called': who_called.render(patient_id, members)
    elif st.session_state.selected_game == 'family_tree': family_tree.render(patient_id, members)
    elif st.session_state.selected_game == 'where_is_it': missing_family.render(patient_id)
    elif st.session_state.selected_game == 'what_happened': daily_life.render(patient_id)
    history.render(patient_id)
