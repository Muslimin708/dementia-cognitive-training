import pandas as pd
import streamlit as st

from database import (
    get_all_patients,
    get_family_members,
    get_recognition_results,
    get_memory_scores,
)


# ============================================================
# CALCULATION FUNCTIONS
# ============================================================

def calculate_recognition_statistics(results):
    """
    Calculate recognition exercise statistics.

    Expected result structure:
    (
        family_member_id,
        correct,
        created_at
    )
    """

    total_attempts = len(results)

    correct_answers = sum(
        1
        for _, correct, _ in results
        if int(correct) == 1
    )

    incorrect_answers = (
        total_attempts - correct_answers
    )

    if total_attempts > 0:
        accuracy = (
            correct_answers / total_attempts
        ) * 100
    else:
        accuracy = 0.0

    return (
        total_attempts,
        correct_answers,
        incorrect_answers,
        accuracy,
    )


def calculate_memory_statistics(memory_scores):
    """
    Calculate memory exercise statistics.

    Expected score structure:
    (
        score,
        created_at
    )
    """

    if not memory_scores:
        return 0, 0, 0.0

    scores = [
        int(score)
        for score, _ in memory_scores
    ]

    latest_score = scores[0]
    highest_score = max(scores)
    average_score = sum(scores) / len(scores)

    return (
        latest_score,
        highest_score,
        average_score,
    )


def calculate_overall_performance(
    recognition_accuracy,
    average_memory_score,
    has_recognition_data,
    has_memory_data,
):
    """
    Calculate a descriptive combined performance percentage.

    This value is not a clinical or diagnostic score.
    """

    memory_percentage = (
        average_memory_score / 3
    ) * 100

    if has_recognition_data and has_memory_data:
        overall_score = (
            recognition_accuracy * 0.7
            + memory_percentage * 0.3
        )

    elif has_recognition_data:
        overall_score = recognition_accuracy

    elif has_memory_data:
        overall_score = memory_percentage

    else:
        overall_score = 0.0

    return overall_score, memory_percentage


# ============================================================
# DATAFRAME CREATION FUNCTIONS
# ============================================================

def create_recognition_dataframe(
    recognition_results,
    family_member_names,
):
    """
    Convert recognition results to a pandas DataFrame.
    """

    rows = []

    for (
        family_member_id,
        correct,
        created_at,
    ) in recognition_results:

        numeric_result = int(correct)

        rows.append(
            {
                "Date": created_at,
                "Family Member": (
                    family_member_names.get(
                        family_member_id,
                        "Deleted family member",
                    )
                ),
                "Result": (
                    "Correct"
                    if numeric_result == 1
                    else "Incorrect"
                ),
                "Score": numeric_result,
            }
        )

    recognition_df = pd.DataFrame(rows)

    if not recognition_df.empty:
        recognition_df["Date"] = pd.to_datetime(
            recognition_df["Date"],
            errors="coerce",
        )

        recognition_df = (
            recognition_df
            .dropna(subset=["Date"])
            .sort_values("Date")
            .reset_index(drop=True)
        )

        recognition_df["Attempt"] = range(
            1,
            len(recognition_df) + 1,
        )

        recognition_df["Cumulative Accuracy"] = (
            recognition_df["Score"]
            .expanding()
            .mean()
            * 100
        )

    return recognition_df


def create_memory_dataframe(memory_scores):
    """
    Convert memory exercise results to a pandas DataFrame.
    """

    rows = []

    for score, created_at in memory_scores:
        rows.append(
            {
                "Date": created_at,
                "Score": int(score),
            }
        )

    memory_df = pd.DataFrame(rows)

    if not memory_df.empty:
        memory_df["Date"] = pd.to_datetime(
            memory_df["Date"],
            errors="coerce",
        )

        memory_df = (
            memory_df
            .dropna(subset=["Date"])
            .sort_values("Date")
            .reset_index(drop=True)
        )

        memory_df["Session"] = range(
            1,
            len(memory_df) + 1,
        )

        memory_df["Average Score"] = (
            memory_df["Score"]
            .expanding()
            .mean()
        )

    return memory_df


def create_family_performance_dataframe(
    recognition_df,
):
    """
    Calculate recognition performance for each family member.
    """

    if recognition_df.empty:
        return pd.DataFrame()

    performance_df = (
        recognition_df
        .groupby(
            "Family Member",
            as_index=False,
        )
        .agg(
            Attempts=("Score", "count"),
            Correct=("Score", "sum"),
        )
    )

    performance_df["Incorrect"] = (
        performance_df["Attempts"]
        - performance_df["Correct"]
    )

    performance_df["Accuracy"] = (
        performance_df["Correct"]
        / performance_df["Attempts"]
        * 100
    ).round(1)

    performance_df = performance_df.sort_values(
        by="Accuracy",
        ascending=True,
    )

    return performance_df


# ============================================================
# VISUALIZATION FUNCTIONS
# ============================================================

def show_recognition_visualizations(
    recognition_df,
    correct_answers,
    incorrect_answers,
):
    """
    Display recognition charts and history.
    """

    st.subheader("Recognition Performance")

    if recognition_df.empty:
        st.info(
            "No recognition exercise data is available."
        )
        return

    chart_col_1, chart_col_2 = st.columns(2)

    with chart_col_1:
        st.markdown(
            "#### Correct and Incorrect Answers"
        )

        result_totals = pd.DataFrame(
            {
                "Result": [
                    "Correct",
                    "Incorrect",
                ],
                "Number of Answers": [
                    correct_answers,
                    incorrect_answers,
                ],
            }
        )

        st.bar_chart(
            result_totals.set_index("Result")
        )

    with chart_col_2:
        st.markdown(
            "#### Recognition Accuracy Trend"
        )

        trend_df = (
            recognition_df[
                [
                    "Attempt",
                    "Cumulative Accuracy",
                ]
            ]
            .set_index("Attempt")
        )

        st.line_chart(trend_df)

    st.markdown(
        "#### Recognition Results Over Time"
    )

    attempt_df = (
        recognition_df[
            [
                "Attempt",
                "Score",
            ]
        ]
        .set_index("Attempt")
    )

    st.line_chart(attempt_df)

    st.caption(
        "A score of 1 means the answer was correct. "
        "A score of 0 means the answer was incorrect."
    )

    st.markdown(
        "#### Performance by Family Member"
    )

    family_performance_df = (
        create_family_performance_dataframe(
            recognition_df
        )
    )

    if not family_performance_df.empty:
        family_accuracy_chart = (
            family_performance_df[
                [
                    "Family Member",
                    "Accuracy",
                ]
            ]
            .set_index("Family Member")
        )

        st.bar_chart(family_accuracy_chart)

        st.dataframe(
            family_performance_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Accuracy": st.column_config.NumberColumn(
                    "Accuracy",
                    format="%.1f%%",
                ),
            },
        )

    st.markdown(
        "#### Recognition History"
    )

    display_recognition_df = recognition_df[
        [
            "Date",
            "Family Member",
            "Result",
            "Cumulative Accuracy",
        ]
    ].copy()

    display_recognition_df[
        "Cumulative Accuracy"
    ] = display_recognition_df[
        "Cumulative Accuracy"
    ].round(1)

    st.dataframe(
        display_recognition_df.sort_values(
            "Date",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date": st.column_config.DatetimeColumn(
                "Date",
                format="DD.MM.YYYY HH:mm",
            ),
            "Cumulative Accuracy":
                st.column_config.NumberColumn(
                    "Cumulative Accuracy",
                    format="%.1f%%",
                ),
        },
    )


def show_memory_visualizations(memory_df):
    """
    Display memory score charts and history.
    """

    st.subheader("Memory Exercise Performance")

    if memory_df.empty:
        st.info(
            "No memory exercise data is available."
        )
        return

    chart_col_1, chart_col_2 = st.columns(2)

    with chart_col_1:
        st.markdown(
            "#### Memory Score by Session"
        )

        score_chart_df = (
            memory_df[
                [
                    "Session",
                    "Score",
                ]
            ]
            .set_index("Session")
        )

        st.line_chart(score_chart_df)

    with chart_col_2:
        st.markdown(
            "#### Score and Running Average"
        )

        average_chart_df = (
            memory_df[
                [
                    "Session",
                    "Score",
                    "Average Score",
                ]
            ]
            .set_index("Session")
        )

        st.line_chart(average_chart_df)

    st.markdown(
        "#### Memory Score Distribution"
    )

    score_distribution = (
        memory_df["Score"]
        .value_counts()
        .reindex(
            [0, 1, 2, 3],
            fill_value=0,
        )
        .rename_axis("Score")
        .reset_index(name="Number of Sessions")
    )

    st.bar_chart(
        score_distribution.set_index("Score")
    )

    st.markdown(
        "#### Memory Exercise History"
    )

    display_memory_df = memory_df[
        [
            "Date",
            "Score",
            "Average Score",
        ]
    ].copy()

    display_memory_df[
        "Average Score"
    ] = display_memory_df[
        "Average Score"
    ].round(2)

    display_memory_df["Maximum Score"] = 3

    st.dataframe(
        display_memory_df.sort_values(
            "Date",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date": st.column_config.DatetimeColumn(
                "Date",
                format="DD.MM.YYYY HH:mm",
            ),
            "Score": st.column_config.ProgressColumn(
                "Score",
                min_value=0,
                max_value=3,
                format="%d",
            ),
            "Average Score":
                st.column_config.NumberColumn(
                    "Average Score",
                    format="%.2f",
                ),
        },
    )


def show_overall_visualizations(
    recognition_accuracy,
    memory_percentage,
    overall_performance,
    has_recognition_data,
    has_memory_data,
):
    """
    Display overall descriptive performance charts.
    """

    st.subheader("Overall Performance Overview")

    if (
        not has_recognition_data
        and not has_memory_data
    ):
        st.info(
            "There is not enough exercise data to "
            "display an overall performance overview."
        )
        return

    comparison_rows = []

    if has_recognition_data:
        comparison_rows.append(
            {
                "Exercise": "Recognition",
                "Performance": recognition_accuracy,
            }
        )

    if has_memory_data:
        comparison_rows.append(
            {
                "Exercise": "Memory",
                "Performance": memory_percentage,
            }
        )

    comparison_df = pd.DataFrame(
        comparison_rows
    )

    overview_col_1, overview_col_2 = (
        st.columns([1, 2])
    )

    with overview_col_1:
        st.metric(
            "Combined Exercise Performance",
            f"{overall_performance:.1f}%",
        )

        st.progress(
            min(
                max(
                    overall_performance / 100,
                    0.0,
                ),
                1.0,
            )
        )

    with overview_col_2:
        st.markdown(
            "#### Exercise Comparison"
        )

        st.bar_chart(
            comparison_df.set_index("Exercise")
        )

    st.info(
        "The combined percentage is a descriptive "
        "summary of exercise performance. It is not "
        "a validated clinical score or diagnosis."
    )


def show_recent_activity(
    recognition_df,
    memory_df,
):
    """
    Combine recognition and memory activity.
    """

    st.subheader("Recent Patient Activity")

    activities = []

    if not recognition_df.empty:
        for _, row in recognition_df.iterrows():
            activities.append(
                {
                    "Date": row["Date"],
                    "Activity": (
                        "Family Recognition"
                    ),
                    "Details": (
                        f'{row["Family Member"]}: '
                        f'{row["Result"]}'
                    ),
                }
            )

    if not memory_df.empty:
        for _, row in memory_df.iterrows():
            activities.append(
                {
                    "Date": row["Date"],
                    "Activity": "Memory Exercise",
                    "Details": (
                        f'{int(row["Score"])} out of 3'
                    ),
                }
            )

    if not activities:
        st.info(
            "No patient activity has been recorded."
        )
        return

    activity_df = pd.DataFrame(activities)

    activity_df = activity_df.sort_values(
        "Date",
        ascending=False,
    ).head(10)

    st.dataframe(
        activity_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date": st.column_config.DatetimeColumn(
                "Date",
                format="DD.MM.YYYY HH:mm",
            ),
        },
    )


# ============================================================
# MAIN NURSING DASHBOARD
# ============================================================

def show_nursing_dashboard():
    """
    Display the nursing staff patient-progress dashboard.
    """

    st.header("🏥 Nursing Staff Dashboard")

    st.write(
        "Review patient exercise activity, recognition "
        "performance, memory scores, and historical trends."
    )

    patients = get_all_patients()

    if not patients:
        st.info(
            "No patients are currently registered."
        )
        return

    patient_options = {
        patient_id: patient_name
        for patient_id, patient_name in patients
    }

    selected_patient_id = st.selectbox(
        "Select Patient",
        options=list(patient_options.keys()),
        format_func=lambda patient_id: (
            patient_options[patient_id]
        ),
        key="nursing_dashboard_patient",
    )

    selected_patient_name = patient_options[
        selected_patient_id
    ]

    st.subheader(
        f"Patient: {selected_patient_name}"
    )

    # --------------------------------------------------------
    # LOAD PATIENT DATA
    # --------------------------------------------------------

    family_members = get_family_members(
        selected_patient_id
    )

    recognition_results = (
        get_recognition_results(
            selected_patient_id
        )
    )

    memory_scores = get_memory_scores(
        selected_patient_id
    )

    family_member_names = {
        member[0]: member for member in family_members
    }


    recognition_df = (
        create_recognition_dataframe(
            recognition_results,
            family_member_names,
        )
    )

    memory_df = create_memory_dataframe(
        memory_scores
    )

    # --------------------------------------------------------
    # CALCULATE STATISTICS
    # --------------------------------------------------------

    (
        total_attempts,
        correct_answers,
        incorrect_answers,
        recognition_accuracy,
    ) = calculate_recognition_statistics(
        recognition_results
    )

    (
        latest_memory_score,
        highest_memory_score,
        average_memory_score,
    ) = calculate_memory_statistics(
        memory_scores
    )

    has_recognition_data = (
        len(recognition_results) > 0
    )

    has_memory_data = len(memory_scores) > 0

    (
        overall_performance,
        memory_percentage,
    ) = calculate_overall_performance(
        recognition_accuracy,
        average_memory_score,
        has_recognition_data,
        has_memory_data,
    )

    # --------------------------------------------------------
    # PATIENT OVERVIEW
    # --------------------------------------------------------

    st.subheader("Patient Overview")

    metric_col_1, metric_col_2, metric_col_3 = (
        st.columns(3)
    )

    with metric_col_1:
        st.metric(
            "Recognition Accuracy",
            (
                f"{recognition_accuracy:.1f}%"
                if has_recognition_data
                else "No data"
            ),
        )

    with metric_col_2:
        st.metric(
            "Recognition Attempts",
            total_attempts,
        )

    with metric_col_3:
        st.metric(
            "Registered Family Members",
            len(family_members),
        )

    metric_col_4, metric_col_5, metric_col_6 = (
        st.columns(3)
    )

    with metric_col_4:
        st.metric(
            "Latest Memory Score",
            (
                f"{latest_memory_score}/3"
                if has_memory_data
                else "No data"
            ),
        )

    with metric_col_5:
        st.metric(
            "Highest Memory Score",
            (
                f"{highest_memory_score}/3"
                if has_memory_data
                else "No data"
            ),
        )

    with metric_col_6:
        st.metric(
            "Average Memory Score",
            (
                f"{average_memory_score:.1f}/3"
                if has_memory_data
                else "No data"
            ),
        )

    # --------------------------------------------------------
    # DATA AVAILABILITY STATUS
    # --------------------------------------------------------

    if (
        not has_recognition_data
        and not has_memory_data
    ):
        st.warning(
            "No exercises have been completed for this "
            "patient. Progress visualizations will appear "
            "after exercise results have been recorded."
        )

    elif (
        not has_recognition_data
        or not has_memory_data
    ):
        st.info(
            "Only partial exercise data is available. "
            "Complete both recognition and memory exercises "
            "for a more complete progress overview."
        )

    else:
        st.success(
            "Recognition and memory exercise data are "
            "available for this patient."
        )

    # --------------------------------------------------------
    # DASHBOARD TABS
    # --------------------------------------------------------

    (
        overview_tab,
        recognition_tab,
        memory_tab,
        family_tab,
        activity_tab,
    ) = st.tabs(
        [
            "Overview",
            "Recognition",
            "Memory",
            "Family Members",
            "Recent Activity",
        ]
    )

    # --------------------------------------------------------
    # OVERVIEW TAB
    # --------------------------------------------------------

    with overview_tab:
        show_overall_visualizations(
            recognition_accuracy,
            memory_percentage,
            overall_performance,
            has_recognition_data,
            has_memory_data,
        )

        st.divider()

        overview_chart_col_1, overview_chart_col_2 = (
            st.columns(2)
        )

        with overview_chart_col_1:
            st.markdown(
                "#### Recognition Summary"
            )

            if has_recognition_data:
                recognition_summary = pd.DataFrame(
                    {
                        "Result": [
                            "Correct",
                            "Incorrect",
                        ],
                        "Attempts": [
                            correct_answers,
                            incorrect_answers,
                        ],
                    }
                )

                st.bar_chart(
                    recognition_summary.set_index(
                        "Result"
                    )
                )
            else:
                st.info(
                    "No recognition results."
                )

        with overview_chart_col_2:
            st.markdown(
                "#### Memory Summary"
            )

            if has_memory_data:
                memory_summary = pd.DataFrame(
                    {
                        "Measure": [
                            "Latest",
                            "Highest",
                            "Average",
                        ],
                        "Score": [
                            latest_memory_score,
                            highest_memory_score,
                            average_memory_score,
                        ],
                    }
                )

                st.bar_chart(
                    memory_summary.set_index(
                        "Measure"
                    )
                )
            else:
                st.info(
                    "No memory exercise results."
                )

    # --------------------------------------------------------
    # RECOGNITION TAB
    # --------------------------------------------------------

    with recognition_tab:
        show_recognition_visualizations(
            recognition_df,
            correct_answers,
            incorrect_answers,
        )

    # --------------------------------------------------------
    # MEMORY TAB
    # --------------------------------------------------------

    with memory_tab:
        show_memory_visualizations(
            memory_df
        )

    # --------------------------------------------------------
    # FAMILY MEMBERS TAB
    # --------------------------------------------------------

    with family_tab:
        st.subheader(
            "Registered Family Members"
        )

        if family_members:
            family_df = pd.DataFrame(
                [
                    {
                        "Name": member[1],
                        "Relationship": member[2],
                        "Photo Available": (
                            "Yes"
                            if member[3]
                            else "No"
                        ),
                        "Voice Available": (
                            "Yes"
                            if member[4]
                            else "No"
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

        else:
            st.info(
                "No family members are registered "
                "for this patient."
            )

    # --------------------------------------------------------
    # RECENT ACTIVITY TAB
    # --------------------------------------------------------

    with activity_tab:
        show_recent_activity(
            recognition_df,
            memory_df,
        )

    st.divider()

    st.caption(
        "These visualizations summarize activity recorded "
        "by this prototype. They are not a medical diagnosis "
        "and should be interpreted alongside professional "
        "clinical assessment."
    )