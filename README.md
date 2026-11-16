# Enron metadata analysis

This repository is being built for metadata-only analysis of the public Enron
email corpus. The current increments provide bounded, allowlisted header ingestion,
conservative exact-address identity resolution, HMAC pseudonymization,
aggregate quality reporting, monthly 2001 network metrics,
resampling-sensitivity bounds, a computed descriptive finding, and an
aggregate structural/temporal privacy assessment.

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
tables only when explicitly requested with `--export-edges`; they contain
stable node pseudonyms and are sensitive. Exported edges count each
message-recipient pair once, exclude self-loops, and apply the configured
monthly threshold (default `5`).
Pseudonymization is not anonymization: because the source corpus is public,
stable graph structures and timing can still enable re-identification. Treat
edge outputs as sensitive; measured signature matching shows that increasing
the threshold does not reliably prevent re-identification.

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

## Run analysis only

```sh
bash ./run.sh
```

## Run tests, then analysis

```sh
bash ./run.sh --with-tests
```

The test command builds a dedicated Docker test target and runs pytest before
the analysis image is built or the corpus is processed. If tests fail, analysis
does not run. Both commands perform the same end-to-end analysis on success.

Paths may be absolute or relative to the repository root. Defaults are
`enron_mail_20150507/maildir` for the corpus, `../secrets/hmac.key` for the
external key, and `config/empty_alias_map.json` for the empty alias map.
Override them with `EMAIL_DATA_DIR`, `HMAC_KEY_FILE`, and `ALIAS_MAP_FILE`.
`MIN_EDGE_COUNT` sets the edge-suppression threshold and defaults to `5`.
By default, the run writes only aggregate reports and does not create edge
tables. Set `EXPORT_EDGES=1` to write the sensitive node-level CSVs; the CLI
prints a warning when this option is enabled. If edge tables were exported in
an earlier run, a later default run does not delete them and will warn that
they remain in `outputs/`; remove those files manually when no longer needed.
If Docker requires elevated access, run the script manually with the required
environment preserved by `sudo`, for example:

```sh
sudo --preserve-env=EMAIL_DATA_DIR,HMAC_KEY_FILE,ALIAS_MAP_FILE,MIN_EDGE_COUNT,EXPORT_EDGES bash ./run.sh
```

The script builds or refreshes the image, mounts the corpus, key, and alias
map read-only, and writes outputs under `outputs/`.

The Dockerfile pins Python to 3.12.16, pip to 25.0.1, and all runtime and test
Python packages to exact versions so dependency resolution does not drift.
Package versions are not locked to OS-specific wheel hashes or one CPU
architecture. The `python:3.12.16-slim` tag is not pinned by image digest, so
Docker base-image updates can still change the underlying OS image; this favors
portability over bit-for-bit image reproduction. For an exact rerun, use the
same repository revision, corpus version, key, and configured parameters.

The current CLI produces a quality report and monthly graph results for 2001.
It also writes `network_metrics_2001.csv` with monthly directed-network
summaries: interactions, nodes, edges, directed density, mean out-degree,
mean weighted out-strength, reciprocity, and largest weak-component share.
The reported 2.5th and 97.5th bootstrap percentiles use a deterministic
day-block resampling stratified by weekday. These are resampling-sensitivity
bounds, not population confidence intervals: they assume days are exchangeable
within each weekday and do not capture messages omitted, redacted, or missing
from the source corpus, nor dependence across days.
`findings.json` derives one descriptive finding from the observed monthly
person-network interaction counts and includes adjacent-month resampling-range
comparisons; it makes no causal claim.
`privacy_assessment.json` tests unique annual structural and 12-month temporal
in/out degree/strength signature matching, assuming the attacker has the
original corpus and knows the release threshold, but not the HMAC key or alias
map. Candidate identities and matches are transient; only aggregate match
counts/rates are serialized.
The report also compares unfiltered monthly graph utility with the released
thresholded graph (interactions, annual dyads, nodes, reciprocity, density,
and largest weak component); this isolates edge-suppression utility and does
not measure the separate loss of within-month timing. It also evaluates
threshold sensitivity at `k=5, 10, 25, 50, 100` and the configured threshold.
Exact signature matching is a limited attack model, not a general
re-identification guarantee; results do not prove anonymity or account for
external auxiliary data.

To run the included tests and then produce the analysis in one command:

```sh
bash ./run.sh --with-tests
```
