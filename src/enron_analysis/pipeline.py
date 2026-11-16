import csv
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

from .ingest import HeaderMessage, QualityCounts, iter_messages
from .pseudonymize import Pseudonymizer, load_alias_map, load_hmac_key
from .report import write_quality_report


EdgeCounts = Counter[tuple[str, str, str]]


def _write_edge_table(
    path: Path,
    edges: Mapping[tuple[str, str, str], int],
    min_edge_count: int,
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    suppressed = 0
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(("month", "source", "target", "weight"))
        for (month, source, target), weight in sorted(edges.items()):
            if weight < min_edge_count:
                suppressed += 1
                continue
            writer.writerow((month, source, target, weight))
    return suppressed


def _accumulate_message(
    message: HeaderMessage,
    pseudonymizer: Pseudonymizer,
    person_edges: EdgeCounts,
    organization_edges: EdgeCounts,
    quality: QualityCounts,
) -> None:
    if message.sent_at is None:
        return
    if message.sent_at.year != 2001:
        quality.messages_outside_2001 += 1
        return
    quality.messages_in_2001 += 1

    if not message.recipients:
        quality.messages_without_recipients += 1
        return

    source_person = pseudonymizer.person(message.sender) if message.sender else None
    source_organization = (
        pseudonymizer.organization(message.sender) if message.sender else None
    )
    if source_person is None:
        quality.unresolved_senders += 1
        return

    month = message.sent_at.strftime("%Y-%m")
    person_targets: set[str] = set()
    organization_targets: set[str] = set()
    for address in message.recipients:
        person_target = pseudonymizer.person(address)
        if person_target is None:
            quality.unresolved_recipients += 1
        else:
            person_targets.add(person_target)
        organization_target = pseudonymizer.organization(address)
        if organization_target is not None:
            organization_targets.add(organization_target)

    if source_organization is None:
        return
    for target in organization_targets:
        if source_organization == target:
            quality.organization_self_loops_skipped += 1
        else:
            organization_edges[(month, source_organization, target)] += 1

    for target in person_targets:
        if source_person == target:
            quality.person_self_loops_skipped += 1
        else:
            person_edges[(month, source_person, target)] += 1


def run_pipeline(
    data_dir: Path,
    key_file: Path,
    output_dir: Path,
    min_edge_count: int = 5,
    alias_map_file: Path | None = None,
) -> QualityCounts:
    """Create suppressed monthly 2001 edge tables and an aggregate quality report."""
    if min_edge_count < 1:
        raise ValueError("minimum edge count must be at least 1")
    source = data_dir.resolve()
    destination = output_dir.resolve()
    if destination == source or source in destination.parents:
        raise ValueError("output directory must be outside the input corpus")

    key = load_hmac_key(key_file)
    aliases = load_alias_map(alias_map_file) if alias_map_file else None
    pseudonymizer = Pseudonymizer(key, aliases)
    quality = QualityCounts()
    person_edges: EdgeCounts = Counter()
    organization_edges: EdgeCounts = Counter()

    for message in iter_messages(data_dir, quality):
        _accumulate_message(
            message,
            pseudonymizer,
            person_edges,
            organization_edges,
            quality,
        )

    person_output = output_dir / "person_edges_2001.csv"
    organization_output = output_dir / "organization_edges_2001.csv"
    quality.person_edge_groups_suppressed = _write_edge_table(
        person_output, person_edges, min_edge_count
    )
    quality.organization_edge_groups_suppressed = _write_edge_table(
        organization_output, organization_edges, min_edge_count
    )
    write_quality_report(output_dir / "quality_report.json", quality)
    return quality
