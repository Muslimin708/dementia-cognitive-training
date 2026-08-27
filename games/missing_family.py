from pathlib import Path
import random
import streamlit as st
from PIL import Image, ImageFilter
from database import get_recent_events, get_event_face_annotations

def render(patient_id):
    if st.button('← Back to Games', key='missing_back'):
        st.session_state.selected_game = None; st.rerun()
    annotated = [e for e in get_recent_events(patient_id) if get_event_face_annotations(e[0])]
    if not annotated:
        st.info('No recent event photos with identified people are available.'); return
    if st.session_state.missing_family_patient_id != patient_id:
        random.shuffle(annotated)
        st.session_state.missing_family_patient_id = patient_id
        st.session_state.missing_family_question_pool = annotated
        st.session_state.missing_family_total_questions = len(annotated)
        st.session_state.missing_family_current_event = annotated.pop(0)
        st.session_state.missing_family_person = None
        st.session_state.missing_family_score = st.session_state.missing_family_attempts = st.session_state.missing_family_total_attempts = 0
        st.session_state.missing_family_first_answered = st.session_state.missing_family_answered = False
    event = st.session_state.missing_family_current_event
    event_id, event_name, _, _, photo_path = event
    annotations = get_event_face_annotations(event_id)
    if st.session_state.missing_family_person is None:
        st.session_state.missing_family_person = random.choice(annotations)
    missing = st.session_state.missing_family_person
    _, name, _, x, y, w, h = missing
    st.subheader('👤 Missing Family Member'); st.write(f'Event: {event_name}')
    image = Image.open(Path(photo_path)).convert('RGB')
    iw, ih = image.size; cx, cy, fw, fh = int(x*iw), int(y*ih), int(w*iw), int(h*ih)
    box = (max(0,cx-fw//2), max(0,cy-fh//2), min(iw,cx+fw//2), min(ih,cy+fh//2))
    image.paste(image.crop(box).filter(ImageFilter.GaussianBlur(max(8, int(min(fw,fh)*.15)))), box[:2])
    st.image(image, width=500)
    options = [missing] + random.sample([a for a in annotations if a != missing], min(4, len(annotations)-1)); random.shuffle(options)
    selected = st.radio('Who is missing from this picture?', [a[1] for a in options], key=f'missing_{event_id}')
    if st.button('Check Answer', key=f'missing_check_{event_id}'):
        st.session_state.missing_family_attempts += 1; st.session_state.missing_family_total_attempts += 1
        first = not st.session_state.missing_family_first_answered; st.session_state.missing_family_first_answered = True
        if selected == name:
            if first: st.session_state.missing_family_score += 1
            st.session_state.missing_family_answered = True; st.success('Correct! 🎉')
        else: st.error('Not quite. Try again.')
    st.write(f"Score: {st.session_state.missing_family_score}")
    st.write(f"Attempts: {st.session_state.missing_family_attempts}")
    if st.session_state.missing_family_answered and st.session_state.missing_family_question_pool:
        if st.button('Next Question →', key='missing_next'):
            st.session_state.missing_family_current_event = st.session_state.missing_family_question_pool.pop(0)
            st.session_state.missing_family_person = None; st.session_state.missing_family_attempts = 0
            st.session_state.missing_family_first_answered = st.session_state.missing_family_answered = False; st.rerun()
    elif st.session_state.missing_family_answered:
        st.success('🎉 Missing Family Member game completed!')
