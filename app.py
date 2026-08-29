import streamlit as st
from database import create_database
from views.patient import render_patient_dashboard
from views.family import render_family_setup
from views.nursing import render_nursing_dashboard

st.set_page_config(page_title='Dementia Cognitive Training App', page_icon='🧠', layout='wide')
create_database()

st.title('Dementia Cognitive Training App')
st.write('A digital cognitive training tool for early dementia.')
st.sidebar.title('Navigation')
role = st.sidebar.radio('Select your role:', ['Patient', 'Family', 'Nursing Staff'])

if role == 'Patient':
    render_patient_dashboard()
elif role == 'Family':
    render_family_setup()
else:
    render_nursing_dashboard()
