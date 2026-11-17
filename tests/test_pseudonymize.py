import hashlib
import hmac
import json

import pytest

from enron_analysis.ingest import QualityCounts
from enron_analysis.pseudonymize import (
    Pseudonymizer,
    load_alias_map,
    load_hmac_key,
)
from enron_analysis.report import write_quality_report


def test_person_tokens_are_stable_and_domain_separated():
    pseudonymizer = Pseudonymizer(b"k" * 32)

    person = pseudonymizer.person("Alice@ENRON.COM")
    organization = pseudonymizer.organization("Alice@enron.com")

    assert person == pseudonymizer.person("Alice@enron.com")
    assert person.startswith("person_")
    assert organization.startswith("organization_")
    assert person != organization
    expected = hmac.new(
        b"k" * 32,
        b"argus-metadata-v1\0person\0alice@enron.com",
        hashlib.sha256,
    ).hexdigest()
    assert person == f"person_{expected}"


def test_alias_resolution_precedes_person_pseudonymization():
    pseudonymizer = Pseudonymizer(
        b"k" * 32,
        {"alias@enron.com": "person@enron.com"},
    )

    assert pseudonymizer.person("alias@enron.com") == pseudonymizer.person(
        "person@ENRON.COM"
    )
    assert pseudonymizer.person("no_address@enron.com") is None


def test_key_file_requires_at_least_32_bytes(tmp_path):
    key_path = tmp_path / "key"
    key_path.write_bytes(b"short")

    with pytest.raises(ValueError, match="at least 32 bytes"):
        load_hmac_key(key_path)

    key_path.write_bytes(b"k" * 32)
    assert load_hmac_key(key_path) == b"k" * 32


def test_alias_map_loader_normalizes_and_does_not_change_source(tmp_path):
    alias_path = tmp_path / "aliases.json"
    source = '{"alias@ENRON.COM":"person@enron.com"}'
    alias_path.write_text(source, encoding="utf-8")

    aliases = load_alias_map(alias_path)

    assert aliases == {"alias@enron.com": "person@enron.com"}
    assert alias_path.read_text(encoding="utf-8") == source


def test_alias_map_loader_rejects_cycles_without_echoing_identifiers(tmp_path):
    alias_path = tmp_path / "aliases.json"
    alias_path.write_text(
        json.dumps(
            {
                "first-private@example.com": "second-private@example.com",
                "second-private@example.com": "first-private@example.com",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as error:
        load_alias_map(alias_path)

    assert "private" not in str(error.value)


def test_quality_report_contains_only_aggregate_counts(tmp_path):
    report_path = tmp_path / "nested" / "quality.json"
    counts = QualityCounts(files_seen=4, messages_parsed=3, missing_sender=1)

    write_quality_report(report_path, counts)

    content = report_path.read_text(encoding="utf-8")
    assert json.loads(content)["files_seen"] == 4
    assert json.loads(content)["missing_sender"] == 1
    assert "sender@example.com" not in content
