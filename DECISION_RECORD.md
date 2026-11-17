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

I kept the two risk scenarios separate because they answer different
questions. The mailbox-corpus comparison matches structural and temporal
signatures using the original mailbox graph. Its raw identity edges exist in
memory for the calculation, but are not pseudonymized or written to reports.
This tests a stronger attacker than the customer described: one who has the
mailbox corpus. The public-information exercise did not answer whether the
customer's release is secure. I assembled a counterfactual fixture of names
extracted from the email corpus and the FERC corporate org chart, but did not
link people to pseudonyms or to positions in the released graph. The fixture
and chart therefore document possible inputs, not an attack result or a
security assessment. That scenario remains unevaluated.

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

The public-information simulation did not provide evidence about the actual
security of the release under the customer's threat model. In part, I lack
knowledge of how press coverage could help an attacker, so I did not know
which sources or person-to-department claims to investigate. In part, I ran
out of time before collecting and verifying that evidence or building the
attacker workflow. The names in the fixture came from the email corpus, while
the FERC chart identifies corporate units but not employees; treating those
names as public did not create an independent link to the pseudonymous graph.
As a result, the simulation ended at input preparation and produced no
measurable attack result. The mailbox-corpus signature results are evidence
only for their stronger mailbox-access scenario and cannot fill that gap.
