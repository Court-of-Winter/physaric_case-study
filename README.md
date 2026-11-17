# Enron metadata analysis

This case study analyzes communication patterns using email metadata only. It
ingests and cleans headers, pseudonymizes identities, analyzes monthly
networks, and assesses re-identification risk. See [RESULTS.md](./RESULTS.md)
for the latest run, tables, threat-model details, and limitations.

## Run

Prerequisites: Docker, the Enron corpus, and an external HMAC key file of at
least 32 bytes. The corpus and key are not included in this repository. By
default, the script expects `enron_mail_20150507/maildir` and
`../secrets/hmac.key`.

For the quickest run, skip the optional tests:

```sh
bash ./run.sh
```

To run tests first, then the analysis:

```sh
bash ./run.sh --with-tests
```

This builds and runs the Docker test target before analysis, so it takes longer
than the default command. To run tests without processing the corpus:

```sh
docker build --target test -t enron-metadata-analysis:test .
docker run --rm enron-metadata-analysis:test
```

Configure paths and the monthly edge-suppression threshold with
`EMAIL_DATA_DIR`, `HMAC_KEY_FILE`, `ALIAS_MAP_FILE`, and `MIN_EDGE_COUNT`.
For example:

```sh
EMAIL_DATA_DIR=/data/maildir \
HMAC_KEY_FILE=/secure/hmac.key \
bash ./run.sh
```

The pipeline writes aggregate reports to the Git-ignored `outputs/` directory.
Sensitive node-level edge CSVs are off by default; opt in with
`EXPORT_EDGES=1`.

## Simulated identity fixture

The repository includes a corpus-derived name/address fixture and a
transcription of the FERC org chart for a bounded simulation. These inputs are
not equivalent to independently verified public attacker knowledge; see
[RESULTS.md](./RESULTS.md) for their sources, use, and current evaluation
limits.

To regenerate a separate name/address inventory from the corpus:

```sh
PYTHONPATH=src python3 -m enron_analysis.extract_names \
  --data-dir enron_mail_20150507/maildir \
  --output /tmp/simulated_identity_names.csv
```

The extractor reads only `From`, `To`, `Cc`, and `Bcc` headers, includes
`enron.com` addresses by default, creates a new owner-readable CSV, and will
not overwrite an existing file.
