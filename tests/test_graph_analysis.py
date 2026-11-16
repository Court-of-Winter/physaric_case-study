import pandas as pd
import pytest

from enron_analysis.graph_analysis import analyze_monthly_networks


def test_monthly_metrics_and_bootstrap_are_deterministic_and_aggregate_only():
    daily_edges = {
        ("2001-01-01", "person_a", "person_b"): 2,
        ("2001-01-02", "person_a", "person_b"): 1,
        ("2001-01-02", "person_b", "person_a"): 1,
        ("2001-01-03", "person_c", "person_a"): 1,
    }

    first = analyze_monthly_networks({"person": daily_edges}, bootstrap_replicates=12)
    second = analyze_monthly_networks({"person": daily_edges}, bootstrap_replicates=12)
    january = first[first["month"] == "2001-01"].set_index("metric")

    assert first.equals(second)
    assert january.loc["interaction_count", "value"] == 5
    assert january.loc["node_count", "value"] == 3
    assert january.loc["directed_edge_count", "value"] == 3
    assert january.loc["directed_density", "value"] == pytest.approx(0.5)
    assert january.loc["reciprocity", "value"] == pytest.approx(2 / 3)
    assert january.loc["largest_weak_component_fraction", "value"] == 1
    assert january.loc["interaction_count", "bootstrap_p025"] is not None
    assert "person_a" not in first.to_csv(index=False)


def test_empty_month_has_defined_zero_metrics_and_undefined_reciprocity():
    metrics = analyze_monthly_networks({"person": {}}, bootstrap_replicates=3)
    january = metrics[metrics["month"] == "2001-01"].set_index("metric")

    assert january.loc["interaction_count", "value"] == 0
    assert january.loc["node_count", "value"] == 0
    assert pd.isna(january.loc["directed_density", "value"])
    assert pd.isna(january.loc["reciprocity", "value"])
    assert january.loc["largest_weak_component_fraction", "value"] == 0


def test_bootstrap_replicates_must_be_positive():
    with pytest.raises(ValueError, match="at least 1"):
        analyze_monthly_networks({"person": {}}, bootstrap_replicates=0)
