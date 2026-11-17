# Enron metadata analysis

This case study analyses communication patterns using email metadata only.
It follows four steps: ingest and clean; pseudonymise; analyse; assess
re-identification risk.

## Run it

Prerequisites: Docker, the Enron corpus, and an external HMAC key file of at
least 32 bytes. The corpus and key are not in this GitHub repository; obtain
the same versions to reproduce the reported results. The default paths are
`enron_mail_20150507/maildir` and `../secrets/hmac.key`.

For the quickest run, start the analysis without running tests:

```sh
bash ./run.sh
```

This skips the separate test-image build and test-suite run, so it avoids that
extra startup time before processing the corpus. The corpus analysis itself
still runs as usual.

To validate the code before analysis, run the tests first:

```sh
bash ./run.sh --with-tests
```

This builds and runs the Docker test target, then starts the same analysis
only if the tests pass. It takes longer than the default option because of the
additional test-image build and test-suite run. **33 tests passed** in the
documented validation. To run tests without processing the corpus:

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

## Simulated public-information inputs

The repository includes two inputs for a bounded, explicitly simulated
public-information scenario:

- `data/simulated_identity_names.csv` contains display-name/address/header
  observations extracted once from the included email corpus.
- `data/simulated_public_org_chart.json` transcribes the corporate-unit
  relationships in Figure 1 (page 3) of the cited FERC report.

The identity CSV is intentionally tracked so reviewers can inspect and use
the same fixture. It contains corpus-derived personal names and addresses;
these are evaluator identity references, **not independently verified public
attacker knowledge**. The report's org chart lists corporate units, not named
employees, and does not connect people or email addresses to those units.
Consequently, the pipeline reports these inputs but marks person-level
matching from the simulated public information as **not evaluated**.

The one-time extractor can create a separate inventory for manual comparison
with independent sources:

```sh
PYTHONPATH=src python3 -m enron_analysis.extract_names \
  --data-dir enron_mail_20150507/maildir \
  --output /tmp/simulated_identity_names.csv
```

It reads only `From`, `To`, `Cc`, and `Bcc` headers, includes `enron.com`
addresses by default, aggregates observed display-name variants, and creates
a new CSV with owner-only permissions. It will not overwrite an existing file.
Do not treat names extracted from mail as evidence of what an attacker could
independently learn from public sources.

## What the pipeline does

1. **Ingest and clean:** reads only `From`, `To`, `Cc`, `Bcc`, and `Date`, plus
   transient `Message-ID` for duplicate detection. Subject and other headers
   are discarded before parsing; reads stop at the header/body separator, so
   body bytes do not enter the parser. Malformed or separatorless messages are
   counted and handled.
2. **Pseudonymise:** conservatively resolves exact addresses and any explicit
   alias map before applying deterministic HMAC-SHA256 pseudonyms, with
   separate person and organization namespaces. Addresses are normalized by
   lowercasing both the local part and domain, so addresses differing only in
   local-part capitalization are merged. Although this matches common email
   practice, the email standard permits case-sensitive local parts; this
   choice can conflate distinct mailboxes in that uncommon case. The key and
   non-empty alias map stay outside the repository.
3. **Analyse:** builds directed, weighted person and email-domain-proxy
   networks and reports monthly 2001 metrics. Domain nodes are proxies, not
   verified organizations.
4. **Assess risk:** reports a simulated public-information scenario using the
   FERC corporate-unit chart and the corpus-derived identity reference above.
   The simulated attacker does not have the mailboxes, HMAC key, or alias map.
   Person-level matching is **not evaluated** because the chart names no
   employees and provides no person-to-unit mapping. A separate
   public-mailbox-corpus scenario compares structural and temporal graph
   signatures in memory, assuming the attacker has the original corpus and
   knows the suppression threshold, but not the key or alias map.

Pseudonymization is not anonymization: graph structure and timing may still
identify people. The mailbox-corpus comparison is not a measurement of risk
under the simulated public-information scenario. Original addresses used for
that comparison are transient and are not logged or persisted in reports. The
tracked name/address fixture is an explicit exception: it is included for
review and reproducibility, and should not be mistaken for public-source
attacker data. Aggregate reports are the default; edge exports contain
pseudonymous node-level links and remain sensitive.

## Results from the included corpus

These are computed results from the local corpus version, which has had some
messages redacted and some addresses inferred from recipient names. Inferred
addresses are not verified; results describe this modified corpus, not the
complete historical record.

- 517,371 messages parsed; 272,934 dated in 2001.
- Resolved person-network interactions peaked in October 2001 at **301,523**.
  The bootstrap ranges for October and September did not overlap; October and
  November did overlap. This is descriptive, not causal.
- In the **separate public-mailbox-corpus scenario**, the test finds exact
  signature matches, not general probabilities of re-identification. At the
  default \(k=5\), post-suppression temporal match rates were 37.73% for people
  and 47.20% for organization proxies; interaction retention was 75.56% and
  67.34%, respectively. These figures do not estimate the simulated
  public-information scenario.
- Raising \(k\) is not a reliable privacy control: match rates are
  non-monotonic, and suppression can leave a smaller, more distinctive graph.
  See the `public_mailbox_corpus_access` scenario in
  `privacy_assessment.json` for its full threshold sweep and utility
  comparisons. Person-level methods in the simulated public-information
  scenario are explicitly marked `not_evaluated`, with the source-data
  limitation reported.

## Outputs and limits

The run writes to the Git-ignored `outputs/` directory:

| Output | Contents |
|---|---|
| `quality_report.json` | Aggregate ingestion, identity, and suppression counts |
| `network_metrics_2001.csv` | Monthly network metrics and resampling ranges |
| `findings.json` | Computed finding and adjacent-month comparison |
| `privacy_assessment.json` | Simulated public-information inputs and evaluation limits, plus separate mailbox-corpus signature matches and utility by threshold |
| `person_edges_2001.csv`, `organization_edges_2001.csv` | Sensitive node-level edges; only with `EXPORT_EDGES=1` |

Bootstrap percentiles are weekday-stratified day-block resampling sensitivity
ranges, not population confidence intervals. They do not account for missing
or redacted mail or dependence across days. The public-mailbox-corpus privacy
test is a limited exact-signature attack; it does not prove anonymity. The
simulated public-information inputs do not support person-level matching, so
the mailbox-corpus match rates should not be used as estimates for that
scenario.
Reproduction requires the same code revision, corpus, key, and settings.
Python and package versions are pinned, but the Docker base image digest and
cross-platform bit-for-bit results are not.
