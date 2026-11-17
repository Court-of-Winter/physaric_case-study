import csv
import os
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

from .findings import generate_findings
from .graph_analysis import analyze_monthly_networks
from .identity import PersonIdentityResolver, organization_domain
from .ingest import HeaderMessage, QualityCounts, iter_messages
from .privacy import assess_reidentification
from .pseudonymize import Pseudonymizer, load_alias_map, load_hmac_key
from .report import (
    write_findings_report,
    write_privacy_report,
    write_quality_report,
)


DailyEdgeCounts = Counter[tuple[str, str, str]]
EdgeCounts = Counter[tuple[str, str, str]]


def _write_edge_table(
    path: Path,
    edges: Mapping[tuple[str, str, str], int],
    min_edge_count: int,
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    suppressed = 0
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as output:
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
    mailbox_identity_resolver: PersonIdentityResolver,
    person_edges: DailyEdgeCounts,
    organization_edges: DailyEdgeCounts,
    mailbox_person_edges: EdgeCounts,
    mailbox_organization_edges: EdgeCounts,
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
    mailbox_source_person = (
        mailbox_identity_resolver.resolve(message.sender)
        if message.sender
        else None
    )
    mailbox_source_organization = (
        organization_domain(message.sender) if message.sender else None
    )
    if source_person is None:
        quality.unresolved_senders += 1
        return

    day = message.sent_at.strftime("%Y-%m-%d")
    month = day[:7]
    person_targets: set[str] = set()
    organization_targets: set[str] = set()
    mailbox_person_targets: set[str] = set()
    mailbox_organization_targets: set[str] = set()
    for address in message.recipients:
        person_target = pseudonymizer.person(address)
        if person_target is None:
            quality.unresolved_recipients += 1
        else:
            person_targets.add(person_target)
        mailbox_person_target = mailbox_identity_resolver.resolve(address)
        if mailbox_person_target is not None:
            mailbox_person_targets.add(mailbox_person_target)
        organization_target = pseudonymizer.organization(address)
        if organization_target is not None:
            organization_targets.add(organization_target)
        mailbox_organization_target = organization_domain(address)
        if mailbox_organization_target is not None:
            mailbox_organization_targets.add(mailbox_organization_target)

    if source_organization is not None:
        for target in organization_targets:
            if source_organization == target:
                quality.organization_self_loops_skipped += 1
            else:
                organization_edges[(day, source_organization, target)] += 1
    if mailbox_source_organization is not None:
        for target in mailbox_organization_targets:
            if mailbox_source_organization != target:
                mailbox_organization_edges[
                    (month, mailbox_source_organization, target)
                ] += 1

    for target in person_targets:
        if source_person == target:
            quality.person_self_loops_skipped += 1
        else:
            person_edges[(day, source_person, target)] += 1
    if mailbox_source_person is not None:
        for target in mailbox_person_targets:
            if mailbox_source_person != target:
                mailbox_person_edges[(month, mailbox_source_person, target)] += 1


def _monthly_edges(daily_edges: Mapping[tuple[str, str, str], int]) -> EdgeCounts:
    monthly_edges: EdgeCounts = Counter()
    for (day, source, target), weight in daily_edges.items():
        monthly_edges[(day[:7], source, target)] += weight
    return monthly_edges


def _count_suppressed_edge_groups(
    edges: Mapping[tuple[str, str, str], int],
    min_edge_count: int,
) -> int:
    return sum(weight < min_edge_count for weight in edges.values())


def run_pipeline(
    data_dir: Path,
    key_file: Path,
    output_dir: Path,
    min_edge_count: int = 5,
    alias_map_file: Path | None = None,
    export_edges: bool = False,
) -> QualityCounts:
    """Create suppressed edge tables and aggregate 2001 analysis reports."""
    if min_edge_count < 1:
        raise ValueError("minimum edge count must be at least 1")
    source = data_dir.resolve()
    destination = output_dir.resolve()
    if destination == source or source in destination.parents:
        raise ValueError("output directory must be outside the input corpus")

    key = load_hmac_key(key_file)
    aliases = load_alias_map(alias_map_file) if alias_map_file else None
    pseudonymizer = Pseudonymizer(key, aliases)
    mailbox_identity_resolver = PersonIdentityResolver()
    quality = QualityCounts()
    person_daily_edges: DailyEdgeCounts = Counter()
    organization_daily_edges: DailyEdgeCounts = Counter()
    mailbox_person_edges: EdgeCounts = Counter()
    mailbox_organization_edges: EdgeCounts = Counter()

    for message in iter_messages(data_dir, quality):
        _accumulate_message(
            message,
            pseudonymizer,
            mailbox_identity_resolver,
            person_daily_edges,
            organization_daily_edges,
            mailbox_person_edges,
            mailbox_organization_edges,
            quality,
        )

    person_edges = _monthly_edges(person_daily_edges)
    organization_edges = _monthly_edges(organization_daily_edges)
    person_output = output_dir / "person_edges_2001.csv"
    organization_output = output_dir / "organization_edges_2001.csv"
    quality.person_edge_groups_suppressed = _count_suppressed_edge_groups(
        person_edges, min_edge_count
    )
    quality.organization_edge_groups_suppressed = _count_suppressed_edge_groups(
        organization_edges, min_edge_count
    )
    if export_edges:
        _write_edge_table(person_output, person_edges, min_edge_count)
        _write_edge_table(organization_output, organization_edges, min_edge_count)
    metrics = analyze_monthly_networks(
        {
            "person": person_daily_edges,
            "organization_proxy": organization_daily_edges,
        }
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(output_dir / "network_metrics_2001.csv", index=False)
    write_findings_report(
        output_dir / "findings.json",
        generate_findings(metrics),
    )
    privacy_report = assess_reidentification(
        {
            "person": mailbox_person_edges,
            "organization_proxy": mailbox_organization_edges,
        },
        {
            "person": person_edges,
            "organization_proxy": organization_edges,
        },
        min_edge_count,
    )
    write_privacy_report(output_dir / "privacy_assessment.json", privacy_report)
    write_quality_report(output_dir / "quality_report.json", quality)
    return quality
