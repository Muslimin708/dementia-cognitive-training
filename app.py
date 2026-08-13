import streamlit as st
from pathlib import Path
import uuid

from database import (
    create_database,
    get_patient_id,
    add_patient,
    add_family_member,
    update_family_member_photo,
    update_family_member_voice,
    get_family_members,
    delete_family_member
)

# Make sure the database exists
create_database()


st.set_page_config(
    page_title="Dementia Cognitive Training App",
    page_icon="🧠",
    layout="wide"
)

st.title("Dementia Cognitive Training App")
st.write("A digital cognitive training tool for early dementia.")

st.sidebar.title("Navigation")

role = st.sidebar.radio(
    "Select your role:",
    ["Patient", "Family", "Nursing Staff"]
)

if role == "Patient":
    st.header("Patient")
    st.write("Cognitive training games will appear here.")

elif role == "Family":
    st.header("Family Setup")

    st.write(
        "Add information about the patient's family members."
    )

    st.subheader("Patient Information")

    patient_name = st.text_input(
        "Patient name",
        placeholder="Enter the patient's name"
    )

    st.subheader("Family Member")

    family_member_name = st.text_input(
        "Family member name",
        placeholder="Enter the family member's name"
    )

    relationship = st.selectbox(
        "Relationship",
        [
            "Mother",
            "Father",
            "Daughter",
            "Son",
            "Sister",
            "Brother",
            "Spouse",
            "Grandparent",
            "Grandchild",
            "Other"
        ]
    )

    photo = st.file_uploader(
    "Upload family member photo",
    type=["jpg", "jpeg", "png"]
)

    voice = st.file_uploader(
    "Upload family member voice recording",
    type=["wav", "mp3", "m4a"]
)

if st.button("Save Family Member"):

    if not patient_name.strip():
        st.error("Please enter the patient's name.")

    elif not family_member_name.strip():
        st.error("Please enter the family member's name.")

    elif photo is None:
        st.error("Please upload a photo.")
    
    elif voice is None:
        st.error("Please upload a voice recording.")
    
    else:
        patient_id = get_patient_id(patient_name.strip())

        if patient_id is None:
            add_patient(patient_name.strip())
            patient_id = get_patient_id(patient_name.strip())

        family_member_id = add_family_member(
            patient_id,
            family_member_name.strip(),
            relationship
        )

        photo_directory = Path("data/photos")
        photo_directory.mkdir(parents=True, exist_ok=True)

        file_extension = Path(photo.name).suffix.lower()

        unique_filename = (
            f"{family_member_id}_{uuid.uuid4().hex}{file_extension}"
        )

        photo_path = photo_directory / unique_filename

        with open(photo_path, "wb") as file:
            file.write(photo.getbuffer())

        update_family_member_photo(
            family_member_id,
            str(photo_path)
        )

# Save the voice recording
        voice_directory = Path("data/voice")
        voice_directory.mkdir(parents=True, exist_ok=True)

        voice_extension = Path(voice.name).suffix.lower()

        voice_filename = (
            f"{family_member_id}_{uuid.uuid4().hex}{voice_extension}"
        )

        voice_path = voice_directory / voice_filename

        with open(voice_path, "wb") as file:
            file.write(voice.getbuffer())
        
        update_family_member_voice(
            family_member_id,
            str(voice_path)
        )

        st.success(
            f"{family_member_name}, photo, and voice recording "
            "have been saved successfully."
        )

        st.image(
            photo,
            caption=family_member_name
        )

        st.audio(
            voice,
            format=voice.type
        )

st.divider()

st.subheader("Saved Family Members")

if patient_name.strip():
    patient_id = get_patient_id(patient_name.strip())

    if patient_id is None:
        st.info("No family members have been added yet.")

    else:
        family_members = get_family_members(patient_id)

        if not family_members:
            st.info("No family members have been added yet.")

        else:
            for member in family_members:
                member_id, name, relationship, photo_path, voice_path = member
                st.markdown(f"### {name}")
                st.write(f"Relationship: {relationship}")

                if photo_path:
                    photo_file = Path(photo_path)

                    if photo_file.exists():
                        st.image(
                            str(photo_file),
                            width=200
                        )
                    else:
                        st.warning("Photo file could not be found.")

                if voice_path:
                    voice_file = Path(voice_path)

                    if voice_file.exists():
                        with open(voice_file, "rb") as audio_file:
                            st.audio(audio_file.read())
                    else:
                        st.warning("Voice file could not be found.")

                if st.button(
                    f"Delete {name}",
                    key=f"delete_{member_id}"
                ):
                    delete_family_member(member_id)

                    st.success(
                        f"{name} has been deleted."
                    )

                    st.rerun()

                st.divider()

elif role == "Nursing Staff":
    st.header("Nursing Staff")
    st.write("The nursing staff dashboard will appear here.")