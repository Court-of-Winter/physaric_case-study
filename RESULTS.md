# Results

This report documents the full pipeline run on 2026-11-17 using the local
Enron corpus, the default edge-suppression threshold \(k=5\), and the current
repository version. The corpus is a modified local copy with some messages
redacted and some addresses inferred from recipient names; it is not the
complete historical record.

The run was started with:

```sh
bash ./run.sh --with-tests
```

The Docker test suite passed (**34 tests**), then the corpus analysis completed.
The default run did not export node-level edge CSVs.

## Ingestion

| Measure | Result |
|---|---:|
| Files scanned | 517,401 |
| Messages parsed | 517,371 |
| Messages dated in 2001 | 272,934 |
| Messages dated outside 2001 | 244,437 |
| Missing sender | 3 |
| Missing header/body separator | 30 |
| Malformed headers | 30 |
| Invalid addresses | 137 |
| Person-network monthly dyad groups suppressed at \(k=5\) | 271,563 |
| Organization-proxy monthly dyad groups suppressed at \(k=5\) | 30,331 |

Messages without a usable date and files with oversized headers are handled by
the pipeline's quality checks; their counts are in `outputs/quality_report.json`.

## Network activity

Resolved person-network message-recipient interactions peaked in October 2001
at **301,523**. The table shows the peak and adjacent months with
weekday-stratified day-block bootstrap percentile ranges (200 replicates).
These ranges describe within-corpus resampling sensitivity, not population
confidence intervals.

| Month | Interactions | 2.5th–97.5th percentile range | Range overlaps October? |
|---|---:|---:|---|
| September 2001 | 80,259 | 68,627–93,956 | No |
| October 2001 | 301,523 | 253,997–359,881 | — |
| November 2001 | 223,883 | 161,127–286,803 | Yes |

This is descriptive and does not establish a cause for the observed pattern.
The resampling does not account for missing or redacted mail or dependence
across days.

## Simulated public-information scenario

The pipeline loaded and reported the simulation inputs, but **did not produce
a person-level re-identification score**. Results are marked
`not_evaluated` in `outputs/privacy_assessment.json`; reporting that status is
the outcome of this run, not a zero-risk result.

| Input or method | Result | Interpretation |
|---|---:|---|
| Corpus-derived name/address/header records | 2,366 | Evaluator reference data extracted from email headers |
| Distinct addresses in the fixture | 1,857 | Addresses are not independently verified public facts |
| Distinct display names in the fixture | 115 | Name variants and errors are possible |
| FERC org-chart entities | 11 | Corporate units, not named people |
| FERC org-chart relationships | 10 | Figure 1, page 3 of the cited report |
| Display-name-only matching | Not evaluable | The names come from the corpus, while released reports do not contain display names |
| Matching people to org-chart relationships | Not evaluable | The chart contains no employees or person-to-unit mapping |

The org chart was transcribed from the Federal Energy Regulatory Commission's
*Report on EnronOnline*, dated August 16, 2001, Figure 1, “Organization Chart
of Enron Corp,” page 3:
[archived FERC report](https://web.archive.org/web/20100527135242/https://www.ferc.gov/industries/electric/indus-act/wec/enron/rpt-enron-online.pdf).
The name/address fixture is explicitly corpus-derived and should not be
presented as information an independent public attacker would necessarily
know. These two inputs support a reproducible simulation fixture, but do not
currently suffice to test the customer public-information threat model.

## Separate public-mailbox-corpus comparison

This is a distinct, stronger-information comparison: the simulated attacker
has the original mailbox corpus and knows the release threshold, but not the
HMAC key or alias map. It uses unique exact matches of structural and
12-month temporal degree/strength signatures. These match rates are not
probabilities of re-identification and do **not** estimate risk in the
public-information scenario above.

| Network | Signature | Before suppression: unique / candidates (rate) | After \(k=5\): unique / nodes (rate) |
|---|---|---:|---:|
| Person | Structural | 7,110 / 60,277 (11.80%) | 3,008 / 14,475 (20.78%) |
| Person | Temporal | 15,026 / 60,277 (24.93%) | 5,462 / 14,475 (37.73%) |
| Organization proxy | Structural | 1,388 / 9,246 (15.01%) | 556 / 2,057 (27.03%) |
| Organization proxy | Temporal | 3,022 / 9,246 (32.68%) | 971 / 2,057 (47.20%) |

Increasing the suppression threshold reduces utility but does not guarantee
lower signature match rates; the full tested threshold sweep
(\(k=5,10,25,50,100\), including the configured value) is in
`outputs/privacy_assessment.json`.

| Network | Interaction retention | Directed-edge retention | Node retention |
|---|---:|---:|---:|
| Person | 75.56% | 22.74% | 24.01% |
| Organization proxy | 67.34% | 19.45% | 22.25% |

## Identity normalization and interpretation

Email addresses are normalized by lowercasing both the local part and domain.
This intentionally merges addresses that differ only by local-part
capitalization. Although common in practice, local parts can technically be
case-sensitive, so distinct mailboxes could be conflated. Pseudonyms and
network results depend on this normalization choice.

Pseudonymization is not anonymization. Graph structure and timing may still
identify people. Aggregate reports are the default; node-level edge exports
contain sensitive pseudonymous links and were not generated in this run.

## Generated reports

The pipeline wrote these files to the Git-ignored `outputs/` directory:

| File | Contents |
|---|---|
| `quality_report.json` | Aggregate ingestion, identity, and suppression counts |
| `network_metrics_2001.csv` | Monthly network metrics and resampling ranges |
| `findings.json` | Peak activity finding and adjacent-month comparisons |
| `privacy_assessment.json` | Simulated public-information inputs and evaluation status, plus the separate mailbox-corpus comparison |

Results require the same code revision, corpus, key, alias map, and settings to
reproduce. Python and package versions are pinned; the Docker base image digest
and cross-platform bit-for-bit reproducibility are not.
