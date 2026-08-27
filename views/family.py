from pathlib import Path
import uuid
import streamlit as st
from components.face_annotation import render as render_face_annotation

from database import (get_patient_id, add_patient, add_family_member, update_family_member_photo,
    update_family_member_voice, get_family_members, delete_family_member, add_recent_event,
    get_recent_events, delete_recent_event, add_event_face_annotation)
from components.face_annotation import render as render_face_annotation

def _save_upload(upload, folder, prefix):
    directory = Path(folder); directory.mkdir(parents=True, exist_ok=True)
    path = directory / f'{prefix}_{uuid.uuid4().hex}{Path(upload.name).suffix.lower()}'
    path.write_bytes(upload.getbuffer()); return str(path)

def render_family_setup():
    st.header('Family Setup'); st.write("Add information about the patient's family members.")
    patient_name = st.text_input('Patient name', placeholder="Enter the patient's name")
    name = st.text_input('Family member name')
    relationship = st.selectbox('Relationship', ['Mother','Father','Daughter','Son','Sister','Brother','Spouse','Grandparent','Grandchild','Other'])
    photo = st.file_uploader('Upload family member photo', type=['jpg','jpeg','png'])
    voice = st.file_uploader('Upload family member voice recording', type=['wav','mp3','m4a'])
    if st.button('Save Family Member'):
        if not all([patient_name.strip(), name.strip(), photo, voice]): st.error('Complete all fields and upload both files.')
        else:
            patient_id = get_patient_id(patient_name.strip())
            if patient_id is None: add_patient(patient_name.strip()); patient_id = get_patient_id(patient_name.strip())
            member_id = add_family_member(patient_id, name.strip(), relationship)
            update_family_member_photo(member_id, _save_upload(photo, 'data/photos', member_id))
            update_family_member_voice(member_id, _save_upload(voice, 'data/voice', member_id))
            st.success(f'{name} has been saved successfully.')
    _saved_members(patient_name)
    st.divider(); _recent_event_form()

def _saved_members(patient_name):
    st.subheader('Saved Family Members')
    if not patient_name.strip(): return
    patient_id = get_patient_id(patient_name.strip())
    for member in get_family_members(patient_id) if patient_id else []:
        member_id,name,relationship,photo_path,voice_path = member
        with st.container(border=True):
            st.markdown(f'### {name}'); st.write(f'Relationship: {relationship}')
            if photo_path and Path(photo_path).exists(): st.image(photo_path, width=200)
            if voice_path and Path(voice_path).exists(): st.audio(Path(voice_path).read_bytes())
            if st.button(f'Delete {name}', key=f'delete_{member_id}'):
                delete_family_member(member_id); st.rerun()

def _recent_event_form():
    st.subheader('Recent Event')
    patient_name = st.text_input('Patient name for recent event', key='event_patient_name')
    event_name = st.text_input('Event', key='event_name')
    event_date = st.date_input('Event date', key='event_date')
    description = st.text_area('Description (optional)', key='event_description')
    photo = st.file_uploader('Upload recent event photo', type=['jpg','jpeg','png'], key='event_photo')
    annotations = render_face_annotation(photo) if photo else []
    patient_id = get_patient_id(patient_name.strip()) if patient_name.strip() else None
    members = get_family_members(patient_id) if patient_id else []
    selected = [m[0] for m in members if st.checkbox(f'{m[1]} ({m[2]})', key=f'event_member_{m[0]}')]
    if st.button('Save Recent Event', key='save_recent_event'):
        if not patient_id or not event_name.strip() or not photo or not selected: st.error('Provide patient, event, photo, and at least one family member.')
        else:
            path = _save_upload(photo, 'data/recent_events', patient_id)
            event_id = add_recent_event(patient_id, event_name.strip(), str(event_date), description.strip(), path, selected)
            for a in annotations:
                add_event_face_annotation(event_id, a['person_name'], a.get('description',''), a['x'], a['y'], a['width'], a['height'])
            st.success(f"Recent event '{event_name.strip()}' has been saved.")
    if patient_id:
        for event in get_recent_events(patient_id):
            event_id,name,date,desc,path = event
            with st.container(border=True):
                st.markdown(f'### 📸 {name}'); st.write(f'**Date:** {date}')
                if desc: st.write(desc)
                if path and Path(path).exists(): st.image(path, width=500)
                if st.button(f'Delete {name}', key=f'delete_event_{event_id}'):
                    if path and Path(path).exists(): Path(path).unlink()
                    delete_recent_event(event_id); st.rerun()
