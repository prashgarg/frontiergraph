# Option C Intro and Object Rewrite

Date: 2026-04-12

This note gives the exact front-end rewrite for the paper under Option C.

The point is to prepare the manuscript now without forcing a premature decision about
which family deserves rhetorical priority. The empirical comparison is still running.
The text below therefore changes the framing, not the final claims.

## 1. Opening introduction draft

Use this as the new opening sequence.

### Paragraph 1

Choosing what to work on is one of the least formalized decisions in economics. We have
disciplined frameworks for identification, estimation, and inference, but much less for
the upstream choice of which question deserves scarce attention in the first place. As
the stock of published work grows, that choice becomes harder. The problem is not only to
find a question. It is to decide which among many plausible next questions is worth
reading, testing, or developing first.

### Paragraph 2

This paper studies whether the structure of past research can help with that choice. I
build a directed literature graph from economics and economics-adjacent papers and use it
to surface two kinds of candidate next questions. In the first, the literature already
contains a direct relation, but later work adds a clearer channel around it. In the
second, the literature already contains local support for a relation, but the direct link
itself is still missing and only appears later. Economists often care most about the
first object because it asks about mechanisms. The second is also useful because it
captures cases where the local structure of the literature points toward a direct
relation that later becomes explicit.

### Paragraph 3

An example makes the distinction concrete. Suppose the literature already links broadband
access to business formation. Later work may connect the two more explicitly through
search frictions, market access, or information costs. That is a mechanism-thickening
question. Now consider a case where the literature already contains trade liberalization
to imported inputs and imported inputs to firm productivity, but not yet a direct trade
liberalization to firm productivity relation. That is a direct-closure question. The
paper studies both objects prospectively in the same graph.

### Paragraph 4

The comparison is simple. At each date, I use only the papers that already existed, rank
still-open candidate questions, and then ask which of them later become part of published
work. I compare a simple graph-based score, a richer ranking rule built on the same graph,
and a simple popularity rule. The popularity rule matters because it captures a plausible
view of how attention moves in research. If future work mostly follows visibility and
existing activity, popularity should be hard to beat.

### Paragraph 5

The paper's broader aim is not to replace judgment with a graph. It is to ask whether the
graph can help direct scarce reading time. Some candidate questions are too obvious,
others are too far from existing work, and some may have been overlooked for good reasons.
The graph cannot settle those distinctions by itself. What it can do is organize local
evidence about which questions are structurally supported, which are mechanism-rich, and
which sit in parts of the literature where a researcher is most likely to learn something
from looking next.

### Paragraph 6

The paper therefore has two empirical layers. The first is historical: do graph-ranked
questions line up better with what later becomes part of the literature? The second is
substantive: what kinds of questions are surfaced, and where does the graph help most?
The main text should compare the two graph objects directly, show how the ranking changes
once a richer rule is allowed, and then return to the kinds of mechanism and path
questions that the graph surfaces.

## 2. Replacement paragraph for the contribution overview

Use this after the opening sequence and before the literature review if the paper still
wants one compact summary paragraph.

This paper contributes in three ways. First, it defines two prospective graph-based
objects for question choice in economics: later mechanism thickening around an existing
direct claim, and later direct closure of a locally supported but still missing relation.
Second, it compares graph-based screening with a simple popularity rule under the reading
constraint that matters most in practice: which questions enter the first short list.
Third, it uses the same graph to study where each object is most informative and what
sorts of questions it actually surfaces.

## 3. Object-definition section draft

This is the text that should appear near the benchmark-anchor / surfaced-question
discussion, before the main results.

### Paragraph 1

The graph supports two distinct historical objects. In a `direct-to-path` case, the
literature already contains a direct relation at date \(t-1\), but the surrounding
mechanism is still thin. Later work adds a mediating path around that relation. In a
`path-to-direct` case, the literature already contains a local path at date \(t-1\), but
the direct relation itself is still missing. Later work states that direct relation
explicitly. Both objects are dated using only the graph that existed at \(t-1\).

### Paragraph 2

The distinction matters substantively. The first object asks whether a known relation is
later given a clearer channel. The second asks whether local structure already points
toward a direct relation that later becomes explicit. Economists will often find the
first object more natural because the literature is often organized around mechanisms. The
second object is still useful because direct relations remain legitimate economic
questions, and because some later papers do make those links explicit rather than only
thickening the path around them.

### Paragraph 3

The benchmark event and the surfaced question are still separate. The historical event is
whether the relevant direct edge or path appears later in the graph. The surfaced
question is the richer, human-readable object built around the local neighborhood. That
separation matters because a researcher does not inspect a bare graph event. A researcher
inspects a question about channels, outcomes, and nearby support.

### Paragraph 4

The paper does not try to benchmark the most open-ended cases where a later question
introduces a genuinely new concept or bridges two distant regions of the graph without a
clear local scaffold. Those cases matter, but they are a different object. The present
paper stays with graph-grounded next questions that are already anchored in local
structure at date \(t-1\).

## 4. Section-opening draft for the results

Use this at the start of the main results section once the dual-family runs are complete.

The results now compare two forms of research progress rather than one. In one, the
literature later makes a direct relation explicit. In the other, it later thickens an
existing relation by adding a clearer path around it. The first question is whether graph
structure improves on popularity in each object. The second is whether the same ranking
logic works equally well for both. The third is where each object is most informative once
the reading budget and the surrounding literature are taken into account.

## 5. Discussion paragraph draft

Use this in the discussion once the side-by-side results exist.

The comparison between direct closure and mechanism thickening is useful because it
matches two ways economists think about the next paper. Sometimes the missing piece is a
channel around a relation the literature already accepts. Sometimes the missing piece is
the direct relation itself, even though nearby work already points in that direction. The
paper does not require one object to dominate the other in the abstract. It asks how the
two behave empirically and where each is most useful as a screening target.

## 6. Intro example pool

These are the recommended example families for the introduction and early figures.

### Strong `direct-to-path` examples

- broadband access -> business formation, later thickened by search frictions
- trade liberalization -> firm productivity, later thickened by imported inputs
- transit investment -> employment, later thickened by commute time

### Strong `path-to-direct` examples

- trade liberalization -> imported inputs -> firm productivity, later direct relation
- childcare subsidies -> maternal labor supply -> household income, later direct relation
- transit investment -> commute time -> employment, later direct relation

### Examples to avoid as lead examples

- cases where the direct edge sounds obviously like the wrong estimand
- cases where the path is so canonical that the direct edge feels like a rhetorical
  shortcut rather than a real economic question

## 7. Writing rule

Until the dual-family empirical comparison finishes, the manuscript should not say:

- that one family is the cleaner validation object
- that one family is economically more important
- that one family is the true target and the other is only auxiliary

It should instead say:

- the paper studies two prospective graph-grounded next-question objects
- one is closer to channel discovery
- the other is closer to direct relation closure
- the comparison between them is part of the paper's contribution
