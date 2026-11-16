from collections import Counter, defaultdict
from collections.abc import Mapping

from .graph_analysis import graph_metrics


MonthlyEdges = Mapping[tuple[str, str, str], int]
_MONTHS_2001 = tuple(f"2001-{month:02d}" for month in range(1, 13))
_THRESHOLDS_TO_TEST = (5, 10, 25, 50, 100)


def _filtered_edges(
    edges: MonthlyEdges,
    min_edge_count: int | None,
) -> Counter[tuple[str, str, str]]:
    return Counter(
        {
            key: weight
            for key, weight in edges.items()
            if min_edge_count is None or weight >= min_edge_count
        }
    )


def _annual_edges(edges: MonthlyEdges) -> Counter[tuple[str, str]]:
    annual: Counter[tuple[str, str]] = Counter()
    for (_, source, target), weight in edges.items():
        annual[(source, target)] += weight
    return annual


def _node_signatures(
    edges: MonthlyEdges,
    signature_type: str,
) -> dict[str, tuple[int, ...]]:
    stats: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0, 0, 0])
    )
    outgoing_neighbors: dict[str, set[str]] = defaultdict(set)
    incoming_neighbors: dict[str, set[str]] = defaultdict(set)
    for (month, source, target), weight in edges.items():
        source_stats = stats[source][month]
        source_stats[0] += 1
        source_stats[2] += weight
        target_stats = stats[target][month]
        target_stats[1] += 1
        target_stats[3] += weight
        outgoing_neighbors[source].add(target)
        incoming_neighbors[target].add(source)

    signatures = {}
    for node, monthly in stats.items():
        if signature_type == "structural":
            signatures[node] = (
                len(outgoing_neighbors[node]),
                len(incoming_neighbors[node]),
                sum(values[2] for values in monthly.values()),
                sum(values[3] for values in monthly.values()),
            )
        else:
            signatures[node] = tuple(
                value
                for month in _MONTHS_2001
                for value in monthly.get(month, [0, 0, 0, 0])
            )
    return signatures


def _unique_match_summary(
    candidate_edges: MonthlyEdges,
    target_edges: MonthlyEdges,
    signature_type: str,
) -> dict[str, int | float]:
    candidates = _node_signatures(candidate_edges, signature_type)
    targets = _node_signatures(target_edges, signature_type)
    candidate_counts = Counter(candidates.values())
    target_counts = Counter(targets.values())
    unique_matches = sum(
        1
        for signature in targets.values()
        if target_counts[signature] == 1 and candidate_counts[signature] == 1
    )
    target_count = len(targets)
    return {
        "target_nodes": target_count,
        "unique_matches": unique_matches,
        "unique_match_rate": unique_matches / target_count if target_count else 0.0,
    }


def _utility_summary(
    baseline_edges: MonthlyEdges,
    released_edges: MonthlyEdges,
) -> dict[str, object]:
    baseline_annual = graph_metrics(_annual_edges(baseline_edges))
    released_annual = graph_metrics(_annual_edges(released_edges))

    def retention(metric: str) -> float | None:
        before = baseline_annual[metric]
        after = released_annual[metric]
        if before is None or not before:
            return None
        return float(after) / float(before)

    def difference(metric: str) -> float | None:
        before = baseline_annual[metric]
        after = released_annual[metric]
        if before is None or after is None:
            return None
        return float(after) - float(before)

    return {
        "baseline_unfiltered": baseline_annual,
        "released_after_suppression": released_annual,
        "retention_fraction": {
            "interactions": retention("interaction_count"),
            "annual_directed_edges": retention("directed_edge_count"),
            "nodes": retention("node_count"),
        },
        "released_minus_baseline": {
            "reciprocity": difference("reciprocity"),
            "largest_weak_component_fraction": difference(
                "largest_weak_component_fraction"
            ),
            "directed_density": difference("directed_density"),
        },
    }


def _attack_summaries(
    candidate_edges: MonthlyEdges,
    target_edges: MonthlyEdges,
) -> dict[str, dict[str, int | float]]:
    return {
        signature_type: _unique_match_summary(
            candidate_edges,
            target_edges,
            signature_type,
        )
        for signature_type in ("structural", "temporal")
    }


def assess_reidentification(
    raw_networks: Mapping[str, MonthlyEdges],
    pseudonymized_networks: Mapping[str, MonthlyEdges],
    min_edge_count: int,
) -> dict[str, object]:
    """Test unique signature matching without persisting identifiers or matches."""
    if min_edge_count < 1:
        raise ValueError("minimum edge count must be at least 1")
    results: dict[str, object] = {
        "attacker_assumption": (
            "Attacker has the original corpus and knows the monthly release "
            "and edge-suppression threshold, but not the HMAC key or alias map."
        ),
        "attack_method": (
            "Unique exact matches of annual in/out degree and strength "
            "profiles, and 12-month profiles of those features."
        ),
        "mitigation": (
            "Monthly aggregation with suppression of monthly dyads below "
            "the configured minimum edge count."
        ),
        "min_edge_count": min_edge_count,
        "networks": {},
    }

    network_results = results["networks"]
    for network_name in sorted(pseudonymized_networks):
        raw_edges = raw_networks.get(network_name, {})
        pseudonymized_edges = pseudonymized_networks[network_name]
        raw_released = _filtered_edges(raw_edges, min_edge_count)
        pseudonymized_released = _filtered_edges(
            pseudonymized_edges, min_edge_count
        )
        threshold_sensitivity = {}
        thresholds = sorted({min_edge_count, *_THRESHOLDS_TO_TEST})
        for threshold in thresholds:
            threshold_raw = _filtered_edges(raw_edges, threshold)
            threshold_pseudonymized = _filtered_edges(
                pseudonymized_edges, threshold
            )
            threshold_sensitivity[str(threshold)] = {
                "attack_results": _attack_summaries(
                    threshold_raw,
                    threshold_pseudonymized,
                ),
                "utility": _utility_summary(
                    pseudonymized_edges,
                    threshold_pseudonymized,
                ),
            }
        network_results[network_name] = {
            "attack_results": {
                signature_type: {
                    "before_mitigation": summary,
                    "after_mitigation": _unique_match_summary(
                        raw_released, pseudonymized_released, signature_type
                    ),
                }
                for signature_type, summary in _attack_summaries(
                    raw_edges, pseudonymized_edges
                ).items()
            },
            "utility": _utility_summary(
                pseudonymized_edges,
                pseudonymized_released,
            ),
            "threshold_sensitivity": threshold_sensitivity,
        }
    return results
