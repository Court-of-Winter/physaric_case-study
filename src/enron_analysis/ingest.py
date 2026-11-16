import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.parser import BytesHeaderParser
from email.policy import default
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path

from .identity import normalize_address


_ALLOWED_HEADERS = frozenset(
    {b"from", b"to", b"cc", b"bcc", b"date", b"message-id"}
)
_ADDRESS_HEADERS = ("from", "to", "cc", "bcc")
_MAX_HEADER_BYTES = 256 * 1024


@dataclass(frozen=True)
class HeaderMessage:
    sender: str | None = field(repr=False)
    recipients: tuple[str, ...] = field(repr=False)
    sent_at: datetime | None


@dataclass(frozen=True)
class _ParsedHeaders:
    sender: str | None = field(repr=False)
    recipients: tuple[str, ...] = field(repr=False)
    sent_at: datetime | None
    message_id: str | None = field(repr=False)
    invalid_address_count: int


@dataclass
class QualityCounts:
    files_seen: int = 0
    messages_parsed: int = 0
    unreadable_files: int = 0
    oversized_headers: int = 0
    missing_separator: int = 0
    malformed_headers: int = 0
    missing_sender: int = 0
    missing_or_invalid_date: int = 0
    missing_message_id: int = 0
    duplicate_message_id: int = 0
    messages_in_2001: int = 0
    messages_outside_2001: int = 0
    messages_without_recipients: int = 0
    unresolved_senders: int = 0
    unresolved_recipients: int = 0
    invalid_addresses: int = 0
    person_self_loops_skipped: int = 0
    organization_self_loops_skipped: int = 0
    person_edge_groups_suppressed: int = 0
    organization_edge_groups_suppressed: int = 0


class HeaderTooLargeError(ValueError):
    pass


def _read_header_lines(path: Path) -> tuple[list[bytes], bool, bool]:
    """Read physical header lines only; never request bytes after the separator."""
    lines: list[bytes] = []
    total = 0
    separated = False
    malformed = False

    with path.open("rb", buffering=0) as source:
        while total <= _MAX_HEADER_BYTES:
            line = source.readline(_MAX_HEADER_BYTES - total + 1)
            if not line:
                break
            total += len(line)
            if total > _MAX_HEADER_BYTES:
                raise HeaderTooLargeError
            if line in (b"\n", b"\r\n"):
                separated = True
                break
            if line.startswith((b" ", b"\t")):
                if not lines:
                    malformed = True
                    break
            else:
                name, separator, _ = line.partition(b":")
                if (
                    not separator
                    or not name
                    or any(byte <= 32 or byte >= 127 for byte in name)
                ):
                    malformed = True
                    break
            lines.append(line)

    return lines, separated, malformed


def _permitted_header_bytes(lines: list[bytes]) -> tuple[bytes, bool]:
    permitted: list[bytes] = []
    current_is_permitted = False
    malformed = False

    for line in lines:
        if line.startswith((b" ", b"\t")):
            if current_is_permitted:
                permitted.append(line)
            continue

        name, separator, _ = line.partition(b":")
        if not separator or not name or any(byte <= 32 or byte >= 127 for byte in name):
            malformed = True
            current_is_permitted = False
            continue

        current_is_permitted = name.lower() in _ALLOWED_HEADERS
        if current_is_permitted:
            permitted.append(line)

    return b"".join(permitted), malformed


def _addresses(message, header_name: str) -> tuple[tuple[str, ...], int]:
    values = message.get_all(header_name, [])
    parsed = getaddresses([str(value) for value in values])
    normalized = set()
    invalid_count = 0
    for _, address in parsed:
        if not address.strip():
            continue
        normalized_address = normalize_address(address)
        if normalized_address is not None:
            normalized.add(normalized_address)
        else:
            invalid_count += 1
    return tuple(sorted(normalized)), invalid_count


def _single_message_id(message) -> str | None:
    values = message.get_all("message-id", [])
    if len(values) != 1:
        return None
    value = str(values[0]).strip()
    return value or None


def _sent_at(message) -> datetime | None:
    values = message.get_all("date", [])
    if len(values) != 1:
        return None
    try:
        parsed = parsedate_to_datetime(str(values[0]))
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed is None or parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def parse_header_lines(lines: list[bytes]) -> tuple[_ParsedHeaders, bool]:
    """Parse only explicitly permitted headers from already bounded header lines."""
    filtered, malformed = _permitted_header_bytes(lines)
    message = BytesHeaderParser(policy=default).parsebytes(filtered)

    senders, invalid_address_count = _addresses(message, "from")
    sender = senders[0] if len(senders) == 1 else None
    recipient_addresses = set()
    for header_name in _ADDRESS_HEADERS[1:]:
        addresses, invalid_count = _addresses(message, header_name)
        recipient_addresses.update(addresses)
        invalid_address_count += invalid_count
    recipients = tuple(sorted(recipient_addresses))
    return (
        _ParsedHeaders(
            sender=sender,
            recipients=recipients,
            sent_at=_sent_at(message),
            message_id=_single_message_id(message),
            invalid_address_count=invalid_address_count,
        ),
        malformed,
    )


def _corpus_files(root: Path) -> Iterator[Path]:
    if not root.is_dir():
        raise ValueError("data directory is not an accessible directory")

    def raise_walk_error(error: OSError) -> None:
        raise error

    for current, directories, filenames in os.walk(
        root,
        followlinks=False,
        onerror=raise_walk_error,
    ):
        directories[:] = sorted(
            name
            for name in directories
            if not (Path(current) / name).is_symlink()
        )
        for filename in sorted(filenames):
            path = Path(current) / filename
            if not path.is_symlink() and path.is_file():
                yield path


def iter_messages(
    root: Path,
    quality: QualityCounts | None = None,
) -> Iterator[HeaderMessage]:
    """Yield header-only records and count failures without exposing identifiers."""
    counts = quality if quality is not None else QualityCounts()
    seen_message_ids: set[str] = set()

    for path in _corpus_files(root):
        counts.files_seen += 1
        try:
            lines, separated, malformed = _read_header_lines(path)
        except HeaderTooLargeError:
            counts.oversized_headers += 1
            continue
        except OSError:
            counts.unreadable_files += 1
            continue

        if malformed:
            counts.malformed_headers += 1
        if not separated:
            counts.missing_separator += 1
            continue

        parsed, parse_malformed = parse_header_lines(lines)
        if parse_malformed:
            counts.malformed_headers += 1
        if parsed.sender is None:
            counts.missing_sender += 1
        if parsed.sent_at is None:
            counts.missing_or_invalid_date += 1
        counts.invalid_addresses += parsed.invalid_address_count
        if parsed.message_id is None:
            counts.missing_message_id += 1
        else:
            dedupe_key = parsed.message_id.strip()
            if dedupe_key in seen_message_ids:
                counts.duplicate_message_id += 1
                continue
            seen_message_ids.add(dedupe_key)

        counts.messages_parsed += 1
        yield HeaderMessage(
            sender=parsed.sender,
            recipients=parsed.recipients,
            sent_at=parsed.sent_at,
        )
