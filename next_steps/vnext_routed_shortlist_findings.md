# vNext Routed Shortlist Findings

## What we changed

We added a conservative routing layer on top of the active path/mechanism shortlist.

Routing rule:
- emit `context_transfer` when context gap is high enough to land in the top quartile of the direct-scored context-transfer family
- emit `evidence_type_expansion` when evidence design is narrow enough to land in the top quartile of the direct-scored evidence-expansion family
- otherwise keep the baseline path/mechanism object

## Counts

- changed rows: `21`
- changed unique pairs: `11`
- context threshold (q75): `0.654`
- evidence threshold (q75): `0.804`
- suppression counts: `{'low_support_blocked_evidence': 2}`

## First read

This is the right kind of upgrade.

The routing layer does not overwrite the whole shortlist. It only upgrades the object when the richer ontology signal is unusually strong.
It also now blocks context-transfer routing when the endpoint labels are too generic.

That makes the result easier to trust and easier to explain.

## What to review next

We should now compare the changed rows against their baseline titles and ask whether the routed object is genuinely more useful, or just more specific.
