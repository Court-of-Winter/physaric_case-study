from typing import Any

import pandas as pd


def _as_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _range_overlaps(first: dict[str, Any], second: dict[str, Any]) -> bool | None:
    first_low = _as_float(first.get("bootstrap_p025"))
    first_high = _as_float(first.get("bootstrap_p975"))
    second_low = _as_float(second.get("bootstrap_p025"))
    second_high = _as_float(second.get("bootstrap_p975"))
    if None in (first_low, first_high, second_low, second_high):
        return None
    return first_low <= second_high and second_low <= first_high


def generate_findings(metrics: pd.DataFrame) -> dict[str, Any]:
    """Derive one descriptive finding from measured monthly person interactions."""
    activity = metrics[
        (metrics["network"] == "person")
        & (metrics["metric"] == "interaction_count")
    ].sort_values("month")
    if activity.empty:
        return {
            "finding": "No person-network monthly interaction metrics were available.",
            "limitations": "No conclusion can be drawn from missing metrics.",
        }

    peak_index = activity["value"].astype(float).idxmax()
    peak = activity.loc[peak_index].to_dict()
    peak_position = activity.index.get_loc(peak_index)
    comparisons = []
    for neighbor_position in (peak_position - 1, peak_position + 1):
        if not 0 <= neighbor_position < len(activity):
            continue
        neighbor = activity.iloc[neighbor_position].to_dict()
        peak_value = float(peak["value"])
        neighbor_value = float(neighbor["value"])
        comparisons.append(
            {
                "month": str(neighbor["month"]),
                "interaction_count": int(neighbor_value),
                "peak_to_neighbor_ratio": (
                    peak_value / neighbor_value if neighbor_value else None
                ),
                "bootstrap_ranges_overlap": _range_overlaps(peak, neighbor),
            }
        )

    peak_month = str(peak["month"])
    peak_value = int(float(peak["value"]))
    if peak_value <= 0:
        finding = "No resolved person-network interactions were observed in 2001."
    else:
        finding = (
            f"Resolved person-network message-recipient interactions peaked in "
            f"{peak_month} at {peak_value:,}."
        )

    return {
        "finding": finding,
        "peak_month": peak_month,
        "peak_interaction_count": peak_value,
        "adjacent_month_comparisons": comparisons,
        "uncertainty": (
            "Comparisons use weekday-stratified day-block bootstrap percentile "
            "ranges; these describe within-corpus resampling sensitivity, not "
            "population confidence or uncertainty from missing/redacted mail."
        ),
        "limitations": (
            "Descriptive association only; this finding does not establish a "
            "cause for the observed monthly pattern."
        ),
    }
