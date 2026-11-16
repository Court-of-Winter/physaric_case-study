import sys

from enron_analysis.cli import build_parser
from enron_analysis.cli import main


def test_edge_suppression_threshold_defaults_to_five(tmp_path):
    args = build_parser().parse_args(
        [
            "--data-dir",
            str(tmp_path),
            "--key-file",
            str(tmp_path / "key"),
            "--output-dir",
            str(tmp_path / "output"),
        ]
    )

    assert args.min_edge_count == 5


def test_edge_suppression_threshold_is_configurable(tmp_path):
    args = build_parser().parse_args(
        [
            "--data-dir",
            str(tmp_path),
            "--key-file",
            str(tmp_path / "key"),
            "--output-dir",
            str(tmp_path / "output"),
            "--min-edge-count",
            "12",
        ]
    )

    assert args.min_edge_count == 12


def test_edge_export_is_disabled_by_default_and_can_be_enabled(tmp_path):
    base_args = [
        "--data-dir",
        str(tmp_path),
        "--key-file",
        str(tmp_path / "key"),
        "--output-dir",
        str(tmp_path / "output"),
    ]

    assert build_parser().parse_args(base_args).export_edges is False
    assert build_parser().parse_args([*base_args, "--export-edges"]).export_edges


def test_alias_map_path_is_optional(tmp_path):
    args = build_parser().parse_args(
        [
            "--data-dir",
            str(tmp_path),
            "--key-file",
            str(tmp_path / "key"),
            "--output-dir",
            str(tmp_path / "output"),
            "--alias-map",
            str(tmp_path / "aliases.json"),
        ]
    )

    assert args.alias_map == tmp_path / "aliases.json"


def test_cli_runs_pipeline_and_writes_quality_report(tmp_path, monkeypatch):
    data_dir = tmp_path / "maildir"
    data_dir.mkdir()
    (data_dir / "message").write_bytes(
        b"From: sender@example.com\r\n"
        b"To: recipient@example.net\r\n"
        b"Date: Mon, 1 Jan 2001 12:00:00 +0000\r\n"
        b"Message-ID: <message@example.test>\r\n\r\n"
        b"body is not processed"
    )
    key_file = tmp_path / "key"
    key_file.write_bytes(b"k" * 32)
    output_dir = tmp_path / "outputs"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "enron-analysis",
            "--data-dir",
            str(data_dir),
            "--key-file",
            str(key_file),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert main() == 0
    assert (output_dir / "quality_report.json").is_file()
    assert not (output_dir / "person_edges_2001.csv").exists()
    assert not (output_dir / "organization_edges_2001.csv").exists()
    assert (output_dir / "network_metrics_2001.csv").is_file()
    assert (output_dir / "privacy_assessment.json").is_file()
    assert (output_dir / "findings.json").is_file()


def test_cli_edge_export_flag_writes_sensitive_tables(tmp_path, monkeypatch, capsys):
    data_dir = tmp_path / "maildir"
    data_dir.mkdir()
    (data_dir / "message").write_bytes(
        b"From: sender@example.com\r\n"
        b"To: recipient@example.net\r\n"
        b"Date: Mon, 1 Jan 2001 12:00:00 +0000\r\n"
        b"Message-ID: <message@example.test>\r\n\r\n"
    )
    key_file = tmp_path / "key"
    key_file.write_bytes(b"k" * 32)
    output_dir = tmp_path / "outputs"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "enron-analysis",
            "--data-dir",
            str(data_dir),
            "--key-file",
            str(key_file),
            "--output-dir",
            str(output_dir),
            "--export-edges",
        ],
    )

    assert main() == 0
    assert (output_dir / "person_edges_2001.csv").is_file()
    assert (output_dir / "organization_edges_2001.csv").is_file()
    assert "re-identifiable graph structure" in capsys.readouterr().err
