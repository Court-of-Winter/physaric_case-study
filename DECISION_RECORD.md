# Decision record

## What I built

I kept the analysis focused on email metadata. The parser reads sender,
recipient, date, and message-ID headers, and stops at the header/body
separator. Addresses are normalized and mapped to deterministic HMAC-SHA256
pseudonyms, with separate namespaces for people and organization domains. The
pipeline builds daily communication edges, reports monthly network metrics,
and suppresses monthly dyads below a configurable threshold (default \(k=5\)).
Aggregate reports are the default; exporting node-level edges requires an
explicit opt-in because those edges remain sensitive even when pseudonymized.

I also kept two risk evaluations separate. The mailbox-corpus comparison
matches structural and temporal signatures using the original mailbox graph.
Its raw identity edges exist in memory for the calculation, but are not
pseudonymized or written to the reports. This is a stronger attacker
assumption than the customer described. For the simulated public-information
case, I included names extracted from the email corpus and the FERC corporate
org chart. The names are not independent public data, and the chart does not
name employees or connect people to departments. So the pipeline records the
fixture and its provenance, but marks person-level matching as not evaluated.

## Why I made these choices

Reading headers rather than message bodies limits what the analysis collects.
HMAC pseudonyms make routine reports less directly identifying, while
preserving the ability to build useful networks. Monthly aggregation and
suppression reduce the detail of a release, but do not guarantee anonymity:
the mailbox-corpus comparison found higher exact-signature match rates after
suppression, even though interaction counts were reduced. This is why I left
edge exports off by default and report the match rates as a separate scenario,
not as an estimate of the customer threat model.

I chose to lowercase both the local part and domain of each address. This
usually matches how email addresses are treated in practice and avoids
splitting one person across capitalization variants. However, local parts can
technically be case-sensitive, so this may merge distinct mailboxes. With
customer data, I would validate this assumption before using it.

## What I would change with real customer data

I would first agree on the attacker's likely access, target population, and
the exact outputs being considered for release. I would then build a
dated, sourced set of public names, roles, and organizational relationships,
including relevant press coverage, and verify identity links independently.
The attacker workflow should use only that public material and the proposed
release. Mailbox-derived identities and graphs should be kept separate as
evaluation ground truth, with restricted access and a defined retention
period. I would test aggregate reports and edge exports separately, then
review the remaining risk and suppression choices with the customer.

## Limits of this work

I did not have time to manually review every part of the codebase and so focused
on the components most important to privacy and went through the included
tests. Modifications are therefore limited to adding some assertions and the above mentioned case-insentive treatment of the local parts of email addresses.  
With more time I would have preferred to write some tests myself, especially for edge cases.

I also lack the experience to judge how press coverage could help an attacker,
so I did not assess that source systematically. Time did not allow me to build
a realistic attacker workflow either. The public-information exercise is
therefore only a documented simulation fixture based on names from the email
corpus and the FERC org chart; it produces no person-level re-identification
result. The mailbox-corpus signature results answer a different, stronger
attacker scenario and should not be used as a substitute.
