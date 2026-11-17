import csv
import json

from enron_analysis.pipeline import run_pipeline
from enron_analysis.pseudonymize import Pseudonymizer


def _message(sender, recipient, date, message_id, extra_headers=b""):
    return (
        f"From: {sender}\r\n".encode()
        + f"To: {recipient}\r\n".encode()
        + extra_headers
        + f"Date: {date}\r\n".encode()
        + f"Message-ID: <{message_id}@example.test>\r\n\r\n".encode()
        + b"Subject: must not be read\r\nbody"
    )


def test_pipeline_writes_suppressed_pseudonymous_monthly_edges(tmp_path):
    source = tmp_path / "maildir"
    source.mkdir()
    output = tmp_path / "output"
    key_file = tmp_path / "key"
    key_file.write_bytes(b"k" * 32)
    aliases_file = tmp_path / "aliases.json"
    aliases_file.write_text(
        json.dumps({"alias@enron.com": "Alice@enron.com"}),
        encoding="utf-8",
    )

    (source / "01").write_bytes(
        _message(
            "Alice <Alice@ENRON.COM>",
            "Bob <bob@other.com>",
            "Mon, 1 Jan 2001 12:00:00 +0000",
            "one",
            b"Bcc: Carol <carol@other.com>\r\n",
        )
    )
    (source / "02").write_bytes(
        _message(
            "Alice@enron.com",
            "bob@other.com",
            "Tue, 2 Jan 2001 12:00:00 +0000",
            "two",
        )
    )
    (source / "03").write_bytes(
        _message(
            "alias@enron.com",
            "bob@other.com",
            "Wed, 3 Jan 2001 12:00:00 +0000",
            "three",
        )
    )
    (source / "04").write_bytes(
        _message(
            "Alice@enron.com",
            "bob@other.com",
            "Tue, 1 Jan 2002 12:00:00 +0000",
            "four",
        )
    )
    (source / "05").write_bytes(
        _message(
            "Alice@enron.com",
            "no_address@enron.com",
            "Thu, 4 Jan 2001 12:00:00 +0000",
            "five",
        )
    )

    quality = run_pipeline(
        data_dir=source,
        key_file=key_file,
        output_dir=output,
        min_edge_count=2,
        alias_map_file=aliases_file,
        export_edges=True,
    )

    with (output / "person_edges_2001.csv").open(
        newline="", encoding="utf-8"
    ) as edge_file:
        person_edges = list(csv.DictReader(edge_file))
    with (output / "organization_edges_2001.csv").open(
        newline="", encoding="utf-8"
    ) as edge_file:
        organization_edges = list(csv.DictReader(edge_file))
    quality_text = (output / "quality_report.json").read_text(encoding="utf-8")
    privacy_text = (output / "privacy_assessment.json").read_text(encoding="utf-8")
    findings_text = (output / "findings.json").read_text(encoding="utf-8")
    quality_report = json.loads(quality_text)
    privacy_report = json.loads(privacy_text)
    pseudonymizer = Pseudonymizer(
        b"k" * 32,
        {"alias@enron.com": "Alice@enron.com"},
    )

    assert person_edges == [
        {
            "month": "2001-01",
            "source": pseudonymizer.person("Alice@enron.com"),
            "target": pseudonymizer.person("bob@other.com"),
            "weight": "3",
        }
    ]
    assert person_edges[0]["source"].startswith("person_")
    assert person_edges[0]["target"].startswith("person_")
    assert len(organization_edges) == 1
    assert organization_edges[0]["month"] == "2001-01"
    assert organization_edges[0]["weight"] == "3"
    assert organization_edges[0]["source"] == pseudonymizer.organization(
        "Alice@enron.com"
    )
    assert organization_edges[0]["target"] == pseudonymizer.organization(
        "bob@other.com"
    )
    assert (output / "person_edges_2001.csv").stat().st_mode & 0o777 == 0o600
    assert (output / "organization_edges_2001.csv").stat().st_mode & 0o777 == 0o600
    assert quality.messages_in_2001 == 4
    assert quality.messages_outside_2001 == 1
    assert quality.unresolved_recipients == 1
    assert quality.person_edge_groups_suppressed == 1
    assert quality_report["messages_parsed"] == 5
    for private_value in (
        "Alice",
        "Bob",
        "Carol",
        "alias@enron.com",
        "@enron.com",
        "@other.com",
        "@example.test",
    ):
        assert private_value not in quality_text
        assert private_value not in privacy_text
        assert private_value not in findings_text
        assert private_value not in repr(person_edges)
        assert private_value not in repr(organization_edges)
    scenarios = privacy_report["scenarios"]
    simulated_scenario = scenarios["simulated_public_information"]
    assert simulated_scenario["status"] == "not_evaluated"
    assert "Counterfactually assume" in simulated_scenario["attacker_assumption"]
    assert simulated_scenario["identity_reference"]["name_address_header_records"] > 0
    assert (
        simulated_scenario["public_organizational_chart"]["entity_count"] == 11
    )
    assert (
        "attack_results"
        in scenarios["public_mailbox_corpus_access"]["networks"]["person"]
    )
    assert "peak_month" in json.loads(findings_text)


def test_pipeline_rejects_output_inside_input(tmp_path):
    source = tmp_path / "maildir"
    source.mkdir()
    key_file = tmp_path / "key"
    key_file.write_bytes(b"k" * 32)

    try:
        run_pipeline(source, key_file, source / "output")
    except ValueError as error:
        assert "outside" in str(error)
    else:
        raise AssertionError("output inside the input corpus should be rejected")
