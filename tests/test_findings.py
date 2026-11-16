import pandas as pd

from enron_analysis.findings import generate_findings


def test_finding_is_derived_from_monthly_results_and_reports_uncertainty():
    metrics = pd.DataFrame(
        [
            {
                "network": "person",
                "month": "2001-09",
                "metric": "interaction_count",
                "value": 100,
                "bootstrap_p025": 80,
                "bootstrap_p975": 120,
            },
            {
                "network": "person",
                "month": "2001-10",
                "metric": "interaction_count",
                "value": 300,
                "bootstrap_p025": 250,
                "bootstrap_p975": 350,
            },
            {
                "network": "person",
                "month": "2001-11",
                "metric": "interaction_count",
                "value": 200,
                "bootstrap_p025": 200,
                "bootstrap_p975": 300,
            },
        ]
    )

    finding = generate_findings(metrics)

    assert finding["peak_month"] == "2001-10"
    assert finding["peak_interaction_count"] == 300
    assert finding["adjacent_month_comparisons"][0][
        "bootstrap_ranges_overlap"
    ] is False
    assert finding["adjacent_month_comparisons"][1][
        "bootstrap_ranges_overlap"
    ] is True
    assert "cause" in finding["limitations"]


def test_finding_handles_no_available_metrics_without_making_a_claim():
    metrics = pd.DataFrame(
        columns=[
            "network",
            "month",
            "metric",
            "value",
            "bootstrap_p025",
            "bootstrap_p975",
        ]
    )

    finding = generate_findings(metrics)

    assert "peak_month" not in finding
    assert "No person-network" in finding["finding"]
