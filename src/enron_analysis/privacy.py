import csv
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

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


def _simulated_public_information_inputs() -> dict[str, Any]:
    data_dir = Path(__file__).resolve().parents[2] / "data"
    identity_path = data_dir / "simulated_identity_names.csv"
    org_chart_path = data_dir / "simulated_public_org_chart.json"

    with identity_path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        expected_fields = {
            "email_address",
            "display_name",
            "header",
            "observations",
            "data_origin",
        }
        if set(reader.fieldnames or ()) != expected_fields:
            raise ValueError("simulated identity data has an unexpected schema")
        identity_rows = list(reader)
    if any(row["data_origin"] != "email_corpus_header" for row in identity_rows):
        raise ValueError("simulated identity data has an unexpected origin")

    with org_chart_path.open(encoding="utf-8") as source:
        org_chart = json.load(source)
    entities = org_chart["entities"]
    relationships = org_chart["relationships"]
    if (
        not isinstance(entities, list)
        or not all(isinstance(entity, str) for entity in entities)
        or not isinstance(relationships, list)
        or not all(
            isinstance(edge, list)
            and len(edge) == 2
            and all(isinstance(entity, str) for entity in edge)
            and set(edge) <= set(entities)
            for edge in relationships
        )
    ):
        raise ValueError("simulated organization chart has an unexpected schema")

    return {
        "preparation_status": "inputs_available",
        "identity_reference": {
            "file": "data/simulated_identity_names.csv",
            "origin": (
                "Display names and addresses extracted from the email corpus; "
                "evaluator reference data, not independent public attacker knowledge."
            ),
            "name_address_header_records": len(identity_rows),
            "distinct_addresses": len(
                {row["email_address"] for row in identity_rows}
            ),
            "distinct_display_names": len(
                {row["display_name"] for row in identity_rows}
            ),
        },
        "public_organizational_chart": {
            "file": "data/simulated_public_org_chart.json",
            **org_chart,
            "entity_count": len(entities),
            "relationship_count": len(relationships),
        },
        "methods": {
            "name_and_address_linkage": {
                "status": "not_evaluable",
                "reason": (
                    "Even treating the corpus-derived names and addresses as "
                    "public attacker knowledge, the pseudonymized edge export "
                    "contains no address-to-pseudonym mapping."
                ),
            },
            "department_to_graph_matching": {
                "status": "not_evaluable",
                "reason": (
                    "The FERC chart describes corporate units but not their "
                    "employees. No independent press, LinkedIn, or similar "
                    "source was collected to map the assumed public names to "
                    "departments and then to graph communities."
                ),
            },
            "mailbox_graph_signature_matching": {
                "status": "evaluated_separately",
                "scenario": "public_mailbox_corpus_access",
            },
        },
    }


def assess_reidentification(
    mailbox_networks: Mapping[str, MonthlyEdges],
    pseudonymized_networks: Mapping[str, MonthlyEdges],
    min_edge_count: int,
) -> dict[str, object]:
    """Report the customer threat model and a separate mailbox-access test."""
    if min_edge_count < 1:
        raise ValueError("minimum edge count must be at least 1")
    results: dict[str, Any] = {
        "scenarios": {
            "simulated_public_information": {
                "status": "not_evaluated",
                "attacker_assumption": (
                    "Counterfactually assume an attacker knows the names and "
                    "email-address associations in the identity fixture, as if "
                    "learned from public sources, and the corporate-unit "
                    "relationships in the cited FERC report. The attacker does "
                    "not have the mailboxes, HMAC key, or alias map. The fixture "
                    "is actually derived from the email corpus."
                ),
                **_simulated_public_information_inputs(),
            },
            "public_mailbox_corpus_access": {
                "status": "evaluated",
                "attacker_assumption": (
                    "Attacker has the original public mailbox corpus and knows "
                    "the monthly release and edge-suppression threshold, but "
                    "not the HMAC key or alias map."
                ),
                "attack_method": (
                    "Unique exact matches of annual in/out degree and strength "
                    "profiles, and 12-month profiles of those features."
                ),
                "mitigation": (
                    "Monthly aggregation with suppression of monthly dyads "
                    "below the configured minimum edge count."
                ),
                "min_edge_count": min_edge_count,
                "networks": {},
            },
        }
    }

    network_results = results["scenarios"]["public_mailbox_corpus_access"][
        "networks"
    ]
    for network_name in sorted(pseudonymized_networks):
        mailbox_edges = mailbox_networks.get(network_name, {})
        pseudonymized_edges = pseudonymized_networks[network_name]
        mailbox_released = _filtered_edges(mailbox_edges, min_edge_count)
        pseudonymized_released = _filtered_edges(
            pseudonymized_edges, min_edge_count
        )
        threshold_sensitivity = {}
        thresholds = sorted({min_edge_count, *_THRESHOLDS_TO_TEST})
        for threshold in thresholds:
            threshold_mailbox = _filtered_edges(mailbox_edges, threshold)
            threshold_pseudonymized = _filtered_edges(
                pseudonymized_edges, threshold
            )
            threshold_sensitivity[str(threshold)] = {
                "attack_results": _attack_summaries(
                    threshold_mailbox,
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
                        mailbox_released,
                        pseudonymized_released,
                        signature_type,
                    ),
                }
                for signature_type, summary in _attack_summaries(
                    mailbox_edges, pseudonymized_edges
                ).items()
            },
            "utility": _utility_summary(
                pseudonymized_edges,
                pseudonymized_released,
            ),
            "threshold_sensitivity": threshold_sensitivity,
        }
    return results
