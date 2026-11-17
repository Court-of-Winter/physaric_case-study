import argparse
import csv
import os
import sys
from collections import Counter
from email.parser import BytesHeaderParser
from email.policy import default
from email.utils import getaddresses
from pathlib import Path

from .identity import normalize_address
from .ingest import (
    HeaderTooLargeError,
    _corpus_files,
    _permitted_header_bytes,
    _read_header_lines,
)


_ADDRESS_HEADERS = ("from", "to", "cc", "bcc")


def extract_display_names(
    data_dir: Path,
    domain: str = "enron.com",
) -> tuple[Counter[tuple[str, str, str]], dict[str, int]]:
    """Aggregate display names from address headers, without reading bodies."""
    normalized_domain = domain.strip().lower().rstrip(".")
    if not normalized_domain or "@" in normalized_domain:
        raise ValueError("domain must be a non-empty domain name")
    try:
        normalized_domain = normalized_domain.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise ValueError("domain must be a valid IDN domain name") from error

    observations: Counter[tuple[str, str, str]] = Counter()
    counts = {
        "files_seen": 0,
        "unreadable_files": 0,
        "oversized_headers": 0,
        "missing_separator": 0,
        "malformed_headers": 0,
    }

    for path in _corpus_files(data_dir):
        counts["files_seen"] += 1
        try:
            lines, separated, malformed = _read_header_lines(path)
        except HeaderTooLargeError:
            counts["oversized_headers"] += 1
            continue
        except OSError:
            counts["unreadable_files"] += 1
            continue

        counts["malformed_headers"] += int(malformed)
        if not separated:
            counts["missing_separator"] += 1
            continue

        permitted_headers, malformed_permitted = _permitted_header_bytes(lines)
        counts["malformed_headers"] += int(malformed_permitted)
        message = BytesHeaderParser(policy=default).parsebytes(permitted_headers)
        for header_name in _ADDRESS_HEADERS:
            for display_name, address in getaddresses(
                [str(value) for value in message.get_all(header_name, [])]
            ):
                normalized_address = normalize_address(address)
                name = " ".join(display_name.split())
                if (
                    normalized_address is None
                    or normalized_address.rsplit("@", 1)[1] != normalized_domain
                    or not name
                ):
                    continue
                observations[(normalized_address, name, header_name)] += 1

    return observations, counts


def write_display_names(
    output_path: Path,
    observations: Counter[tuple[str, str, str]],
) -> None:
    """Create a new, owner-readable CSV; never overwrite existing data."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        output_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(
            ("email_address", "display_name", "header", "observations", "data_origin")
        )
        for (address, display_name, header), count in sorted(observations.items()):
            writer.writerow(
                (address, display_name, header, count, "email_corpus_header")
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "One-time extraction of display names from email address headers. "
            "This does not run as part of the analysis pipeline."
        )
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Path to the email corpus directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New CSV path for the sensitive corpus-derived name/address data.",
    )
    parser.add_argument(
        "--domain",
        default="enron.com",
        help="Only include this email domain (default: enron.com).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()
    output_path = args.output.resolve()
    if data_dir == output_path or data_dir in output_path.parents:
        parser.error("output file must be outside the input corpus")

    try:
        observations, counts = extract_display_names(data_dir, args.domain)
        write_display_names(output_path, observations)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(
        f"Wrote {len(observations)} name/address/header records to {output_path}. "
        f"Scanned {counts['files_seen']} files. This is corpus-derived "
        "simulation data, not independently verified public information.",
        file=sys.stderr,
    )
    if counts["unreadable_files"] or counts["oversized_headers"]:
        print(
            "Some files were skipped: "
            f"{counts['unreadable_files']} unreadable, "
            f"{counts['oversized_headers']} oversized headers.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
