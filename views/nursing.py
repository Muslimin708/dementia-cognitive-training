import pandas as pd
import streamlit as st

from database import (
    add_patient,
    get_all_patients,
    get_family_members,
    get_family_members_detailed,
    get_game_results,
)


# =====================================================
# PATIENT REGISTRATION
# =====================================================

def show_patient_registration():
    """
    Allow nursing staff to register a new patient.

    The database automatically generates a unique
    patient access code. The code can then be provided
    to the patient and authorized family members.
    """

    st.subheader("Register New Patient")

    with st.form(
        "patient_registration_form",
        clear_on_submit=True,
    ):
        patient_name = st.text_input(
            "Patient name",
            placeholder="Enter the patient's full name",
        )

        created_by = st.text_input(
            "Registered by",
            placeholder="Enter nursing staff name",
        )

        register_patient = st.form_submit_button(
            "Register Patient",
            use_container_width=True,
        )

    if register_patient:
        cleaned_patient_name = patient_name.strip()
        cleaned_created_by = created_by.strip()

        if not cleaned_patient_name:
            st.error("Please enter the patient's name.")
            return

        if not cleaned_created_by:
            cleaned_created_by = "Nursing staff"

        try:
            patient_id, patient_code = add_patient(
                name=cleaned_patient_name,
                created_by=cleaned_created_by,
            )

            st.session_state[
                "new_patient_registration"
            ] = {
                "patient_id": patient_id,
                "patient_name": cleaned_patient_name,
                "patient_code": patient_code,
                "created_by": cleaned_created_by,
            }

        except ValueError as error:
            st.error(str(error))

        except Exception as error:
            st.error(
                "The patient could not be registered. "
                f"Database error: {error}"
            )

    registration = st.session_state.get(
        "new_patient_registration"
    )

    if registration:
        st.success(
            f"Patient '{registration['patient_name']}' "
            "was registered successfully."
        )

        st.markdown("#### Patient Access Code")

        st.code(
            registration["patient_code"],
            language=None,
        )

        st.info(
            "Provide this code only to the patient and "
            "authorized family members. The patient uses "
            "it to access the games, and family members "
            "use it to add photos, voice recordings, "
            "relationships, and recent events."
        )

        col_1, col_2 = st.columns(2)

        with col_1:
            st.write(
                f"**Patient ID:** "
                f"{registration['patient_id']}"
            )

        with col_2:
            st.write(
                f"**Registered by:** "
                f"{registration['created_by']}"
            )

        if st.button(
            "Close Registration Message",
            key="close_registration_message",
        ):
            del st.session_state[
                "new_patient_registration"
            ]
            st.rerun()


# =====================================================
# PATIENT LIST
# =====================================================

def show_registered_patients(patients):
    """
    Display patients registered by nursing staff.

    Expected patient structure:
    (
        patient_id,
        patient_name,
        access_code
    )
    """

    st.subheader("Registered Patients")

    if not patients:
        st.info("No patients are currently registered.")
        return

    patient_rows = []

    for patient in patients:
        patient_id = patient[0]
        patient_name = patient[1]

        patient_code = (
            patient[2]
            if len(patient) > 2
            else "Not available"
        )

        patient_rows.append(
            {
                "Patient ID": patient_id,
                "Patient Name": patient_name,
                "Access Code": patient_code,
            }
        )

    patients_df = pd.DataFrame(patient_rows)

    st.dataframe(
        patients_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Patient ID":
                st.column_config.NumberColumn(
                    "Patient ID",
                    format="%d",
                ),
            "Patient Name":
                st.column_config.TextColumn(
                    "Patient Name",
                ),
            "Access Code":
                st.column_config.TextColumn(
                    "Access Code",
                    help=(
                        "Code used by the patient and "
                        "authorized family members."
                    ),
                ),
        },
    )

    st.caption(
        "Patient access codes should only be shared with "
        "the corresponding patient and authorized family members."
    )


# =====================================================
# GAME RESULT DATA PROCESSING
# =====================================================

def create_results_dataframe(game_results):
    """
    Convert database game results into a DataFrame.

    Expected database structure:
    (
        result_id,
        game_name,
        total_questions,
        score,
        total_attempts,
        completed_at
    )
    """

    rows = []

    for result in game_results:
        (
            result_id,
            game_name,
            total_questions,
            score,
            total_attempts,
            completed_at,
        ) = result

        total_questions = int(
            total_questions or 0
        )

        score = int(
            score or 0
        )

        total_attempts = int(
            total_attempts or 0
        )

        if total_questions > 0:
            accuracy = (
                score / total_questions * 100
            )
        else:
            accuracy = 0.0

        rows.append(
            {
                "Result ID": result_id,
                "Game": game_name,
                "Questions": total_questions,
                "Score": score,
                "Attempts": total_attempts,
                "Accuracy": accuracy,
                "Completed": completed_at,
            }
        )

    results_df = pd.DataFrame(rows)

    if not results_df.empty:
        results_df["Completed"] = pd.to_datetime(
            results_df["Completed"],
            errors="coerce",
        )

        results_df = (
            results_df
            .sort_values("Completed")
            .reset_index(drop=True)
        )

        results_df["Session"] = range(
            1,
            len(results_df) + 1,
        )

        results_df["Running Accuracy"] = (
            results_df["Accuracy"]
            .expanding()
            .mean()
        )

    return results_df


def create_game_summary(results_df):
    """
    Calculate average performance for every game.
    """

    if results_df.empty:
        return pd.DataFrame()

    game_summary = (
        results_df
        .groupby(
            "Game",
            as_index=False,
        )
        .agg(
            Sessions=("Result ID", "count"),
            Average_Score=("Score", "mean"),
            Average_Accuracy=("Accuracy", "mean"),
            Average_Attempts=("Attempts", "mean"),
        )
    )

    game_summary = game_summary.rename(
        columns={
            "Average_Score": "Average Score",
            "Average_Accuracy": "Average Accuracy",
            "Average_Attempts": "Average Attempts",
        }
    )

    game_summary["Average Score"] = (
        game_summary["Average Score"]
        .round(1)
    )

    game_summary["Average Accuracy"] = (
        game_summary["Average Accuracy"]
        .round(1)
    )

    game_summary["Average Attempts"] = (
        game_summary["Average Attempts"]
        .round(1)
    )

    return game_summary


def calculate_progress_change(results_df):
    """
    Compare the latest session accuracy with the
    previous session accuracy.
    """

    if len(results_df) < 2:
        return None

    latest_accuracy = (
        results_df.iloc[-1]["Accuracy"]
    )

    previous_accuracy = (
        results_df.iloc[-2]["Accuracy"]
    )

    return (
        latest_accuracy - previous_accuracy
    )


# =====================================================
# PATIENT PROGRESS OVERVIEW
# =====================================================

def show_overview(
    results_df,
    family_members,
):
    st.subheader("Patient Progress Overview")

    total_family_members = len(
        family_members
    )

    if results_df.empty:
        metric_col_1, metric_col_2 = st.columns(2)

        with metric_col_1:
            st.metric(
                "Registered Family Members",
                total_family_members,
            )

        with metric_col_2:
            st.metric(
                "Games Completed",
                0,
            )

        st.info(
            "No completed game sessions are available "
            "for this patient."
        )

        return

    total_sessions = len(results_df)

    average_accuracy = (
        results_df["Accuracy"].mean()
    )

    average_attempts = (
        results_df["Attempts"].mean()
    )

    latest_accuracy = (
        results_df.iloc[-1]["Accuracy"]
    )

    progress_change = (
        calculate_progress_change(results_df)
    )

    metric_col_1, metric_col_2 = st.columns(2)
    metric_col_3, metric_col_4 = st.columns(2)

    with metric_col_1:
        st.metric(
            "Games Completed",
            total_sessions,
        )

    with metric_col_2:
        st.metric(
            "Average Accuracy",
            f"{average_accuracy:.1f}%",
        )

    with metric_col_3:
        st.metric(
            "Average Attempts",
            f"{average_attempts:.1f}",
        )

    with metric_col_4:
        if progress_change is None:
            st.metric(
                "Latest Accuracy",
                f"{latest_accuracy:.1f}%",
            )
        else:
            st.metric(
                "Latest Accuracy",
                f"{latest_accuracy:.1f}%",
                delta=f"{progress_change:+.1f}%",
            )

    st.caption(
        "The change compares the latest completed "
        "session with the previous completed session."
    )

    st.divider()

    st.markdown("#### Accuracy Across Sessions")

    progress_chart = (
        results_df[
            [
                "Session",
                "Accuracy",
                "Running Accuracy",
            ]
        ]
        .set_index("Session")
    )

    st.line_chart(
        progress_chart,
        use_container_width=True,
    )

    st.caption(
        "Accuracy shows the result of each session. "
        "Running Accuracy shows the average across "
        "all sessions completed up to that point."
    )

    st.markdown("#### Score and Attempts")

    chart_col_1, chart_col_2 = st.columns(2)

    with chart_col_1:
        st.markdown("##### Score")

        score_chart = (
            results_df[
                [
                    "Session",
                    "Score",
                ]
            ]
            .set_index("Session")
        )

        st.bar_chart(
            score_chart,
            use_container_width=True,
        )

    with chart_col_2:
        st.markdown("##### Attempts")

        attempts_chart = (
            results_df[
                [
                    "Session",
                    "Attempts",
                ]
            ]
            .set_index("Session")
        )

        st.bar_chart(
            attempts_chart,
            use_container_width=True,
        )

    st.info(
        f"This patient has {total_family_members} "
        f"registered family member(s) and "
        f"{total_sessions} completed game session(s). "
        "These values describe activity in this prototype "
        "and are not a clinical assessment."
    )


# =====================================================
# GAME COMPARISON
# =====================================================

def show_game_comparison(results_df):
    st.subheader("Progress by Game")

    if results_df.empty:
        st.info(
            "No game results are available."
        )
        return

    game_summary = create_game_summary(
        results_df
    )

    st.markdown(
        "#### Average Accuracy by Game"
    )

    accuracy_chart = (
        game_summary[
            [
                "Game",
                "Average Accuracy",
            ]
        ]
        .set_index("Game")
    )

    st.bar_chart(
        accuracy_chart,
        use_container_width=True,
    )

    st.markdown(
        "#### Completed Sessions by Game"
    )

    session_chart = (
        game_summary[
            [
                "Game",
                "Sessions",
            ]
        ]
        .set_index("Game")
    )

    st.bar_chart(
        session_chart,
        use_container_width=True,
    )

    st.markdown(
        "#### Game Performance Summary"
    )

    st.dataframe(
        game_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Average Accuracy":
                st.column_config.NumberColumn(
                    "Average Accuracy",
                    format="%.1f%%",
                ),
            "Average Score":
                st.column_config.NumberColumn(
                    "Average Score",
                    format="%.1f",
                ),
            "Average Attempts":
                st.column_config.NumberColumn(
                    "Average Attempts",
                    format="%.1f",
                ),
        },
    )


# =====================================================
# GAME HISTORY
# =====================================================

def show_history(results_df):
    st.subheader("Game History")

    if results_df.empty:
        st.info(
            "No completed games are available."
        )
        return

    history_df = results_df[
        [
            "Completed",
            "Game",
            "Questions",
            "Score",
            "Attempts",
            "Accuracy",
        ]
    ].copy()

    history_df["Accuracy"] = (
        history_df["Accuracy"]
        .round(1)
    )

    history_df = history_df.sort_values(
        "Completed",
        ascending=False,
    )

    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Completed":
                st.column_config.DatetimeColumn(
                    "Completed",
                    format="DD.MM.YYYY HH:mm",
                ),
            "Accuracy":
                st.column_config.ProgressColumn(
                    "Accuracy",
                    min_value=0.0,
                    max_value=100.0,
                    format="%.1f%%",
                ),
        },
    )


# =====================================================
# FAMILY MEMBER INFORMATION
# =====================================================

def show_family_members(
    family_members,
    detailed_family_members,
):
    st.subheader("Registered Family Members")

    if not family_members:
        st.info(
            "No family members are registered "
            "for this patient."
        )
        return

    family_rows = []

    if detailed_family_members:
        for member in detailed_family_members:
            (
                member_id,
                name,
                relationship,
                email,
                photo_path,
                photo_added_at,
                photo_updated_at,
                voice_path,
                voice_added_at,
                voice_updated_at,
            ) = member

            family_rows.append(
                {
                    "ID": member_id,
                    "Name": name,
                    "Relationship": (
                        relationship or "Not provided"
                    ),
                    "Email": (
                        email or "Not provided"
                    ),
                    "Photo": (
                        "Available"
                        if photo_path
                        else "Missing"
                    ),
                    "Photo Added": photo_added_at,
                    "Photo Updated": photo_updated_at,
                    "Voice": (
                        "Available"
                        if voice_path
                        else "Missing"
                    ),
                    "Voice Added": voice_added_at,
                    "Voice Updated": voice_updated_at,
                }
            )

    else:
        for member in family_members:
            family_rows.append(
                {
                    "ID": member[0],
                    "Name": member[1],
                    "Relationship": member[2],
                    "Email": "Not available",
                    "Photo": (
                        "Available"
                        if member[3]
                        else "Missing"
                    ),
                    "Photo Added": None,
                    "Photo Updated": None,
                    "Voice": (
                        "Available"
                        if member[4]
                        else "Missing"
                    ),
                    "Voice Added": None,
                    "Voice Updated": None,
                }
            )

    family_df = pd.DataFrame(
        family_rows
    )

    date_columns = [
        "Photo Added",
        "Photo Updated",
        "Voice Added",
        "Voice Updated",
    ]

    for column in date_columns:
        family_df[column] = pd.to_datetime(
            family_df[column],
            errors="coerce",
        )

    st.dataframe(
        family_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID":
                st.column_config.NumberColumn(
                    "ID",
                    format="%d",
                ),
            "Email":
                st.column_config.TextColumn(
                    "Email",
                    help=(
                        "Email address used for future "
                        "photo refresh reminders."
                    ),
                ),
            "Photo Added":
                st.column_config.DatetimeColumn(
                    "Photo Added",
                    format="DD.MM.YYYY HH:mm",
                ),
            "Photo Updated":
                st.column_config.DatetimeColumn(
                    "Photo Updated",
                    format="DD.MM.YYYY HH:mm",
                ),
            "Voice Added":
                st.column_config.DatetimeColumn(
                    "Voice Added",
                    format="DD.MM.YYYY HH:mm",
                ),
            "Voice Updated":
                st.column_config.DatetimeColumn(
                    "Voice Updated",
                    format="DD.MM.YYYY HH:mm",
                ),
        },
    )

    family_members_with_email = sum(
        1
        for member in detailed_family_members
        if member[3]
    )

    family_members_with_photos = sum(
        1
        for member in detailed_family_members
        if member[4]
    )

    metric_col_1, metric_col_2, metric_col_3 = (
        st.columns(3)
    )

    with metric_col_1:
        st.metric(
            "Family Members",
            len(family_members),
        )

    with metric_col_2:
        st.metric(
            "Photos Available",
            family_members_with_photos,
        )

    with metric_col_3:
        st.metric(
            "Reminder Emails",
            family_members_with_email,
        )

    st.caption(
        "Photo Added records the first upload. "
        "Photo Updated records the most recent replacement. "
        "The latest photo date can be used to schedule "
        "future photo-refresh reminders."
    )


# =====================================================
# NURSING DASHBOARD
# =====================================================

def render_nursing_dashboard():
    st.header("🏥 Nursing Staff Dashboard")

    st.write(
        "Register patients and view their participation, "
        "family information, and progress across the "
        "cognitive training games."
    )

    (
        registration_tab,
        monitoring_tab,
        patient_list_tab,
    ) = st.tabs(
        [
            "➕ Register Patient",
            "📊 Patient Monitoring",
            "📋 Registered Patients",
        ]
    )

    # -------------------------------------------------
    # PATIENT REGISTRATION TAB
    # -------------------------------------------------

    with registration_tab:
        show_patient_registration()

    # Reload patients after registration
    patients = get_all_patients()

    # -------------------------------------------------
    # REGISTERED PATIENT LIST TAB
    # -------------------------------------------------

    with patient_list_tab:
        show_registered_patients(
            patients
        )

    # -------------------------------------------------
    # PATIENT MONITORING TAB
    # -------------------------------------------------

    with monitoring_tab:
        if not patients:
            st.warning(
                "No patients are registered. "
                "Register a patient from the "
                "'Register Patient' tab first."
            )
            return

        patient_options = {
            patient[0]: {
                "name": patient[1],
                "code": (
                    patient[2]
                    if len(patient) > 2
                    else "Not available"
                ),
            }
            for patient in patients
        }

        selected_patient_id = st.selectbox(
            "Select Patient",
            options=list(
                patient_options.keys()
            ),
            format_func=lambda patient_id: (
                patient_options[
                    patient_id
                ]["name"]
            ),
            key="nursing_patient_selector",
        )

        selected_patient = (
            patient_options[
                selected_patient_id
            ]
        )

        selected_patient_name = (
            selected_patient["name"]
        )

        selected_patient_code = (
            selected_patient["code"]
        )

        patient_col_1, patient_col_2 = (
            st.columns(2)
        )

        with patient_col_1:
            st.markdown(
                f"### Patient: "
                f"{selected_patient_name}"
            )

        with patient_col_2:
            st.markdown(
                "### Access Code"
            )

            st.code(
                selected_patient_code,
                language=None,
            )

        st.caption(
            "Share this access code only with the "
            "corresponding patient and authorized "
            "family members."
        )

        family_members = get_family_members(
            selected_patient_id
        )

        try:
            detailed_family_members = (
                get_family_members_detailed(
                    selected_patient_id
                )
            )
        except Exception:
            detailed_family_members = []

        game_results = get_game_results(
            selected_patient_id
        )

        results_df = create_results_dataframe(
            game_results
        )

        (
            overview_tab,
            comparison_tab,
            history_tab,
            family_tab,
        ) = st.tabs(
            [
                "📊 Progress Overview",
                "🎮 Game Comparison",
                "📋 Game History",
                "👪 Family Members",
            ]
        )

        with overview_tab:
            show_overview(
                results_df,
                family_members,
            )

        with comparison_tab:
            show_game_comparison(
                results_df
            )

        with history_tab:
            show_history(
                results_df
            )

        with family_tab:
            show_family_members(
                family_members,
                detailed_family_members,
            )

        st.divider()

        st.caption(
            "This dashboard summarizes performance in the "
            "cognitive training prototype. It is not intended "
            "to provide a diagnosis or replace professional "
            "clinical assessment."
        )