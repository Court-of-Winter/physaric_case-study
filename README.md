# Enron metadata analysis

This repository is being built for metadata-only analysis of the public Enron
email corpus. The current increments provide bounded, allowlisted header ingestion,
conservative exact-address identity resolution, HMAC pseudonymization,
aggregate quality reporting, and monthly 2001 edge tables. Network metrics
and the privacy assessment are not implemented yet.

## Project layout

- `src/enron_analysis/`: command-line application
- `tests/`: automated tests
- `Dockerfile` and `compose.yaml`: container build and read-only input/key mounts

Ingestion reads unbuffered physical lines only through the header/body
separator. Only `From`, `To`, `Cc`, `Bcc`, `Date`, and transient `Message-ID`
header lines are passed to the email parser. Subject and all other headers are
discarded before parsing; no bytes after a valid separator are requested.
Messages without a separator are discarded without being passed to the email
parser; because such a message has no reliable header/body boundary, the
reader stops at the first line that cannot be a header and records the
malformation. Addresses and message IDs are transient in-memory values and
are excluded from yielded records.
Identity resolution preserves local-part case, canonicalizes domain case, and
merges addresses only through an explicit alias mapping. The known
`no_address@enron.com` placeholder is unresolved. Domain identities are
proxies, not verified organizations.

Pseudonyms use HMAC-SHA256 with distinct `person` and `organization`
namespaces. The alias map is a JSON object mapping alias email addresses to
canonical email addresses, for example `{"old@example.com":"new@example.com"}`.
It is loaded into memory and never emitted as a report. A quality report serializes
only aggregate counters. The CLI writes separate person and domain-proxy edge
tables, counts each message-recipient pair once, excludes self-loops, and
suppresses monthly edge groups below `--min-edge-count` (default `5`).
Pseudonymization is not anonymization: because the source corpus is public,
stable graph structures and timing can still enable re-identification. Treat
edge outputs as sensitive; the threshold is not a guarantee of anonymity.

The corpus is excluded from Docker build context and must be mounted read-only
at runtime. The HMAC key and any non-empty alias map must be stored outside the
repository; mount them read-only. The key must contain at least 32 bytes and
must never be supplied as a command-line value. Analytical outputs are
written to `outputs/`, which is ignored by Git. Do not put original addresses,
display names, alias maps, or the key in outputs, logs, or the repository.

## Build

```sh
docker build -t enron-metadata-analysis:local .
```

## Run

```sh
bash ./run.sh
```

Paths may be absolute or relative to the repository root. Defaults are
`enron_mail_20150507/maildir` for the corpus, `../secrets/hmac.key` for the
external key, and `config/empty_alias_map.json` for the empty alias map.
Override them with `EMAIL_DATA_DIR`, `HMAC_KEY_FILE`, and `ALIAS_MAP_FILE`.
`MIN_EDGE_COUNT` sets the edge-suppression threshold and defaults to `5`.
If Docker requires elevated access, run the script manually with the required
environment preserved by `sudo`, for example:

```sh
sudo --preserve-env=EMAIL_DATA_DIR,HMAC_KEY_FILE,ALIAS_MAP_FILE,MIN_EDGE_COUNT bash ./run.sh
```

The script builds or refreshes the image, mounts the corpus, key, and alias
map read-only, and writes outputs under `outputs/`.

The current CLI produces a quality report and monthly edge tables for 2001.
Network metrics, privacy attack evaluation, utility comparison, and
evidence-based findings are subsequent implementation stages.

Use the development requirements and run `pytest` to execute tests.
