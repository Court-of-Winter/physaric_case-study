from datetime import datetime, timezone

from enron_analysis.identity import (
    normalize_address,
    organization_domain,
    resolve_person_identity,
)
from enron_analysis.ingest import QualityCounts, iter_messages, parse_header_lines


def test_body_and_unpermitted_headers_are_not_passed_to_parser(tmp_path, monkeypatch):
    from enron_analysis import ingest

    message = tmp_path / "message"
    message.write_bytes(
        b"From: Alice <Alice@ENRON.com>\r\n"
        b"To: Bob <bob@enron.com>\r\n"
        b"Subject: secret subject\r\n"
        b"X-Private: should not be parsed\r\n"
        b"Date: Mon, 1 Jan 2001 12:00:00 -0500\r\n"
        b"Message-ID: <one@example.com>\r\n"
        b"\r\n"
        b"Subject: body text must not be read\r\n"
        b"From: body@example.com\r\n"
    )

    original_parser = ingest.BytesHeaderParser
    parser_inputs = []

    class CapturingParser:
        def __init__(self, *args, **kwargs):
            self.parser = original_parser(*args, **kwargs)

        def parsebytes(self, content, *args, **kwargs):
            parser_inputs.append(content)
            return self.parser.parsebytes(content, *args, **kwargs)

    monkeypatch.setattr(ingest, "BytesHeaderParser", CapturingParser)
    record = next(iter_messages(tmp_path))

    assert record.sender == "alice@enron.com"
    assert record.recipients == ("bob@enron.com",)
    assert record.sent_at == datetime(2001, 1, 1, 17, 0, tzinfo=timezone.utc)
    assert not hasattr(record, "message_id")
    assert "alice@enron.com" not in repr(record)
    assert len(parser_inputs) == 1
    assert b"Subject:" not in parser_inputs[0]
    assert b"X-Private:" not in parser_inputs[0]
    assert b"body@example.com" not in parser_inputs[0]


def test_reader_stops_at_header_separator(tmp_path, monkeypatch):
    from enron_analysis import ingest

    message = tmp_path / "message"
    message.write_bytes(b"From: sender@example.com\r\n\r\n" + b"x" * 100_000)
    original_open = ingest.Path.open
    bytes_requested = []

    class TrackedFile:
        def __init__(self, source):
            self.source = source

        def __enter__(self):
            self.source.__enter__()
            return self

        def __exit__(self, *args):
            return self.source.__exit__(*args)

        def readline(self, size=-1):
            bytes_requested.append(size)
            return self.source.readline(size)

    def tracked_open(path, *args, **kwargs):
        return TrackedFile(original_open(path, *args, **kwargs))

    monkeypatch.setattr(ingest.Path, "open", tracked_open)

    list(iter_messages(tmp_path))

    assert len(bytes_requested) == 2
    assert all(size > 0 for size in bytes_requested)


def test_folded_encoded_headers_and_bad_date_are_handled():
    record, malformed = parse_header_lines(
        [
            b"From: =?utf-8?q?Alice?= <Alice@Example.COM>\r\n",
            b"To: Bob\r\n",
            b" <bob@example.com>\r\n",
            b"Date: not a date\r\n",
            b"Subject: ignored\r\n",
            b"Bad Header\r\n",
        ]
    )

    assert record.sender == "alice@example.com"
    assert record.recipients == ("bob@example.com",)
    assert record.sent_at is None
    assert malformed


def test_invalid_addresses_are_counted_without_being_kept():
    record, _ = parse_header_lines(
        [
            b"From: sender@example.com\r\n",
            b"To: not-an-email-address\r\n",
            b"Date: Mon, 1 Jan 2001 12:00:00 +0000\r\n",
        ]
    )

    assert record.recipients == ()
    assert record.invalid_address_count == 1


def test_duplicate_message_ids_are_counted_without_outputting_duplicate():
    from pathlib import Path
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as directory:
        root = Path(directory)
        headers = (
            b"From: person@example.com\r\n"
            b"Date: Mon, 1 Jan 2001 12:00:00 +0000\r\n"
            b"Message-ID: <same@example.com>\r\n\r\n"
        )
        (root / "a").write_bytes(headers + b"first body")
        (root / "b").write_bytes(headers + b"different body")
        quality = QualityCounts()

        records = list(iter_messages(root, quality))

    assert len(records) == 1
    assert quality.duplicate_message_id == 1
    assert quality.messages_parsed == 1


def test_message_without_separator_is_discarded_without_header_parsing(
    tmp_path, monkeypatch
):
    from enron_analysis import ingest

    (tmp_path / "message").write_bytes(
        b"From: sender@example.com\r\n"
        b"Date: Mon, 1 Jan 2001 12:00:00 +0000\r\n"
        b"body that has no separator\r\n"
    )
    quality = QualityCounts()

    def unexpected_parse(_):
        raise AssertionError("separatorless content must not reach the email parser")

    monkeypatch.setattr(ingest, "parse_header_lines", unexpected_parse)

    assert list(iter_messages(tmp_path, quality)) == []
    assert quality.missing_separator == 1
    assert quality.malformed_headers == 1


def test_identity_resolution_is_case_insensitive_and_placeholders_are_unresolved():
    assert normalize_address(" User@ENRON.COM ") == "user@enron.com"
    assert resolve_person_identity("User@enron.com") == "user@enron.com"
    assert resolve_person_identity("user@enron.com") == "user@enron.com"
    assert resolve_person_identity("no_address@enron.com") is None
    assert resolve_person_identity(
        "alias@enron.com",
        {"alias@ENRON.com": "person@enron.com"},
    ) == "person@enron.com"
    assert organization_domain("Person@ENRON.COM") == "enron.com"


def test_identity_resolution_merges_local_parts_that_differ_only_by_case():
    assert resolve_person_identity("User@enron.com") == resolve_person_identity(
        "user@enron.com"
    )


def test_alias_map_rejects_conflicting_normalized_aliases():
    try:
        resolve_person_identity(
            "alias@enron.com",
            {
                "alias@enron.com": "one@enron.com",
                "Alias@enron.com": "two@enron.com",
            },
        )
    except ValueError as exc:
        assert "conflicting" in str(exc)
    else:
        raise AssertionError("conflicting aliases should fail")
