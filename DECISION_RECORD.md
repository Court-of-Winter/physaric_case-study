# Decision record

## Architecture

The pipeline reads email headers only (`From`, `To`, `Cc`, `Bcc`, and `Date`,
with transient `Message-ID` for duplicate detection), and stops at the
header/body separator. It resolves addresses, applies keyed HMAC-SHA256
pseudonyms with separate person and organization namespaces, aggregates
directed communication networks by day/month, suppresses monthly dyads below
the configured threshold (default \(k=5\)), and writes aggregate metrics and
privacy reports. Node-level edge CSVs are an explicit opt-in because they are
sensitive.

Identity normalization lowercases both the local part and domain. This
reflects common practice, but local-part case sensitivity is permitted by
email standards, so differently capitalized addresses may be merged. The
privacy report separates a public-mailbox-corpus signature comparison from a
simulated public-information scenario. The latter records a corpus-derived
name/address fixture and a FERC organizational-unit chart; it reports
person-level evaluation as not evaluable because the chart identifies no
employees or person-to-unit mappings. Raw mailbox-derived edges used by the
separate corpus comparison exist in memory, are not pseudonymized, and are
not written to reports.

## Trade-offs

- **Metadata-only parsing** reduces content exposure and limits scope, but
  graph structure and timing can still be identifying.
- **HMAC pseudonyms** avoid publishing direct addresses in routine reports,
  but are deterministic within a key and do not anonymize graph patterns.
- **Monthly dyad suppression** reduces released detail while preserving some
  aggregate utility. The measured corpus comparison shows suppression is not
  a guarantee: exact signature match rates rose after suppression, while
  interaction retention remained about 76% for people and 67% for
  organization proxies at \(k=5\).
- **Corpus-derived names plus the FERC chart** provide a reproducible
  simulation fixture, not an authentic public-information attacker dataset.
  The names came from mail, and the chart contains corporate units rather
  than employees. I therefore report the public-information person attack as
  not evaluated instead of presenting mailbox-informed results as a proxy.
- **Case-insensitive local-part normalization** simplifies identity
  resolution in line with common provider behavior, at the cost of potentially
  conflating rare case-distinct mailboxes.

## What I would do differently with real customer data

I would first agree a threat model with the customer and privacy/security
stakeholders: attacker access, likely auxiliary sources (including press),
released outputs, target population, and acceptable risk. I would not infer
public attacker knowledge from the mailbox corpus. Instead, I would curate a
dated, provenance-backed public dataset of names, roles, and organizational
relationships, validate identity links independently, and test a documented
attacker workflow against each actual release mode. Any mailbox-derived
identity mapping and raw graph used as evaluation ground truth would be
isolated from attacker inputs, access-controlled, minimized, and retained only
as long as needed.

I would also keep edge exports disabled by default, review whether the
suppression rule is adequate against realistic linkage, and validate
normalization and alias handling against customer-specific address behavior
before processing. I would document data lineage, access controls, retention,
and residual risk, then have the customer review the release decision.

## Limitations of this work

Time did not allow me to manually control or deeply review every part of the
codebase. I focused review on the parts most important to privacy and examined
the included tests; I also added assertions for what reaches the email parser
and changed address normalization to be case-insensitive. With more time, I
would design additional edge-case tests, especially for malformed and unusual
headers, identity collisions, aliases, and attack assumptions.

I lack sufficient knowledge of how press data would help an attacker, so press
sources and their value were not systematically assessed. Time also prevented
building a realistic attacker workflow. The current public-information
exercise is only a bounded simulation using names extracted from the email
corpus and the cited FERC org chart; it is not a true public-information
attack, and it yields no person-level re-identification result. The separate
mailbox-corpus signature test assumes stronger attacker access and must not be
read as a result for the customer scenario.
