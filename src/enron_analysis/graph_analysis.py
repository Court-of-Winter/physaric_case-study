import calendar
import random
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import date

import networkx as nx
import pandas as pd


DailyEdges = Mapping[tuple[str, str, str], int]
_METRIC_NAMES = (
    "interaction_count",
    "node_count",
    "directed_edge_count",
    "directed_density",
    "mean_out_degree",
    "mean_weighted_out_strength",
    "reciprocity",
    "largest_weak_component_fraction",
)


def _graph(edges: Mapping[tuple[str, str], int]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for (source, target), weight in edges.items():
        if weight > 0:
            graph.add_edge(source, target, weight=weight)
    return graph


def graph_metrics(
    edges: Mapping[tuple[str, str], int],
) -> dict[str, float | int | None]:
    graph = _graph(edges)
    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    interaction_count = sum(
        int(attributes["weight"]) for _, _, attributes in graph.edges(data=True)
    )
    density = edge_count / (node_count * (node_count - 1)) if node_count > 1 else None
    reciprocal_edges = sum(
        1 for source, target in graph.edges if graph.has_edge(target, source)
    )
    reciprocity = reciprocal_edges / edge_count if edge_count else None
    largest_component_fraction = (
        max(map(len, nx.weakly_connected_components(graph))) / node_count
        if node_count
        else 0.0
    )
    return {
        "interaction_count": interaction_count,
        "node_count": node_count,
        "directed_edge_count": edge_count,
        "directed_density": density,
        "mean_out_degree": edge_count / node_count if node_count else 0.0,
        "mean_weighted_out_strength": (
            interaction_count / node_count if node_count else 0.0
        ),
        "reciprocity": reciprocity,
        "largest_weak_component_fraction": largest_component_fraction,
    }


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def analyze_monthly_networks(
    networks: Mapping[str, DailyEdges],
    bootstrap_replicates: int = 200,
) -> pd.DataFrame:
    """Summarize monthly networks and day-block bootstrap intervals."""
    if bootstrap_replicates < 1:
        raise ValueError("bootstrap replicate count must be at least 1")

    grouped: dict[str, dict[str, dict[str, Counter[tuple[str, str]]]]] = {}
    for network_name, daily_edges in networks.items():
        grouped[network_name] = defaultdict(lambda: defaultdict(Counter))
        for (day, source, target), weight in daily_edges.items():
            month = day[:7]
            grouped[network_name][month][day][(source, target)] += weight

    rows = []
    for network_index, network_name in enumerate(sorted(networks)):
        months = grouped[network_name]
        for month_number in range(1, 13):
            month = f"2001-{month_number:02d}"
            days_in_month = calendar.monthrange(2001, month_number)[1]
            days = [
                f"{month}-{day:02d}"
                for day in range(1, days_in_month + 1)
            ]
            days_by_weekday: dict[int, list[str]] = defaultdict(list)
            for day in days:
                days_by_weekday[date.fromisoformat(day).weekday()].append(day)
            day_edges = months.get(month, {})
            monthly_edges: Counter[tuple[str, str]] = Counter()
            for edges_for_day in day_edges.values():
                monthly_edges.update(edges_for_day)
            point_estimates = graph_metrics(monthly_edges)

            samples = {metric: [] for metric in _METRIC_NAMES}
            rng = random.Random(20010000 + month_number * 10 + network_index)
            for _ in range(bootstrap_replicates):
                sampled_edges: Counter[tuple[str, str]] = Counter()
                for weekday_days in days_by_weekday.values():
                    for _ in weekday_days:
                        sampled_day = rng.choice(weekday_days)
                        sampled_edges.update(day_edges.get(sampled_day, {}))
                replicate = graph_metrics(sampled_edges)
                for metric in _METRIC_NAMES:
                    value = replicate[metric]
                    if value is not None:
                        samples[metric].append(float(value))

            for metric in _METRIC_NAMES:
                values = samples[metric]
                rows.append(
                    {
                        "network": network_name,
                        "month": month,
                        "metric": metric,
                        "value": point_estimates[metric],
                        "bootstrap_p025": _percentile(values, 2.5),
                        "bootstrap_p975": _percentile(values, 97.5),
                        "bootstrap_method": "weekday_stratified_day_block_percentile",
                        "bootstrap_replicates": bootstrap_replicates,
                        "bootstrap_valid_replicates": len(values),
                    }
                )
    return pd.DataFrame(rows)
