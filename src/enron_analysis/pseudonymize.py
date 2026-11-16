import hashlib
import hmac
import json
from pathlib import Path

from .identity import (
    PersonIdentityResolver,
    normalize_alias_map,
    organization_domain,
)


_MINIMUM_KEY_BYTES = 32


def load_hmac_key(path: Path) -> bytes:
    """Read a secret from a file, without exposing its contents in errors."""
    try:
        key = path.read_bytes()
    except OSError:
        raise ValueError("HMAC key file is unavailable") from None
    if len(key) < _MINIMUM_KEY_BYTES:
        raise ValueError("HMAC key must contain at least 32 bytes")
    return key


def load_alias_map(path: Path) -> dict[str, str]:
    """Load JSON aliases into memory; never write the mapping back out."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("alias map file is unavailable or invalid JSON") from None
    if not isinstance(data, dict) or any(
        not isinstance(alias, str) or not isinstance(canonical, str)
        for alias, canonical in data.items()
    ):
        raise ValueError("alias map must be a JSON object of address strings")
    return normalize_alias_map(data)


class Pseudonymizer:
    def __init__(
        self,
        key: bytes,
        aliases: dict[str, str] | None = None,
    ) -> None:
        if len(key) < _MINIMUM_KEY_BYTES:
            raise ValueError("HMAC key must contain at least 32 bytes")
        self._key = bytes(key)
        self._identity_resolver = PersonIdentityResolver(aliases)

    def _token(self, namespace: str, identifier: str) -> str:
        payload = f"argus-metadata-v1\0{namespace}\0{identifier}".encode("utf-8")
        digest = hmac.new(self._key, payload, hashlib.sha256).hexdigest()
        return f"{namespace}_{digest}"

    def person(self, address: str) -> str | None:
        identity = self._identity_resolver.resolve(address)
        if identity is None:
            return None
        return self._token("person", identity)

    def organization(self, address: str) -> str | None:
        domain = organization_domain(address)
        if domain is None:
            return None
        return self._token("organization", domain)
