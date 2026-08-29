
from datetime import datetime

import pandas as pd
import streamlit as st

from database import get_game_results


def _format_completed_at(value):
    """Convert a database timestamp into a readable date and time."""
    if value is None:
        return "Not available"

    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")

    text = str(value).strip()
    if not text:
        return "Not available"

    supported_formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    )

    for date_format in supported_formats:
        try:
            completed_at = datetime.strptime(text, date_format)
            return completed_at.strftime("%d.%m.%Y %H:%M")
        except ValueError:
            continue

    return text


def _normalise_results(results):
    """Validate database rows and convert them into dictionaries."""
    normalised_results = []

    for result in results or []:
        if not isinstance(result, (list, tuple)) or len(result) < 6:
            continue

        (
            result_id,
            game_name,
            total_questions,
            score,
            total_attempts,
            completed_at,
        ) = result[:6]

        try:
            result_id = int(result_id or 0)
        except (TypeError, ValueError):
            result_id = 0

        try:
            total_questions = int(total_questions or 0)
        except (TypeError, ValueError):
            total_questions = 0

        try:
            score = int(score or 0)
        except (TypeError, ValueError):
            score = 0

        try:
            total_attempts = int(total_attempts or 0)
        except (TypeError, ValueError):
            total_attempts = 0

        if total_questions > 0:
            accuracy = score / total_questions * 100
        else:
            accuracy = 0.0

        normalised_results.append(
            {
                "result_id": result_id,
                "game_name": game_name or "Unknown Game",
                "total_questions": total_questions,
                "score": score,
                "total_attempts": total_attempts,
                "accuracy": accuracy,
                "completed_at": completed_at,
                "completed_display": _format_completed_at(completed_at),
            }
        )

    return normalised_results


def _show_overall_summary(results):
    """Display summary metrics across all completed sessions."""
    session_count = len(results)
    if session_count == 0:
        return

    average_accuracy = (
        sum(result["accuracy"] for result in results) / session_count
    )
    average_attempts = (
        sum(result["total_attempts"] for result in results) / session_count
    )

    best_result = max(
        results,
        key=lambda result: (
            result["accuracy"],
            result["score"],
            -result["total_attempts"],
        ),
    )

    metric_1, metric_2 = st.columns(2)
    metric_3, metric_4 = st.columns(2)

    metric_1.metric("Sessions Completed", session_count)
    metric_2.metric("Average Accuracy", f"{average_accuracy:.1f}%")
    metric_3.metric("Average Attempts", f"{average_attempts:.1f}")
    metric_4.metric(
        "Best Session",
        f"{best_result['score']} / {best_result['total_questions']}",
    )

    st.caption(
        "Accuracy represents the percentage of questions answered "
        "correctly on the first attempt."
    )


def _show_game_summary(results):
    """Display an aggregated summary for each game."""
    if not results:
        return

    rows = [
        {
            "Game": result["game_name"],
            "Score": result["score"],
            "Questions": result["total_questions"],
            "Attempts": result["total_attempts"],
            "Accuracy": result["accuracy"],
        }
        for result in results
    ]

    results_df = pd.DataFrame(rows)
    summary_df = (
        results_df.groupby("Game", as_index=False)
        .agg(
            Sessions=("Game", "size"),
            Average_Score=("Score", "mean"),
            Average_Accuracy=("Accuracy", "mean"),
            Average_Attempts=("Attempts", "mean"),
        )
        .rename(
            columns={
                "Average_Score": "Average Score",
                "Average_Accuracy": "Average Accuracy",
                "Average_Attempts": "Average Attempts",
            }
        )
        .sort_values("Game")
        .reset_index(drop=True)
    )

    summary_df["Average Score"] = summary_df["Average Score"].round(1)
    summary_df["Average Accuracy"] = summary_df["Average Accuracy"].round(1)
    summary_df["Average Attempts"] = summary_df["Average Attempts"].round(1)

    st.markdown("#### Performance by Game")

    chart_data = summary_df[["Game", "Average Accuracy"]].set_index("Game")
    st.bar_chart(chart_data, use_container_width=True)

    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Sessions": st.column_config.NumberColumn(
                "Sessions",
                format="%d",
            ),
            "Average Score": st.column_config.NumberColumn(
                "Average Score",
                format="%.1f",
            ),
            "Average Accuracy": st.column_config.NumberColumn(
                "Average Accuracy",
                format="%.1f%%",
            ),
            "Average Attempts": st.column_config.NumberColumn(
                "Average Attempts",
                format="%.1f",
            ),
        },
    )


def _sortable_completed_at(value):
    """Convert a completion value into a datetime for reliable sorting."""
    if isinstance(value, datetime):
        return value

    if value is None:
        return datetime.min

    text = str(value).strip()
    supported_formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    )

    for date_format in supported_formats:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue

    return datetime.min


def _show_session_history(results):
    """Display individual sessions in newest-first order."""
    st.markdown("#### Session History")

    sorted_results = sorted(
        results,
        key=lambda result: (
            _sortable_completed_at(result["completed_at"]),
            result["result_id"],
        ),
        reverse=True,
    )

    for result in sorted_results:
        with st.container(border=True):
            st.markdown(f"### {result['game_name']}")

            score_column, accuracy_column, attempts_column = st.columns(3)

            score_column.metric(
                "Score",
                f"{result['score']} / {result['total_questions']}",
            )
            accuracy_column.metric(
                "First-Attempt Accuracy",
                f"{result['accuracy']:.1f}%",
            )
            attempts_column.metric(
                "Total Attempts",
                result["total_attempts"],
            )

            st.caption(f"Completed: {result['completed_display']}")


def render(patient_id):
    """Render game summaries and session history for one patient."""
    st.subheader("Game History")

    if patient_id is None:
        st.warning("Please select a patient to view game history.")
        return

    try:
        database_results = get_game_results(patient_id)
    except Exception as error:
        st.error(f"Game history could not be loaded: {error}")
        return

    results = _normalise_results(database_results)

    if not results:
        st.info("No completed game sessions are available yet.")
        return

    _show_overall_summary(results)
    st.divider()

    summary_tab, sessions_tab = st.tabs(
        ["Game Summary", "All Sessions"]
    )

    with summary_tab:
        _show_game_summary(results)

    with sessions_tab:
        _show_session_history(results)

    st.caption(
        "These results describe activity in the cognitive-training "
        "prototype and are not a clinical assessment."
    )
