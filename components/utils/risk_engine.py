def calculate_risk_status(
    recognition_accuracy,
    average_memory_score
):

    if (
        recognition_accuracy >= 80
        and average_memory_score >= 2.5
    ):
        return (
            "🟢 Stable",
            "Low"
        )

    elif (
        recognition_accuracy >= 60
        and average_memory_score >= 1.5
    ):
        return (
            "🟡 Monitor",
            "Medium"
        )

    return (
        "🔴 Needs Attention",
        "High"
    )