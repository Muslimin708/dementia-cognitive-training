import pandas as pd
import streamlit as st

from database import (
    get_all_patients,
    get_family_members,
    get_game_results,
)


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

        total_questions = int(total_questions or 0)
        score = int(score or 0)
        total_attempts = int(total_attempts or 0)

        if total_questions > 0:
            accuracy = score / total_questions * 100
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
        game_summary["Average Score"].round(1)
    )

    game_summary["Average Accuracy"] = (
        game_summary["Average Accuracy"].round(1)
    )

    game_summary["Average Attempts"] = (
        game_summary["Average Attempts"].round(1)
    )

    return game_summary


def calculate_progress_change(results_df):
    """
    Compare the latest session accuracy with the
    previous session accuracy.
    """

    if len(results_df) < 2:
        return None

    latest_accuracy = results_df.iloc[-1]["Accuracy"]
    previous_accuracy = results_df.iloc[-2]["Accuracy"]

    return latest_accuracy - previous_accuracy


def show_overview(
    results_df,
    family_members,
):
    st.subheader("Patient Progress Overview")

    if results_df.empty:
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

    progress_change = calculate_progress_change(
        results_df
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
        f"This patient has {len(family_members)} registered "
        f"family member(s) and {total_sessions} completed "
        "game session(s). These values describe activity "
        "in this prototype and are not a clinical assessment."
    )


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

    st.markdown("#### Average Accuracy by Game")

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

    st.markdown("#### Completed Sessions by Game")

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

    st.markdown("#### Game Performance Summary")

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
        history_df["Accuracy"].round(1)
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


def show_family_members(family_members):
    st.subheader("Registered Family Members")

    if not family_members:
        st.info(
            "No family members are registered "
            "for this patient."
        )
        return

    family_df = pd.DataFrame(
        [
            {
                "Name": member[1],
                "Relationship": member[2],
                "Photo Available": (
                    "Yes" if member[3] else "No"
                ),
                "Voice Available": (
                    "Yes" if member[4] else "No"
                ),
            }
            for member in family_members
        ]
    )

    st.dataframe(
        family_df,
        use_container_width=True,
        hide_index=True,
    )


def render_nursing_dashboard():
    st.header("🏥 Nursing Staff Dashboard")

    st.write(
        "View patient participation and progress "
        "across the cognitive training games."
    )

    patients = get_all_patients()

    if not patients:
        st.warning(
            "No patients are registered. Add a patient "
            "from the Family section first."
        )
        return

    patient_options = {
        patient[0]: patient[1]
        for patient in patients
    }

    selected_patient_id = st.selectbox(
        "Select Patient",
        options=list(patient_options.keys()),
        format_func=lambda patient_id: (
            patient_options[patient_id]
        ),
        key="nursing_patient_selector",
    )

    selected_patient_name = (
        patient_options[selected_patient_id]
    )

    family_members = get_family_members(
        selected_patient_id
    )

    game_results = get_game_results(
        selected_patient_id
    )

    results_df = create_results_dataframe(
        game_results
    )

    st.subheader(
        f"Patient: {selected_patient_name}"
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
            family_members
        )

    st.divider()

    st.caption(
        "This dashboard summarizes performance in the "
        "cognitive training prototype. It is not intended "
        "to provide a diagnosis or replace professional "
        "clinical assessment."
    )