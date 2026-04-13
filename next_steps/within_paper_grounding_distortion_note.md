# Within-Paper Grounding Distortion

This diagnostic measures how much a global grounding layer collapses distinct within-paper nodes and edges.

| Variant | Papers with node collision | Node collision rate | Papers with edge collision | Edge collision rate | Papers with self loop | Self-loop rate | Papers with path collapse | Path collapse rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct threshold only (`>=0.75`) | 7,456 | 0.016 | 1,129 | 0.009 | 1,884 | 0.014 | 1,008 | 0.036 |
| Reviewed overlay, existing-concept attachments only | 10,167 | 0.019 | 2,054 | 0.012 | 2,430 | 0.012 | 1,661 | 0.035 |
| Reviewed overlay plus synthetic family nodes | 10,237 | 0.017 | 2,209 | 0.011 | 2,442 | 0.011 | 1,794 | 0.031 |

Interpretation:
- node collision means two distinct raw labels in the same paper map to the same grounded node
- edge collision means distinct raw edges collapse onto the same grounded edge
- self loops are edges that become source=target after grounding
- path collapse is a proxy for local structural compression in two-step paths
