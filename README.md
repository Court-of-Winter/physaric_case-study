# Enron metadata analysis

This case study analyses communication patterns using email metadata only.
It follows four steps: ingest and clean; pseudonymise; analyse; assess
re-identification risk.

## Run it

Prerequisites: Docker, the Enron corpus, and an external HMAC key file of at
least 32 bytes. The corpus and key are not in this GitHub repository; obtain
the same versions to reproduce the reported results. The default paths are
`enron_mail_20150507/maildir` and `../secrets/hmac.key`.

Analysis only:

```sh
bash ./run.sh
```

Run tests first, then the same analysis:

```sh
bash ./run.sh --with-tests
```

The latter builds and runs the Docker test target; analysis starts only if
tests pass. **30 tests passed** in the documented validation. To run tests
without processing the corpus:

```sh
docker build --target test -t enron-metadata-analysis:test .
docker run --rm enron-metadata-analysis:test
```

Override input paths and the monthly edge-suppression threshold with
`EMAIL_DATA_DIR`, `HMAC_KEY_FILE`, `ALIAS_MAP_FILE`, and `MIN_EDGE_COUNT`.
For example:

```sh
EMAIL_DATA_DIR=/data/maildir HMAC_KEY_FILE=/secure/hmac.key bash ./run.sh
```

The default writes aggregate reports only. Node-level edge CSVs are sensitive
and off by default; explicitly opt in with `EXPORT_EDGES=1`. A prior edge
export is not deleted by a later default run.

## What the pipeline does

1. **Ingest and clean:** reads only `From`, `To`, `Cc`, `Bcc`, and `Date`, plus
   transient `Message-ID` for duplicate detection. Subject and other headers
   are discarded before parsing; reads stop at the header/body separator, so
   body bytes do not enter the parser. Malformed or separatorless messages are
   counted and handled.
2. **Pseudonymise:** conservatively resolves exact addresses and any explicit
   alias map before applying deterministic HMAC-SHA256 pseudonyms, with
   separate person and organization namespaces. The key and non-empty alias
   map stay outside the repository.
3. **Analyse:** builds directed, weighted person and email-domain-proxy
   networks and reports monthly 2001 metrics. Domain nodes are proxies, not
   verified organizations.
4. **Assess risk:** compares structural and temporal graph signatures against
   the original public corpus in memory. The assumed attacker has that corpus
   and knows the suppression threshold, but not the key or alias map.

Pseudonymization is not anonymization: graph structure and timing may still
identify people. Original addresses used in the attack comparison are
transient and are not logged or persisted in reports. Aggregate reports are
the default; edge exports contain pseudonymous node-level links and remain
sensitive.

## Results from the included corpus

These are computed results from the local corpus version, which has had some
messages redacted and some addresses inferred from recipient names. Inferred
addresses are not verified; results describe this modified corpus, not the
complete historical record.

- 517,371 messages parsed; 272,934 dated in 2001.
- Resolved person-network interactions peaked in October 2001 at **301,523**.
  The bootstrap ranges for October and September did not overlap; October and
  November did overlap. This is descriptive, not causal.
- The risk test finds exact signature matches, not general probabilities of
  re-identification. At the default \(k=5\), post-suppression temporal match
  rates were 37.73% for people and 47.20% for organization proxies; interaction
  retention was 75.56% and 67.34%, respectively.
- Raising \(k\) is not a reliable privacy control: match rates are
  non-monotonic, and suppression can leave a smaller, more distinctive graph.
  See `privacy_assessment.json` for the full threshold sweep and utility
  comparisons.

## Outputs and limits

The run writes to the Git-ignored `outputs/` directory:

| Output | Contents |
|---|---|
| `quality_report.json` | Aggregate ingestion, identity, and suppression counts |
| `network_metrics_2001.csv` | Monthly network metrics and resampling ranges |
| `findings.json` | Computed finding and adjacent-month comparison |
| `privacy_assessment.json` | Aggregate signature matches and utility by threshold |
| `person_edges_2001.csv`, `organization_edges_2001.csv` | Sensitive node-level edges; only with `EXPORT_EDGES=1` |

Bootstrap percentiles are weekday-stratified day-block resampling sensitivity
ranges, not population confidence intervals. They do not account for missing
or redacted mail or dependence across days. The privacy test is a limited
exact-signature attack; it does not prove anonymity or cover every source of
auxiliary information. Reproduction requires the same code revision, corpus,
key, and settings. Python and package versions are pinned, but the Docker base
image digest and cross-platform bit-for-bit results are not.
