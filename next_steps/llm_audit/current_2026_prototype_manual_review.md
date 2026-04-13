# Manual Review: Current 2026 Path/Mediator Prototype

Date: 2026-04-05

## Bottom line

The prototype is a meaningful improvement over the current direct-edge wording.

The strongest conclusion is:

- the **final surfaced object should usually not be a direct-edge question**
- the **path-question framing is usually better**
- the **mediator-question framing is useful for a smaller but real subset**

So the prototype succeeded in the main thing it was supposed to test.

## What clearly improved

### 1. The question object now matches the evidence better

Many current candidates already carry local support through intermediate nodes. The new path template reflects that directly.

Examples that look clearly better:

- `How might international trade (trade flows) change green growth?`
  becomes
  `Through which nearby pathways might international trade (trade flows) shape green growth?`

- `How might foreign direct investments change catastrophic health expenditures?`
  becomes
  `Through which nearby pathways might foreign direct investments shape catastrophic health expenditures?`

- `How might foreign direct investments change life expectancy?`
  becomes
  `Which nearby mechanisms most plausibly link foreign direct investments to life expectancy?`

These are closer to what the graph is actually showing.

### 2. The first-step guidance is better aligned

The prototype no longer implies that all top candidates are ready for a direct empirical test.

Instead it distinguishes:

- path questions that deserve follow-up now
- path questions that are lower priority
- mechanism questions that are really about channels

That is a better fit for both the paper and the product.

### 3. The route mix is informative

On the full ranked window of 120:

- `81` promote as path questions
- `29` downrank as path questions
- `7` promote as mediator questions
- `2` downrank as mediator questions
- `1` remain direct-edge

So even after manual inspection, the main takeaway still holds:

- the system is retrieving useful objects
- but most of them are better represented as **path-level** rather than **direct-edge** questions

## What still feels off

### 1. Some promoted path questions are still too broad or too generic

This is the biggest remaining issue.

Examples:

- `Through which nearby pathways might high-frequency trading shape prices?`
- `Through which nearby pathways might Special economic zones shape inequality?`
- `Through which nearby pathways might information and communication technology (ICT) shape welfare?`

These are better than the direct-edge versions, but some still feel too broad to be strong shortlist objects.

So:

- path framing improves the object
- but path framing alone does **not** solve genericity

This means the next ranking stage still matters a lot.

### 2. Some endpoint labels remain awkward for product-facing output

Examples:

- `cyclical component`
- `new-type urbanization`
- `TVP-SV-VAR model`
- `welfare level`

These are not caused by the new path layer. They are current ontology / display-label issues surfacing more clearly.

So the prototype is useful partly because it reveals which labels still read badly in final presentation.

### 3. The single direct-edge exception should not be overinterpreted

The lone kept direct-edge case:

- `How might monetary policy shocks change cyclical component?`

is not strong enough to justify a large direct-edge bucket.

It should be treated as:

- possible exception
- not evidence that direct-edge should remain a major final object

## Practical interpretation

The prototype says:

1. **Keep current retrieval**
2. **Change the surfaced object**
3. **Still improve ranking within the new object families**

That is a very useful sequence.

## Recommendation for next steps

### Immediate

- keep this prototype internal
- do not ship publicly yet
- use it to revise how the paper talks about the object

### Next modeling step

Build the learned reranker on the current ontology, but think of its target as:

- which path questions are worth promoting
- which mediator questions are worth promoting

not only:

- which direct edges appear next

### Deferred

Once the paper direction is settled:

- wire the path/mediator layer into the public export pipeline
- then separately improve endpoint labels and ontology presentation

## My judgment

If the question is:

- "Did this prototype justify the move away from direct-edge output?"

the answer is **yes**.

If the question is:

- "Is the prototype already ready to ship publicly as-is?"

the answer is **not yet**.

It is good enough to guide the paper and the next model step, but not yet polished enough to be the final public-facing layer.
