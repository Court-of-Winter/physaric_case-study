from collections.abc import Mapping


_UNRESOLVED_ADDRESSES = frozenset({"no_address@enron.com"})


def normalize_address(address: str) -> str | None:
    """Lowercase the local part and domain, treating addresses case-insensitively."""
    candidate = address.strip()
    if candidate.count("@") != 1 or any(char.isspace() for char in candidate):
        return None

    local_part, domain = candidate.rsplit("@", 1)
    if not local_part or not domain:
        return None

    try:
        normalized_domain = domain.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError:
        return None
    if not normalized_domain or normalized_domain.startswith("."):
        return None

    return f"{local_part.lower()}@{normalized_domain}"


def normalize_alias_map(aliases: Mapping[str, str]) -> dict[str, str]:
    """Validate and flatten an explicit address-to-canonical-address mapping."""
    normalized_aliases: dict[str, str] = {}
    for alias, canonical in aliases.items():
        normalized_alias = normalize_address(alias)
        normalized_canonical = normalize_address(canonical)
        if normalized_alias is None or normalized_canonical is None:
            raise ValueError("alias map contains an invalid address")
        if (
            normalized_alias in _UNRESOLVED_ADDRESSES
            or normalized_canonical in _UNRESOLVED_ADDRESSES
        ):
            raise ValueError("alias map cannot resolve a placeholder address")
        if normalized_alias == normalized_canonical:
            continue
        previous = normalized_aliases.get(normalized_alias)
        if previous is not None and previous != normalized_canonical:
            raise ValueError("alias map contains conflicting normalized aliases")
        normalized_aliases[normalized_alias] = normalized_canonical

    flattened: dict[str, str] = {}
    for alias in normalized_aliases:
        canonical = normalized_aliases[alias]
        visited = {alias}
        while canonical in normalized_aliases:
            if canonical in visited:
                raise ValueError("alias map contains a cycle")
            visited.add(canonical)
            canonical = normalized_aliases[canonical]
        flattened[alias] = canonical
    return flattened


def resolve_person_identity(
    address: str,
    aliases: Mapping[str, str] | None = None,
) -> str | None:
    """Use exact normalized addresses; only an explicit alias map may merge them."""
    return PersonIdentityResolver(aliases).resolve(address)


class PersonIdentityResolver:
    def __init__(self, aliases: Mapping[str, str] | None = None) -> None:
        self._aliases = normalize_alias_map(aliases or {})

    def resolve(self, address: str) -> str | None:
        """Resolve one address using aliases normalized at construction time."""
        normalized = normalize_address(address)
        if normalized is None or normalized in _UNRESOLVED_ADDRESSES:
            return None
        return self._aliases.get(normalized, normalized)


def organization_domain(address: str) -> str | None:
    """Return a normalized domain proxy, not a verified organization identity."""
    normalized = normalize_address(address)
    if normalized is None or normalized in _UNRESOLVED_ADDRESSES:
        return None
    return normalized.rsplit("@", 1)[1]
