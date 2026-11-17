# Results

This report documents the full pipeline run on 2026-11-17 using the local
Enron corpus, the default edge-suppression threshold \(k=5\), and the current
repository version. The corpus is a modified local copy with some messages
redacted and some addresses inferred from recipient names; it is not the
complete historical record.

The run was started with node-level edge export enabled:

```sh
EXPORT_EDGES=1 bash ./run.sh --with-tests
```

The Docker test suite passed (**34 tests**), then the corpus analysis completed.
This intentionally produced pseudonymized node-level edges in the ignored
`outputs/` directory for examination. Treat these files as sensitive; they
were not added to Git.

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
at **301,523**. The table gives all months' interaction counts and
weekday-stratified day-block bootstrap percentile ranges (200 replicates),
alongside network size and reciprocity. The ranges describe within-corpus
resampling sensitivity, not population confidence intervals. **Bold** marks
the October interaction peak and the higher October–November reciprocity.

| Month | Interactions (2.5th–97.5th percentile range) | Range overlaps October? | Active nodes | Directed ties | Reciprocity |
|---|---:|---:|---:|---:|---:|
| January 2001 | 156,817 (134,701–177,683) | No | 7,279 | 18,874 | 11.2% |
| February 2001 | 172,825 (151,203–195,009) | No | 8,953 | 21,319 | 10.1% |
| March 2001 | 252,270 (217,691–281,772) | Yes | 9,180 | 26,527 | 11.7% |
| April 2001 | 289,158 (262,191–317,374) | Yes | 12,549 | 30,810 | 11.1% |
| May 2001 | 277,577 (242,872–315,841) | Yes | 15,205 | 43,994 | 9.7% |
| June 2001 | 144,392 (103,825–197,579) | No | 11,724 | 33,767 | 7.9% |
| July 2001 | 75,880 (65,870–84,984) | No | 7,901 | 18,983 | 9.1% |
| August 2001 | 58,224 (47,728–75,333) | No | 8,537 | 20,856 | 9.9% |
| September 2001 | 80,259 (68,627–93,956) | No | 11,841 | 28,185 | 10.8% |
| **October 2001** | **301,523 (253,997–359,881)** | — | **18,133** | **53,247** | **16.1%** |
| November 2001 | 223,883 (161,127–286,803) | Yes | 15,338 | 43,816 | **16.4%** |
| December 2001 | 50,179 (43,169–56,756) | No | 8,600 | 18,712 | 13.9% |

October had the highest observed interaction count and the largest network
measured by active nodes and directed ties. Reciprocity, the share of directed
ties that also existed in reverse, was higher in October and November than in
the other listed months. By December, activity and network size were much
lower. The October-range overlap column compares each month's resampling range
with October's; overlap is not a formal significance test and does not show
that two months had equivalent activity. These are descriptive changes, not
evidence about their cause. The resampling does not account for missing or
redacted mail or dependence across days, and structural metrics also vary with
monthly activity.

## Public-information simulation: no security result

The public-information simulation **did not establish anything about whether
the release is secure against the customer's attacker**. It assembled
counterfactual inputs—a corpus-derived name/address fixture and a public FERC
corporate-unit chart—but did not complete a person-to-pseudonym or
person-to-network match. The input counts below describe the fixture; they
are not attack successes, security measurements, or evidence that the risk is
low.

| Simulated input or step | Result | What it tells us |
|---|---:|---|
| Corpus-derived name/address/header records | 2,366 | Fixture size only; not independently verified public information |
| Distinct addresses in the fixture | 1,857 | Fixture coverage only |
| Distinct display names in the fixture | 115 | Fixture coverage only; name variants and errors are possible |
| FERC org-chart entities / relationships | 11 / 10 | Corporate-unit hierarchy; it does not identify employees |
| Link names or addresses to released pseudonyms | Not evaluated | The exported edges contain no address-to-pseudonym mapping |
| Match people or departments to network positions | Not evaluated | No independent person-to-department evidence was collected |
| Security under the public-information threat model | **No conclusion** | The simulation did not perform a measurable attack |

For the simulation, the corpus-derived names and name-to-email associations
were treated as if public, and the attacker was assumed to know the FERC chart
and see the pseudonymized edge exports—but not the raw mailboxes, HMAC key, or
alias map. That assumption does not make the fixture independently public.
The plausible attack would need outside evidence linking people to roles or
departments, then a method to match those affiliations to network patterns.
The FERC chart lists units, not staff. Since neither that evidence nor a
person-to-pseudonym linkage was available, the scenario stopped before an
attack result could be measured. `outputs/privacy_assessment.json` records
the relevant methods as `not_evaluable`. This means **unknown risk**, not no
risk.

The chart was transcribed from the Federal Energy Regulatory Commission's
*Report on EnronOnline*, dated August 16, 2001, Figure 1, “Organization Chart
of Enron Corp,” page 3:
[archived FERC report](https://web.archive.org/web/20100527135242/https://www.ferc.gov/industries/electric/indus-act/wec/enron/rpt-enron-online.pdf).
The separate mailbox-corpus comparison below does produce match rates, but
assumes access to the original mailbox corpus. It is not a substitute for the
missing public-information attack and says nothing direct about the customer's
weaker attacker scenario.

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
identify people. Aggregate reports are the default; the node-level edge
exports from this run contain sensitive pseudonymous links.

## Generated reports

The pipeline wrote these files to the Git-ignored `outputs/` directory:

| File | Contents |
|---|---|
| `quality_report.json` | Aggregate ingestion, identity, and suppression counts |
| `network_metrics_2001.csv` | Monthly network metrics and resampling ranges |
| `findings.json` | Peak activity finding and adjacent-month comparisons |
| `privacy_assessment.json` | Simulated public-information inputs and evaluation status, plus the separate mailbox-corpus comparison |
| `person_edges_2001.csv` | 87,527 sensitive pseudonymous monthly person-edge rows |
| `organization_edges_2001.csv` | 7,885 sensitive pseudonymous monthly organization-proxy edge rows |

Results require the same code revision, corpus, key, alias map, and settings to
reproduce. Python and package versions are pinned; the Docker base image digest
and cross-platform bit-for-bit reproducibility are not. Edge CSVs are ignored
by Git, created with owner-only permissions, and should be handled as sensitive
data.
