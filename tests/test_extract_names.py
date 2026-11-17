import csv

from enron_analysis.extract_names import (
    extract_display_names,
    write_display_names,
)


def test_extract_display_names_reads_only_allowed_headers_and_filters_domain(
    tmp_path,
):
    source = tmp_path / "maildir"
    source.mkdir()
    (source / "message").write_bytes(
        b"From: =?utf-8?q?Alice_Smith?= <Alice@ENRON.COM>\r\n"
        b"To: Bob Jones <bob@enron.com>\r\n"
        b"Cc: Outside Person <outside@example.net>\r\n"
        b"Subject: Ignored Person <ignored@enron.com>\r\n"
        b"\r\n"
        b"From: Body Person <body@enron.com>\r\n"
    )

    observations, counts = extract_display_names(source)

    assert observations == {
        ("alice@enron.com", "Alice Smith", "from"): 1,
        ("bob@enron.com", "Bob Jones", "to"): 1,
    }
    assert counts["files_seen"] == 1


def test_write_display_names_creates_restricted_non_overwriting_csv(tmp_path):
    output = tmp_path / "simulated_names.csv"
    observations = {
        ("alice@enron.com", "Alice Smith", "from"): 2,
    }

    write_display_names(output, observations)

    with output.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert rows == [
        {
            "email_address": "alice@enron.com",
            "display_name": "Alice Smith",
            "header": "from",
            "observations": "2",
            "data_origin": "email_corpus_header",
        }
    ]
    assert output.stat().st_mode & 0o777 == 0o600

    try:
        write_display_names(output, observations)
    except FileExistsError:
        pass
    else:
        raise AssertionError("existing name data must not be overwritten")


def test_extract_display_names_rejects_invalid_domain(tmp_path):
    try:
        extract_display_names(tmp_path, "user@example.com")
    except ValueError as error:
        assert "domain" in str(error)
    else:
        raise AssertionError("email addresses are not valid domain filters")
