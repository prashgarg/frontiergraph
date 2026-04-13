# v2.3 Ontology Policy

This note governs the conservative Pause 1 ontology closeout for `v2.3`.

## Core principles

- Raw provenance is immutable.
- `label`, `source`, `parent_label`, and `root_label` are never rewritten.
- Cleanup is display-layer only unless a source-backed alternative label exists in the ontology record itself.
- Parent-child additions must be defensible as ontology decisions, not as ranker hacks.
- Broad roots are allowed.

## Label policy

Allowed `change_basis` values:

- `format_only_normalization`
- `source_backed_display_cleanup`
- `no_change`
- `ambiguous_container`

Display cleanup rules:

- normalize spacing and Unicode quirks
- remove obvious footnote markers
- strip terminal JEL sentence punctuation in `display_label`
- prefer an alternate source label only when it is already attached to the same ontology row and is strictly cleaner without changing the concept
- do not freehand rewrite source labels into nicer prose

## Broad roots

The ontology may keep broad top-level anchors without forcing extra parents above them.

Examples:

- `economics`
- `mathematics`
- other high-level field labels such as `finance`, `politics`, `history`, `geography`, `sociology`, `psychology`, `education`, `technology`, `law`, `health`, and `medicine`

These may remain root-like even if some source-native hierarchy also attaches them upward.

## Ambiguous containers

Some labels are vague, adjective-like, or too underspecified to treat as clean paper-facing concepts.

Examples:

- `Behavioral`
- `Monetary`
- `Strategic.`
- `Sociocultural.`

These are allowed to exist, but they should be flagged as `ambiguous_container` rather than silently treated as precise ontology labels.

## Duplicate policy

Merge only when the evidence supports true same-concept identity.

Merge if at least one strict rule holds:

- cleaned display labels are equivalent
- the difference is only punctuation, case, spacing, or footnote markup
- the same ontology row already carries a cleaner source-backed alias

Do not merge when:

- one label adds a substantive modifier
- the pair is broader versus narrower
- the pair is better understood as siblings in one family
- the evidence is only weak semantic similarity

## Intermediate-parent policy

Add an intermediate parent only when it is:

- standard
- reusable
- materially better than the current broad direct parent

Do not add hierarchy only to make the tree deeper.

Intermediate review must be based on:

- repeated child support
- a coherent child set
- a standard target concept or family
- explicit review evidence

If the parent zone itself is still dirty or under-specified, park the case instead of forcing an intermediate.

## Pause 1 standard

Pause 1 is successful if we can produce a coherent `v2.3` candidate with:

- explicit `display_label`
- explicit label-policy sidecars
- explicit duplicate-resolution sidecars
- explicit intermediate-review sidecars
- provenance preserved
- hierarchy validated
- unresolved backlog parked rather than hidden

No ranker or frontier result is allowed to justify an ontology choice in this phase.
