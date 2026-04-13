# Paper Line-by-Line Change Log

Date: 2026-04-11

This file records the exhaustive zero-context diff for the paper manuscript and the paper-refresh support notes.

## Files included

- paper/research_allocation_paper.tex
- next_steps/paper_refresh_checklist_2026_04_11.md
- next_steps/paper_consistency_audit_findings_2026_04_11.md
- next_steps/full_paper_refresh_audit_2026_04_11.md
- next_steps/current_locked_vs_open_decisions.md
- next_steps/method_v2_design.md
- next_steps/method_v2_path_to_direct_refresh_status.md

## Diff stat

```
 paper/research_allocation_paper.tex | 962 +++++++++++++++++++++++++++++-------
 1 file changed, 781 insertions(+), 181 deletions(-)
```

## Zero-context diff

```diff
diff --git a/paper/research_allocation_paper.tex b/paper/research_allocation_paper.tex
index d9343e4..ab0c3a2 100644
--- a/paper/research_allocation_paper.tex
+++ b/paper/research_allocation_paper.tex
@@ -24 +24 @@
-\usetikzlibrary{arrows.meta,positioning,shapes.geometric,fit,calc,backgrounds}
+\usetikzlibrary{arrows.meta,positioning,shapes.geometric,fit,calc,backgrounds,decorations.pathreplacing}
@@ -28 +28 @@
-\graphicspath{{../outputs/paper/figures/}{../outputs/paper/slides_figures/}{../outputs/paper/13_heterogeneity_atlas/figures/}{../outputs/paper/14_title_revision/}}
+\setlength{\emergencystretch}{1.5em}
@@ -53 +53 @@
-  \VerbatimInput[fontsize=\scriptsize,breaklines=true,breakanywhere=true]{#1}
+  \VerbatimInput[fontsize=\tiny,breaklines=true,breakanywhere=true]{#1}
@@ -59 +59 @@
-\title{\textbf{What Should Economics Ask Next?}\\[0.35em]\large A graph-based screening benchmark for candidate questions in economics}
+\title{\textbf{What Should Economics Ask Next?}\\[0.35em]\large A benchmark for screening candidate questions in economics}
@@ -61 +61 @@
-\date{17 March 2026\\[0.3em]\normalsize Draft for comments. Please do not cite without permission.}
+\date{6 April 2026\\[0.3em]\normalsize Draft for comments. Please do not cite without permission.}
@@ -68 +68,3 @@
-As AI makes drafting, coding, and reviewing cheaper, choosing the right research question may become a more important bottleneck. This paper studies that problem in economics by representing plausible next questions as missing links in a directed map of the literature and ranking them using patterns in the surrounding research neighborhood. I build this map from over 240{,}000 papers in core economics and adjacent journals published over the last 50 years (1976 to early 2026), and test whether the ranking predicts connections that later emerge in the literature. A simple baseline that favors already well-connected topics performs better at the very top of the ranking, but the graph-based score becomes more useful once researchers look beyond just the top few suggestions, especially in adjacent journals, design-based causal work, and areas of the literature with many nearby pathways. The contribution is practical rather than universal: the method helps surface plausible next questions and helps researchers see why each suggestion is being made.
+As AI lowers the cost of drafting, coding, and reviewing, the scarce input in research may shift toward question choice. This paper studies that problem in economics. I build a directed claim graph from 242{,}595 published papers (1976--2026) and ask whether missing directed links---relations that nearby structure suggests but that no paper has yet established---can screen candidate next questions better than cumulative advantage alone. The benchmark is prospective: freeze the graph at year \(t{-}1\), rank missing links, and check which ones later appear. The main null is preferential attachment.
+
+A transparent graph score is readable and, on the current main benchmark, already beats preferential attachment at the strict shortlist margin. A learned reranker---using only graph-derived features with walk-forward temporal discipline---improves materially further: it beats both transparent retrieval and preferential attachment at every main horizon tested. The reranker also generalizes forward to a fully held-out era. Broader shortlists, value-weighted outcomes, and heterogeneity by journal tier and method family all point in the same direction: graph structure adds the most screening value when the reading budget is tight and the local graph is informative enough to guide selection.
@@ -75,3 +77 @@ As AI makes drafting, coding, and reviewing cheaper, choosing the right research
-Choosing what to work on is one of the least formalized decisions in economics. We have disciplined frameworks for identification, estimation, and inference, but much less for the upstream choice of which question deserves scarce attention in the first place. Bloom et al.~\citeyearpar{bloom2020ideas} argue that ideas are getting harder to find, while Jones~\citeyearpar{jones2009burden} emphasizes the growing knowledge burden faced by new researchers. Those arguments point in the same direction: the frontier becomes harder to navigate even as the stock of published work keeps growing.
-
-That problem becomes sharper, not weaker, when AI lowers the cost of adjacent research tasks such as drafting, review assistance, and iterative revision. If downstream paper-production tasks become cheaper, the bottleneck shifts upstream toward question choice. The question is no longer only how to write or review a paper more cheaply. It is how to decide which question deserves attention next.
+Choosing what to work on is one of the least formalized decisions in economics. We have disciplined frameworks for identification, estimation, and inference, but much less for the upstream choice of which question deserves scarce attention in the first place. Bloom et al.~\citeyearpar{bloom2020ideas} argue that ideas are getting harder to find, while Jones~\citeyearpar{jones2009burden} emphasizes the growing knowledge burden faced by new researchers. Those arguments point in the same direction: the frontier becomes harder to navigate even as the stock of published work keeps growing. And the problem is not only about productivity. Foster, Rzhetsky, and Evans~\citeyearpar{foster2015tradition} show that scientists overwhelmingly choose conservative strategies, even though riskier exploration disproportionately generates high-impact work. That means the question-choice problem is not just hard---it is systematically biased toward the familiar.
@@ -79 +79 @@ That problem becomes sharper, not weaker, when AI lowers the cost of adjacent re
-This paper studies that narrower empirical problem. It does not answer the welfare question of what economics ought to study in the abstract. It asks whether the structure of past research can help surface plausible next questions, and whether those suggestions can be made clear enough to inspect and use. I start by building a map of how topics connect across papers. In that map, possible next questions appear as connections that have not yet been made. Formally, I represent those as missing directed links in a literature map built from economics and adjacent journals. Suppose the literature already contains links such as public debt $\rightarrow$ public investment and public investment $\rightarrow$ CO\(_2\) emissions, but the direct relation public debt $\rightarrow$ CO\(_2\) emissions has not yet appeared. That missing direct connection is a concrete candidate question. The closest computational analogy is link prediction, but the object here is narrower and more interpretable than generic network completion. In this paper, ``should'' is therefore used in that narrower operational sense. A question deserves attention next when it is neglected enough to remain open, supported enough to be credible, concrete enough to become a paper, and worth reading under a realistic shortlist budget rather than only at a winner-take-all top rank. The website at \href{https://frontiergraph.com/}{frontiergraph.com} lets readers inspect those surfaced questions and the nearby evidence behind them.
+That problem becomes sharper, not weaker, when AI lowers the cost of adjacent research tasks such as drafting, review assistance, coding, and iterative revision \citep{korinek2024generative,agrawal2024ai}. If downstream paper-production tasks become cheaper, the bottleneck shifts upstream toward question choice. The relevant question is then narrower than ``what should economics study?'' in the abstract. It is whether the structure of past research can help screen candidate next questions in a disciplined way.
@@ -81 +81 @@ This paper studies that narrower empirical problem. It does not answer the welfa
-That map-based view is useful because it preserves more of the local logic of scientific development than keyword overlap or raw citation counts alone. It lets us see whether a putative question is supported by nearby chains of papers and topics, and only then name those features more formally as paths, motifs, and local graph structure. The framework is intentionally modest. It is a discovery aid, not proof of importance; a prospective ranking exercise, not a welfare theorem; and a graph of extracted claim relations, not a full adjudication of causal truth from complete papers.
+This paper studies that narrower empirical problem. I build a directed literature graph from economics-facing papers and use missing directed links as benchmarkable benchmark anchors. Suppose the literature already contains ``price changes $\rightarrow$ energy demand'' and ``energy demand $\rightarrow$ CO\(_2\) emissions,'' but not the direct relation ``price changes $\rightarrow$ CO\(_2\) emissions.'' The missing direct link is the benchmark anchor that later either appears or does not appear. A researcher, however, would rarely want to inspect only that raw anchor. The more natural question is richer: what nearby pathways could connect price changes to CO\(_2\) emissions, or which mechanisms most plausibly connect them? The paper therefore separates the benchmark anchor from the question a researcher actually reads.
@@ -83 +83 @@ That map-based view is useful because it preserves more of the local logic of sc
-The empirical design starts from a field-weighted citation impact selected corpus of top core and adjacent journals. The selected sample contains 242{,}595 papers spanning 1976 to early 2026, of which 230{,}929 contain at least one extracted edge and 230{,}479 survive into the normalized graph used in evaluation. I build that graph from the paper-level extraction framework in Garg and Fetzer~\citeyearpar{gargfetzer2025causal}, then distinguish between directed causal links and undirected contextual support inside a single graph object. Missing directed links are ranked by a graph-based score built from path support, underexploration gaps, motif support, and hub penalties. I then freeze the graph at year \(t-1\), rank candidates, and test whether those links first appear over 3-, 5-, 10-, and 15-year horizons.
+That separation is the organizing idea of the paper. The missing directed link is useful because it is clean, dated, and prospectively testable. It lets me compare graph-based screens with cumulative-advantage baselines on the same event: later link appearance. But the human-facing question is not generic link prediction. It is a screening problem under limited attention---what Kleinberg et al.~\citeyearpar{kleinberg2015prediction} call a ``prediction policy problem,'' where the binding constraint is which cases to inspect rather than what causal parameter to estimate.\footnote{Ludwig and Mullainathan~\citeyearpar{ludwig2024hypothesis} argue more broadly that ML can systematize hypothesis generation, a process they describe as remaining ``largely informal'' and at a ``prescientific'' stage in much of economics. The present paper can be read as an instance of that program, applied to the structure of past research rather than to individual-level behavioral data. Mullainathan and Spiess~\citeyearpar{mullainathan2017ml} provide the broader econometric framing: the benchmark here is a prediction (\(\hat{y}\)) problem, not an estimation (\(\hat\beta\)) problem.} A candidate question is useful if it is still open, nearby enough to be credible, concrete enough to become a paper, and readable enough to survive a shortlist. The public system at \href{https://frontiergraph.com/}{frontiergraph.com} lets readers inspect those surfaced questions and the nearby evidence behind them.
@@ -85 +85 @@ The empirical design starts from a field-weighted citation impact selected corpu
-The headline result is mixed and therefore informative. The toughest benchmark is a simple rule that favors topics that are already well connected. In network terms, that rule is preferential attachment, and it still wins in the pooled rolling benchmark at very tight shortlists. In concrete terms, a 100-question shortlist built from that benchmark retrieves roughly 2.6, 3.3, 7.0, and 10.0 more realized directed links than the graph score at \(h=3,5,10,15\). But that is not the end of the story. Once the shortlist widens, so that a researcher is willing to inspect more than just the top few suggestions, the graph-based score becomes more competitive. The newer heterogeneity results also suggest that pooled averages hide meaningful variation across journals, methods, and parts of the literature. A separate path-development exercise points to a second pattern: research often builds mediating structure around existing direct claims more often than it closes a direct link already implied by local paths.
+The benchmark comparison is intentionally simple in structure. At each year cutoff, I freeze the graph using the literature through \(t{-}1\), rank missing directed links, and ask whether those links later appear in the literature. In the main effective-corpus benchmark emphasized below, the reported five-year cutoff grid runs from 1990 through 2015, with earlier years included rather than dropped. That full benchmark matters for interpretation: the 1990 and 1995 cutoffs are not just noisier versions of the later sample. They have fewer realized positives and surface candidate objects with younger support, higher recent-share measures, and lower diversity and stability. The main economic null is preferential attachment: a popularity rule that favors topics that are already well connected. I then widen the transparent comparison to stronger simple baselines such as degree plus recency and directed closure, and finally allow a learned reranker to reweight the same graph candidate universe using only graph-derived features and the same vintage discipline. This keeps the benchmark honest without turning the paper into a black-box prediction exercise.
@@ -87 +87 @@ The headline result is mixed and therefore informative. The toughest benchmark i
-The paper makes three contributions. First, it proposes a way to rank plausible next questions using the nearby structure of the literature; I treat the resulting object as a benchmarked screening problem in a directed literature graph. Second, it shows where that nearby structure helps more, and how research often develops by adding mediator paths around existing direct claims rather than only closing missing direct links. Third, it makes the object inspectable through a public browser that exposes suggested questions, nearby topics, supporting paths, and starter papers.
+The headline result is layered rather than triumphant. On the current main benchmark, even the transparent graph score beats pure popularity at the strict top of the ranking. But a learned reranker---trained on the same graph features with walk-forward discipline---improves substantially further and beats both transparent retrieval and preferential attachment at every main horizon tested. The paper makes three contributions. First, it proposes a prospectively testable screening benchmark for candidate questions in economics by using missing directed links as benchmark anchors in a claim graph. Second, it shows why the object a researcher should inspect is usually richer than the anchor itself: path-rich and mechanism-rich questions are often more informative than bare missing edges. Third, it shows where local graph structure is more useful for screening, and where cumulative advantage remains dominant.
@@ -89 +89 @@ The paper makes three contributions. First, it proposes a way to rank plausible
-These findings connect the paper to several literatures at once. They speak to the economics of ideas and scientific search \citep{bloom2020ideas,jones2009burden}, to the science-of-science literature on novelty, impact, and frontier tracing \citep{uzzi2013atypical,fortunato2018science,wang2021science}, and to current work on AI-assisted scientific workflows and discovery systems \citep{zhang2025scientificmethod,shao2025sciscigpt}. They also speak to a practical question. The public system at \href{https://frontiergraph.com/}{frontiergraph.com} is meant to help researchers inspect why one candidate question surfaced, what local paths support it, and which nearby literatures are doing the work.
+The paper tests a specific tension in the research-allocation literature. If the future of any field is mostly driven by cumulative advantage---popular topics attracting still more work---then screening tools have limited value because the best forecast is just popularity. If, instead, the nearby structure of a field carries information beyond popularity, then a graph-based screen can surface questions that popularity alone would miss. The answer turns out to be layered: graph structure already improves on pure popularity in the main benchmark, and its advantage becomes larger once the decision problem looks more like actual research browsing and reranking rather than a single transparent heuristic. The contribution is practical rather than universal. It evaluates a screening rule under realistic attention constraints. It is not a full theory of scientific discovery and not a substitute for field knowledge or causal judgment.
@@ -95 +95,5 @@ This paper sits at the intersection of four literatures.
-First, it belongs to the economics of ideas and discovery. Bloom et al.~\citeyearpar{bloom2020ideas} document rising research effort alongside falling research productivity across several domains, while Jones~\citeyearpar{jones2009burden} studies how accumulating knowledge changes the organization of innovative activity. Those papers focus on the production of ideas and the cost of reaching the frontier. The present paper shifts attention to a narrower but operationally central problem: given a large existing literature, how should one screen candidate next questions?
+First, it belongs to the economics of ideas, discovery, and research direction. Bloom et al.~\citeyearpar{bloom2020ideas} document rising research effort alongside falling research productivity across several domains, while Jones~\citeyearpar{jones2009burden} studies how accumulating knowledge changes the organization of innovative activity.\footnote{The ``ideas are getting harder to find'' framing is itself debated. Fort~\citeyearpar{fort2025growth} argues that what is declining is the translation of ideas into measured growth, not the rate of idea generation itself.} Those papers focus on the production of ideas and the cost of reaching the frontier. A related body of work asks whether incentive structures systematically steer researchers toward safe topics. Azoulay, Graff Zivin, and Manso~\citeyearpar{azoulay2011incentives} compare exploration-tolerant and exploitation-rewarding funding regimes and show that tolerating early failure produces more novel and more high-impact work. Foster, Rzhetsky, and Evans~\citeyearpar{foster2015tradition} confirm empirically that conservative strategies dominate in practice, even though riskier exploration disproportionately generates breakthroughs.\footnote{Packalen and Bhattacharya~\citeyearpar{packalen2020stagnation} argue that citation-based incentives have further shifted scientists away from new ideas toward established topics, creating a self-reinforcing momentum that a screening tool could partially offset.} The present paper shifts attention to a narrower but operationally central problem: given a large existing literature, can the structure of past research help screen candidate next questions in a way that is less path-dependent than pure cumulative advantage?
+
+Second, the paper draws on the science-of-science literature that uses large-scale scientific data to study novelty, impact, and frontier formation. Fortunato et al.~\citeyearpar{fortunato2018science} provide a broad synthesis. Wang and Barabasi~\citeyearpar{wang2021science} show how scientific frontiers can be studied quantitatively, while Uzzi et al.~\citeyearpar{uzzi2013atypical} show how novelty often combines conventional structure with a limited number of atypical combinations. More recent work raises the stakes further. Park, Leahey, and Funk~\citeyearpar{park2023disruptive} document a broad decline in disruptive science since the mid-twentieth century, and Wang, Veugelers, and Stephan~\citeyearpar{wang2017novelty} show that genuinely novel papers face a short-run citation penalty even though they are far more likely to become top-cited in the long run.\footnote{The disruption-decline finding is itself debated. Petersen, Arroyave, and Pammolli~\citeyearpar{petersen2024disruption} argue that part of the measured decline reflects citation inflation rather than a real shift in innovativeness. For this paper, the relevant implication is narrower: whether or not measured disruption is declining, the literature's structure visibly thickens around existing claims over time, and that thickening is exactly what the path-development results in Section~\ref{sec:path-evolution} measure.} That literature is highly relevant in spirit, but my object differs. I do not measure novelty from citations or reference-pair combinations. I define candidate questions as missing links in a claim graph and evaluate them prospectively.
+
+Third, the benchmark logic comes from network growth and cumulative advantage. Price~\citeyearpar{price1976general} and Barabasi and Albert~\citeyearpar{barabasi1999emergence} show why already connected nodes tend to attract more links. For this project, that is not a decorative comparison. It is the main null. If the future of the literature is mostly a popularity process, then a rich-get-richer rule should perform well when the target is future edge appearance. Preferential attachment is therefore not a straw man. It is a serious benchmark because it encodes one plausible model of how scientific attention moves. The broader link-prediction literature in network science \citep{liben2007link,martinez2016survey} and the learning-to-rank tradition in information retrieval \citep{liu2009learning} show that learned models built on topological features can substantially outperform fixed heuristics. More directly, a growing body of work treats missing links in scientific knowledge graphs as candidate research directions. Krenn and Zeilinger~\citeyearpar{krenn2020predicting} use a semantic network from 750{,}000 quantum physics papers with a five-year temporal holdout to predict future concept associations. Gu and Krenn~\citeyearpar{gu2025impact4cast} extend this to 2.4 million papers across the sciences, predicting not only link appearance but citation impact, using 141 engineered features and a neural network. Sourati et al.~\citeyearpar{sourati2023accelerating} show that incorporating the distribution of researcher expertise into the knowledge network improves discovery prediction by up to 400 percent, especially in sparse literatures. Rzhetsky et al.~\citeyearpar{rzhetsky2015choosing} provide theoretical grounding by simulating how more exploratory research strategies would accelerate collective discovery. The learned reranker used in this paper sits in that tradition, but it differs in three ways: the features are all derived from a substantively interpreted economics claim graph with directed causal edges, the benchmark is framed around scarce reading budgets with preferential attachment as the named economic null, and the walk-forward vintage discipline mirrors the real ex ante screening problem that an economist would face.
@@ -97 +101 @@ First, it belongs to the economics of ideas and discovery. Bloom et al.~\citeyea
-Second, the paper draws on the science-of-science literature that uses large-scale scientific data to study novelty, impact, and frontier formation. Fortunato et al.~\citeyearpar{fortunato2018science} provide a broad synthesis. Wang and Barabasi~\citeyearpar{wang2021science} show how scientific frontiers can be studied quantitatively, while Uzzi et al.~\citeyearpar{uzzi2013atypical} show how novelty often combines conventional structure with a limited number of atypical combinations. That literature is highly relevant in spirit, but my object differs. I do not measure novelty from citations or reference-pair combinations. I define candidate questions as missing links in a claim graph and evaluate them prospectively.
+Fourth, the paper enters a fast-moving discussion around AI-assisted scientific work. Recent systems already help with tasks such as hypothesis generation, literature synthesis, manuscript feedback, and reviewer assistance \citep{zhang2025scientificmethod,shao2025sciscigpt,korinek2024generative,refine2026,iclr2026reviewer,stanfordagentic2026,projectape2026}. Si, Yang, and Hashimoto~\citeyearpar{si2024llmideas} find in a large-scale evaluation that LLM-generated research ideas are rated more novel, though slightly less feasible, than expert-generated ones. Agrawal, McHale, and Oettl~\citeyearpar{agrawal2024ai} formalize AI-assisted discovery as prioritized search over a combinatorial hypothesis space.\footnote{A related concern is that data-driven tools may narrow exploration rather than broaden it. Hoelzemann et al.~\citeyearpar{hoelzemann2024streetlight} show that when data highlights attractive but suboptimal paths, it can suppress breakthrough discovery---a ``streetlight effect'' that a screening tool must be honest about. The attention-frontier and heterogeneity results in Section~5 speak to this directly.} My contribution is not a new general-purpose AI assistant and not a new claim-extraction model. The paper uses AI-extracted paper-level structure as an enabling layer, then asks an economics question: can we convert that structure into an inspectable, prospectively testable research-allocation object?
@@ -99 +103 @@ Second, the paper draws on the science-of-science literature that uses large-sca
-Third, the benchmark logic comes from network growth and cumulative advantage. Price~\citeyearpar{price1976general} and Barabasi and Albert~\citeyearpar{barabasi1999emergence} show why already connected nodes tend to attract more links. For this project, that is not a decorative comparison. It is the main null. If the future of the literature is mostly a popularity process, then a rich-get-richer rule should perform well when the target is future edge appearance. Preferential attachment is therefore not a straw man. It is a serious benchmark because it encodes one plausible model of how scientific attention moves.
+That positioning also helps distinguish this project from generic link prediction. Generic link-prediction work often asks whether a missing edge will appear in a network. The closest social-science comparisons are Tong et al.~\citeyearpar{tong2024automating}, who extract causal relations from psychology papers and use knowledge-graph link prediction to generate hypotheses, and Lee et al.~\citeyearpar{lee2024econcausal}, who construct context-annotated causal triplets from economics papers to benchmark LLM causal reasoning. The present paper differs in scale (242{,}595 papers versus 43{,}312), in evaluation design (prospective walk-forward backtesting versus expert judgment), and in the separation between the benchmarkable anchor and the surfaced question. Here the edges are substantively interpreted claim-like relations in economics, the benchmark is explicitly framed around scarce reading budgets, the principal comparison is with cumulative advantage, and the public output is designed to be inspectable question by question. The paper is therefore best understood as economics-first metascience with a graph-based empirical object, rather than as a pure machine-learning exercise.
@@ -101 +105 @@ Third, the benchmark logic comes from network growth and cumulative advantage. P
-Fourth, the paper enters a fast-moving discussion around AI-assisted scientific work. Recent systems already help with tasks such as hypothesis generation, literature synthesis, manuscript feedback, and reviewer assistance \citep{zhang2025scientificmethod,shao2025sciscigpt,refine2026,iclr2026reviewer,stanfordagentic2026,projectape2026}. My contribution is not a new general-purpose AI assistant and not a new claim-extraction model. The paper uses AI-extracted paper-level structure as an enabling layer, then asks an economics question: can we convert that structure into an inspectable, prospectively testable research-allocation object?
+Taken together, these four literatures frame the paper's central question. If the frontier is harder to navigate, if incentives bias researchers toward the familiar, if disruption is declining, and if AI is lowering the cost of downstream research tasks, then the upstream choice of what to work on becomes more important and more amenable to structured screening. The paper tests whether a graph-based screen can add value beyond cumulative advantage in that specific decision problem. Table~\ref{tab:positioning} summarizes how this paper differs from the closest comparable systems.
@@ -103 +107,19 @@ Fourth, the paper enters a fast-moving discussion around AI-assisted scientific
-That positioning also helps distinguish this project from generic link prediction. Generic link-prediction work often asks whether a missing edge will appear in a network. Here the edges are substantively interpreted claim-like relations in economics, the benchmark is explicitly framed around scarce reading budgets, the principal comparison is with cumulative advantage, and the public output is designed to be inspectable question by question. The paper is therefore best understood as economics-first metascience with a graph-based empirical object, rather than as a pure machine-learning exercise.
+\begin{table}[t]
+  \caption{Positioning relative to closest comparable work}
+  \label{tab:positioning}
+  \centering
+  \small
+  \begin{tabular}{L{0.18\linewidth}L{0.18\linewidth}L{0.18\linewidth}L{0.18\linewidth}L{0.18\linewidth}}
+    \toprule
+    & This paper & Impact4Cast & Sourati et al. & Tong et al. \\
+    \midrule
+    Domain & Economics & All sciences & Biomedicine & Psychology \\
+    Edge type & Directed causal & Co-occurrence & Co-occurrence & Causal \\
+    Corpus & 242{,}595 papers & 2.4M papers & Varies & 43{,}312 papers \\
+    Main null & Pref.\ attach.\ & ML baselines & Content-only & TransE \\
+    Temporal eval & Walk-forward & Holdout & Holdout & None \\
+    Human eval & Prepared & No & No & Yes \\
+    \bottomrule
+  \end{tabular}
+  \fignotes{Impact4Cast: Gu and Krenn~\citeyearpar{gu2025impact4cast}. Sourati et al.: Sourati et al.~\citeyearpar{sourati2023accelerating}. Tong et al.: Tong et al.~\citeyearpar{tong2024automating}. This paper is the only comparison case with directed causal edges, preferential attachment as the named economic null, and walk-forward evaluation in economics.}
+\end{table}
@@ -107 +129,73 @@ That positioning also helps distinguish this project from generic link predictio
-The paper starts from a published-journal corpus rather than a broad scrape of all economics-adjacent writing. The selected journal corpus contains 242{,}595 papers drawn from the top 150 core economics journals and the top 150 adjacent journals under the field-weighted citation impact selection rule. The sample spans 1976 to early 2026. Of those papers, 230{,}929 contain at least one extracted edge, yielding 1{,}443{,}407 raw extracted edges. After normalization and graph construction, the evaluation graph retains 230{,}479 papers, 6{,}752 concept codes, and 1{,}271{,}014 normalized links.
+Figure~\ref{fig:pipeline-overview} summarizes the full pipeline. The paper starts from a published-journal corpus, extracts paper-local claim graphs using a language model, normalizes concept labels into a reusable ontology-backed graph, and then ranks missing directed links as candidate questions for prospective evaluation. The selected journal corpus contains 242{,}595 papers drawn from the top 150 core economics journals and the top 150 adjacent journals under the field-weighted citation impact selection rule. The sample spans 1976 to early 2026. Of those papers, 230{,}929 contain at least one extracted edge, yielding 1{,}443{,}407 raw extracted edges. After normalization and graph construction, the current benchmark snapshot retains 230{,}479 papers and 1{,}271{,}014 normalized links. The ontology inventory itself is frozen separately at 154{,}359 rows in the v2.3 baseline described in Section~3.3 and Appendix~\ref{app:node-normalization}.
+
+\begin{figure}[t]
+  \caption{Full pipeline: from published papers to prospective screening benchmark}
+  \label{fig:pipeline-overview}
+  \centering
+  \begin{tikzpicture}[
+    x=1cm, y=1cm,
+    stage/.style={draw=#1!40, rounded corners=5pt, fill=#1!6, minimum width=3.6cm, minimum height=5.8cm, inner sep=6pt},
+    stagehead/.style={font=\small\bfseries, fill=#1!20, rounded corners=3pt, inner sep=4pt, minimum width=3.2cm, align=center},
+    node/.style={draw=black!25, circle, fill=white, minimum size=0.7cm, inner sep=1pt, font=\tiny, align=center},
+    edge/.style={-{Latex[length=1.5mm]}, draw=blue!60!black, line width=0.7pt},
+    ctxedge/.style={draw=black!20, line width=0.5pt},
+    miss/.style={-{Latex[length=1.5mm]}, draw=red!70!black, dashed, line width=0.9pt},
+    flow/.style={-{Latex[length=3mm]}, draw=black!50, line width=1.5pt},
+    annot/.style={font=\tiny\itshape, text=black!60},
+    doc/.style={draw=black!20, fill=white, minimum width=0.55cm, minimum height=0.7cm, inner sep=0pt},
+  ]
+    \node[stage=blue] (s1) at (0,0) {};
+    \node[stage=green] (s2) at (4.6,0) {};
+    \node[stage=orange] (s3) at (9.2,0) {};
+    \node[stage=purple] (s4) at (13.8,0) {};
+    \node[stagehead=blue] at (0,3.2) {1. Corpus};
+    \node[stagehead=green] at (4.6,3.2) {2. Extract};
+    \node[stagehead=orange] at (9.2,3.2) {3. Graph};
+    \node[stagehead=purple] at (13.8,3.2) {4. Screen};
+    \foreach \y in {1.8,1.3,0.8} { \node[doc] at (-0.3,\y) {}; }
+    \foreach \y in {1.7,1.2,0.7} { \node[doc] at (0.0,\y) {}; }
+    \foreach \y in {1.6,1.1,0.6} { \node[doc] at (0.3,\y) {}; }
+    \node[annot] at (0,0.0) {242{,}595 papers};
+    \node[annot] at (0,-0.5) {1976--2026};
+    \node[annot] at (0,-1.0) {Core + adjacent};
+    \node[annot] at (0,-1.5) {economics journals};
+    \node[annot] at (4.6,2.4) {LLM reads each};
+    \node[annot] at (4.6,2.0) {title + abstract};
+    \node[node] (e1) at (3.8,1.0) {Public\\debt};
+    \node[node] (e2) at (5.4,1.0) {Public\\invest.};
+    \draw[edge] (e1) -- (e2);
+    \node[node] (e3) at (3.8,-0.3) {CO$_2$};
+    \node[node] (e4) at (5.4,-0.3) {Energy\\demand};
+    \draw[ctxedge] (e3) -- (e4);
+    \node[annot, text=blue!60!black] at (4.6,0.35) {\(\rightarrow\) directed causal};
+    \node[annot, text=black!40] at (4.6,-0.95) {--- undirected context};
+    \node[annot] at (4.6,-1.6) {1{,}271{,}014 edges};
+    \node[node, fill=orange!8] (g1) at (8.2,1.5) {Public\\debt};
+    \node[node, fill=orange!8] (g2) at (9.2,2.1) {Public\\invest.};
+    \node[node, fill=orange!8] (g3) at (10.2,1.5) {CO$_2$};
+    \node[node, fill=orange!8] (g4) at (9.2,0.5) {Financial\\devel.};
+    \draw[edge] (g1) -- (g2);
+    \draw[edge] (g2) -- (g3);
+    \draw[edge] (g1) -- (g4);
+    \draw[edge] (g4) -- (g3);
+    \draw[miss] (g1) -- (g3);
+    \node[annot] at (9.2,-0.3) {Ontology-backed graph};
+    \node[annot] at (9.2,-0.9) {\textcolor{red!70!black}{Missing links}};
+    \node[annot] at (9.2,-1.4) {\textcolor{red!70!black}{= candidates}};
+    \node[annot] at (13.8,2.4) {Freeze at $t{-}1$};
+    \node[annot] at (13.8,1.9) {Rank candidates};
+    \node[annot] at (13.8,1.2) {Transparent score};
+    \node[annot] at (13.8,0.7) {+ Learned reranker};
+    \draw[black!30, rounded corners=2pt] (13.0,-0.2) rectangle (14.6,-1.6);
+    \node[font=\tiny, anchor=west] at (13.1,-0.45) {1. Debt $\rightarrow$ CO$_2$};
+    \node[font=\tiny, anchor=west] at (13.1,-0.75) {2. Trade $\rightarrow$ Energy};
+    \node[font=\tiny, anchor=west] at (13.1,-1.05) {3. Finance $\rightarrow$ Innov.};
+    \node[font=\tiny, anchor=west, text=black!40] at (13.1,-1.35) {\ldots};
+    \node[annot] at (13.8,-2.0) {Did link appear};
+    \node[annot] at (13.8,-2.5) {in $[t, t{+}h]$?};
+    \draw[flow] (1.9,0) -- (2.7,0);
+    \draw[flow] (6.5,0) -- (7.3,0);
+    \draw[flow] (11.1,0) -- (11.9,0);
+  \end{tikzpicture}
+  \fignotes{Four stages: corpus definition, LLM extraction, concept normalization, and prospective screening. The worked example---public debt, public investment, and CO\(_2\) emissions---runs through all four. Scale annotations report data volume at each stage.}
+\end{figure}
@@ -164 +258 @@ The journal universe is deliberately narrow in two senses. First, it uses a sele
-  \fignotes{This figure shows the core measurement pipeline as a worked example. The unit of observation at extraction is the individual paper title and abstract. Each paper first produces a paper-local graph, repeated concept labels are then matched into shared concept identities across papers, and the resulting concept-level structure can surface a missing direct relation as a candidate question. Directed causal relations are stored for the design-based causal task, while noncausal contextual support remains in the same concept graph as undirected structure.}
+  \fignotes{Each paper produces a paper-local graph. Repeated concept labels are later matched into shared concept identities, which lets the graph surface missing direct relations as candidate questions. Directed causal relations (arrows) are stored separately from undirected contextual support (gray lines).}
@@ -169 +263 @@ The journal universe is deliberately narrow in two senses. First, it uses a sele
-The extraction layer builds on Garg and Fetzer~\citeyearpar{gargfetzer2025causal}. Each title and abstract is converted into a paper-local graph in which nodes correspond to extracted concepts and edges summarize the relations the paper itself states, studies, or reports. The present paper inherits that idea but extends it in three ways that matter downstream. First, the schema is broader than explicit causal claims, because the benchmark also needs undirected contextual support. Second, the schema separates the paper's \emph{causal presentation} from the \emph{evidence method} used to support a claim. Third, the local graph stores contextual qualifiers in dedicated fields rather than forcing them into the node label. The goal is not simply to recover whether a paper makes a claim; it is to recover enough structured local information that the claim can later live inside a reusable concept graph. Code, prompt files, and release materials are available in the public repository at \url{https://github.com/prashgarg/frontiergraph}.
+The extraction layer builds on Garg and Fetzer~\citeyearpar{gargfetzer2025causal}. Each title and abstract is converted into a paper-local graph in which nodes correspond to extracted concepts and edges summarize the relations the paper itself states, studies, or reports (Figure~\ref{fig:extraction-flow}). The present paper inherits that idea but extends it in three ways that matter downstream. First, the schema is broader than explicit causal claims, because the benchmark also needs undirected contextual support.\footnote{This is a deliberate departure from Garg and Fetzer~\citeyearpar{gargfetzer2025causal}. Their object is the rise of credible causal language and design in economics, so the stricter identified-causal layer is the natural headline object there. Here the downstream task is broader research-allocation over candidate questions, so the main target is a wider causal-claim layer, while the stricter identified-causal layer is retained as a nested credibility-oriented benchmark.} Second, the schema separates the paper's \emph{causal presentation} from the \emph{evidence method} used to support a claim. Third, the local graph stores contextual qualifiers in dedicated fields rather than forcing them into the node label. The goal is not simply to recover whether a paper makes a claim; it is to recover enough structured local information that the claim can later live inside a reusable concept graph. Code, prompt files, and release materials are available in the public repository at \url{https://github.com/prashgarg/frontiergraph}.
@@ -177 +271 @@ The normalization problem is central in this paper because candidate generation,
-For that reason the paper builds a native concept ontology. The aim is to preserve concept identity at the level at which candidate questions are actually formed. The pipeline first resolves easy cases with deterministic lexical signatures, then uses a text-embedding matching step to rank plausible concept matches for harder cases, and finally stores mapping provenance and quality bands so weaker tail recoveries remain auditable.\footnote{The embedding step is used as a retrieval and ranking device after exact and signature-based passes, not as an unconstrained merge rule. That ordering keeps obvious cases deterministic and makes softer matches inspectable.} The ontology build creates native concept codes, clusters a selected head pool into accepted concepts, applies hard and soft mappings for the tail, and then uses a force-mapped recovery layer so the fuller corpus remains in the graph rather than being dropped for lack of a clean early match. Appendix~\ref{app:node-normalization} gives the full algorithmic detail.
+For that reason the paper now uses a structured frozen ontology baseline (v2.3) rather than a native head-pool build. The ontology combines five source families that contribute different kinds of coverage: JEL, an economics-filtered Wikidata pull, OpenAlex topics, OpenAlex keywords, and an economics-filtered Wikipedia crawl, together with a small reviewed family layer carried forward from the earlier enrichment passes. The frozen baseline contains 154{,}359 rows. Raw source provenance remains immutable throughout. The ontology stores the raw source label and, when needed, a paper-facing \texttt{display\_label} cleanup, and it records reviewed \texttt{effective\_parent\_*} and \texttt{effective\_root\_*} fields as hierarchy overlays rather than treating source-native parent labels as final truth. Mapping then proceeds in stages. Easy cases are resolved deterministically with exact label and surface-form matches. Harder cases use embedding retrieval against the ontology and store the rank-1, rank-2, and rank-3 candidates rather than collapsing everything into one irreversible merge.\footnote{The embedding step is used as a retrieval and ranking device after exact lexical passes, not as an unconstrained merge rule. That ordering keeps obvious cases deterministic and makes softer matches auditable.} Grounding is tiered rather than binary: a primary threshold defines linked and soft matches, lower-confidence candidate and rescue bands remain visible, broader ontology grounding is allowed when the ontology only has a more general concept, and unresolved labels are retained rather than dropped. At the primary 0.75 threshold, 316{,}292 labels and 553{,}015 label occurrences attach directly. The broader reviewed grounding layer is then kept as a separate auditable interpretive layer rather than being used to rewrite source truth. Appendix~\ref{app:node-normalization} gives the full algorithmic detail. Table~\ref{tab:notation} fixes the key notation used throughout the paper.
@@ -197 +291,9 @@ For that reason the paper builds a native concept ontology. The aim is to preser
-\section{Candidate Questions and Evaluation Design}
+\begin{figure}[t]
+  \caption{A real neighborhood in the economics claim graph}
+  \label{fig:real-neighborhood}
+  \centering
+  \includegraphics[width=0.92\linewidth]{real_neighborhood.png}
+  \fignotes{This shows an actual fragment of the economics claim graph around a core concept, with directed causal edges (blue arrows) and undirected contextual edges (gray lines). Node positions are from a spring layout of the local subgraph. This is the concrete object behind the stylized TikZ schematics: each node is a normalized concept from the ontology, each arrow is a directed causal relation extracted from a published paper, and each gray line is undirected contextual support. The density of edges and the mix of causal and contextual structure vary by neighborhood.}
+\end{figure}
+
+\section{Direct-Edge Retrieval Anchors, Surfaced Questions, and Evaluation Design}
@@ -199 +301 @@ For that reason the paper builds a native concept ontology. The aim is to preser
-This section explains how the paper turns possible next questions into ranked suggestions and then tests them against the later literature. At year \(t-1\), I start from the literature map assembled from papers observed through that date. A candidate question is represented as a connection that has not yet appeared in that map. Formally, let \(G_{t-1}=(V,E_{t-1})\) denote the claim graph assembled through that date. For a directed causal candidate, \(u \rightarrow v\) is eligible when that ordered directed link has not yet appeared in the historical graph. For an undirected noncausal candidate, \(\{u,v\}\) is eligible when the pair has not yet appeared as undirected support. The headline object in this paper is the directed causal candidate.
+The graph is now a reusable concept-level object with dated edges, directed causal links, and undirected contextual support. Figure~\ref{fig:real-neighborhood} shows what a real neighborhood looks like. The next question is what to do with it. This section distinguishes the two objects that the paper keeps separate throughout. The historical backtest needs a narrow, dated, benchmarkable event. The reader, by contrast, needs a research object that is natural to inspect. I therefore use missing directed links as benchmark anchors (Section~\ref{sec:missing-links}) and path-rich or mechanism-rich questions as surfaced objects. The headline benchmark remains the directed causal anchor.
@@ -201 +303,2 @@ This section explains how the paper turns possible next questions into ranked su
-\subsection{Missing links as candidate questions}
+\subsection{Missing links as benchmark anchors}
+\label{sec:missing-links}
@@ -203 +306 @@ This section explains how the paper turns possible next questions into ranked su
-One way to read the novelty and frontier literatures is that many scientific advances come from combinations or connections that were not yet explicit in the recorded structure of a field \citep{uzzi2013atypical,fortunato2018science,wang2021science}. The representation used here takes that intuition in a narrow form. The point is not that every paper can be reduced to one edge. The point is that many research moves can be approximated as the appearance of a relation that was already plausible in the nearby literature before it became explicit. That lets us define a prospectively testable object. The approach is closer to frontier tracing than to open-ended ideation: it asks which direct relations the existing local graph seems to invite next.
+One way to read the novelty and frontier literatures is that many scientific advances come from combinations or connections that were not yet explicit in the recorded structure of a field \citep{uzzi2013atypical,fortunato2018science,wang2021science}. The representation used here takes that intuition in a narrow form. The point is not that every paper can be reduced to one edge. The point is that many research moves can be approximated as the appearance of a relation that was already plausible in the nearby literature before it became explicit. That gives the paper a prospectively testable object, but it does not force the surfaced question to remain equally narrow.
@@ -214,0 +318,19 @@ where \(E^{U}_{t-1}\) denotes the undirected contextual support subgraph. A futu
+The narrow anchor matters because it keeps the benchmark symmetric and dated. The richer surfaced question matters because economists do not browse bare missing links. They browse questions that might plausibly become papers (Table~\ref{tab:anchor-readings}).
+
+The reason the surfaced object remains endpoint-centered is practical rather than reductive. A local graph neighborhood may contain several paths, several candidate mediators, and several partially overlapping motif readings. But a historical benchmark needs one dated event, and a reader needs one inspectable research question. Endpoint or endpoint-plus-mediator formulations are usually the least lossy compression that satisfies both requirements. They preserve a focal relation that can be benchmarked symmetrically over time while still allowing the surrounding path, mediator, and branching structure to enter as supporting evidence rather than disappearing. The paper therefore treats richer motifs as evidence carried by a candidate, not as the benchmark object itself.
+
+This benchmark also holds the active concept set fixed at the cutoff. A distinct extension, which I do not mix into the main backtest here, is \emph{node activation}: dormant ontology concepts, weakly grounded phrases, or genuinely new concepts later entering the active graph. That object is substantively important, but it requires a different dated event than missing-link appearance and is therefore better treated as a separate frontier problem.
+
+\begin{table}[t]
+  \caption{The benchmark anchor is narrower than the surfaced question}
+  \label{tab:anchor-readings}
+  \centering
+  \begin{tabular}{L{0.27\linewidth}L{0.31\linewidth}L{0.31\linewidth}}
+    \toprule
+    Direct-edge benchmark anchor & Path-rich reading & Mechanism-rich reading \\
+    \midrule
+    Price changes \(\rightarrow\) CO\(_2\) emissions & What nearby pathways could connect price changes to CO\(_2\) emissions? & Which mechanisms most plausibly connect price changes to CO\(_2\) emissions? \\
+    \bottomrule
+  \end{tabular}
+\end{table}
+
@@ -352 +474 @@ The ranking rule combines four ingredients: path support, underexploration gap,
-In the implementation used for this paper, the score takes the form
+Formally, the score for a candidate pair \((u,v)\) is a weighted sum of four components:
@@ -359,0 +482,11 @@ That transparency choice matters for interpretation. The graph already stores st
+\subsection{The learned reranker}
+\label{sec:reranker-design}
+
+The transparent score is deliberately fixed-weight and inspectable. Its weights are chosen by design judgment rather than tuned to historical outcomes, which keeps the score readable question by question. But that inspectability comes at a cost: fixed weights may underweight features that are empirically important for screening. The stronger transparent baselines introduced above---degree plus recency and directed closure---confirm that fixed weights alone are not enough to beat cumulative advantage at the strict shortlist margin. The natural response to that specific diagnosis is not to abandon the graph-based framing but to ask whether a model that \emph{learns} how to combine the same graph features can recover the benchmark. That is what the learned reranker does. It operates on the same missing-link candidates, uses only information available at the historical cutoff, and adds no text features, no future data, and no author or institutional identity.
+
+The reranker draws on five nested feature families, each extending the previous. The first is the transparent graph score itself. The second adds structural features: path support, motif counts, mediator counts, co-occurrence signals, endpoint degree products, and a same-field indicator. The third adds temporal features: support age, recency of the most recent supporting edge, and recent-window degree and incident counts for each endpoint. The fourth adds evidence-composition features: mean edge stability, evidence-type diversity, venue diversity, source diversity, and mean field-weighted citation impact at each endpoint. The fifth adds boundary and gap flags: whether the two endpoints sit in different field groups with no co-occurrence, whether the pair looks gap-like in the sense of having path support despite a missing direct link, and the local closure density around the pair. In total, the richest family uses 34 graph-derived features. Table~\ref{tab:feature-families} in Appendix~\ref{app:reranker-design} lists the full inventory.
+
+Training follows a walk-forward temporal discipline. At each evaluation cutoff \(t\), the model is trained only on cutoff-year cells strictly before \(t\), and evaluated at \(t\). Features are computed from the historical corpus through year \(t-1\). The positive label is whether the candidate edge first appears within the evaluation horizon. Two model families are tested: an interpretable logistic regression with class-balanced weights, and a pairwise ranking model that learns from positive-versus-negative feature differences. Both use \(L_2\) regularization. The feature families are nested, so the complexity gradient is itself interpretable: the paper can ask whether topology alone is enough, or whether recency, evidence composition, or boundary structure adds screening value. Appendix~\ref{app:reranker-design} gives the full training design, regularization grid, best configurations by horizon, and a grouped feature decomposition showing which feature families drive the combined model's predictions.
+
+The reranker stays inside the graph-screening framing: every feature comes from the literature graph (no text, no author identity, no external data), the candidate universe is the same set of missing links, and the temporal discipline is the same walk-forward vintage design.\footnote{The difference is only in how the graph features are combined: by fixed design judgment in the transparent score, or by weights learned from earlier cutoffs in the reranker.}
+
@@ -364 +497,63 @@ The prospective design freezes the graph at year \(t-1\), ranks candidates using
-For each cutoff year, the graph is built from the historical stock only. Realizations are then defined from future papers over the chosen horizon. The benchmark is rolling rather than one-shot, so each horizon is evaluated across multiple cutoff dates. A cutoff is eligible for horizon \(h\) only if \(t+h\leq 2026\), and the heterogeneity atlas applies the same rule on a five-year cutoff grid when it extends the exercise to \(h=20\). The headline benchmark focuses on directed causal candidates, but the fuller atlas also evaluates directed and undirected objects separately and then pools them by weighted aggregation rather than by constructing one mixed ranking universe.
+For each cutoff year, the graph is built from the historical stock only. Realizations are then defined from future papers over the chosen horizon. The benchmark is rolling rather than one-shot, so each horizon is evaluated across multiple cutoff dates. A cutoff is eligible for horizon \(h\) only if \(t+h\leq 2026\), and the appendix horizon extension applies the same rule on a five-year cutoff grid when it extends the transparent benchmark to \(h=20\). The headline benchmark focuses on directed causal candidates, but the fuller atlas also evaluates directed and undirected objects separately and then pools them by weighted aggregation rather than by constructing one mixed ranking universe. Figure~\ref{fig:evaluation-design} makes the temporal discipline visual.
+
+\begin{figure}[t]
+  \caption{Walk-forward evaluation design: the vintage discipline}
+  \label{fig:evaluation-design}
+  \centering
+  \begin{tikzpicture}[
+    x=1cm, y=1cm,
+    yearbox/.style={draw=black!30, rounded corners=2pt, minimum width=1.0cm, minimum height=0.6cm, font=\scriptsize, align=center},
+    trainbox/.style={yearbox, fill=blue!12},
+    evalbox/.style={yearbox, fill=red!12},
+    horizonbox/.style={yearbox, fill=green!10},
+    brace/.style={decorate, decoration={brace, amplitude=5pt, mirror}},
+    annot/.style={font=\scriptsize, text=black!70},
+  ]
+    \draw[-{Latex[length=2mm]}, thick, black!40] (-0.5,-0.3) -- (16,-0.3);
+    \foreach \x/\yr in {0/1990, 2/1995, 4/2000, 6/2005, 8/2010, 10/2015, 12/2020, 14/2025} {
+      \draw[black!40] (\x,-0.15) -- (\x,-0.45);
+      \node[font=\tiny, text=black!50] at (\x,-0.7) {\yr};
+    }
+    \node[annot, anchor=east] at (-1,1.5) {Cutoff 2005, $h{=}5$:};
+    \foreach \x in {0,2,4} { \node[trainbox] at (\x,1.5) {}; }
+    \node[evalbox] at (6,1.5) {};
+    \draw[green!50!black, very thick, -{Latex[length=2mm]}] (6.6,1.5) -- (8.4,1.5);
+    \node[horizonbox] at (8,1.5) {};
+    \draw[brace, blue!50] (-0.5,0.9) -- (4.5,0.9);
+    \node[font=\tiny, text=blue!60!black] at (2,0.55) {Train: graph through 2004};
+    \node[font=\tiny, text=red!60!black] at (6,0.95) {Score};
+    \node[font=\tiny, text=green!50!black] at (8.8,1.5) {Realize?};
+    \node[annot, anchor=east] at (-1,3.2) {Cutoff 2010, $h{=}10$:};
+    \foreach \x in {0,2,4,6} { \node[trainbox] at (\x,3.2) {}; }
+    \node[evalbox] at (8,3.2) {};
+    \draw[green!50!black, very thick, -{Latex[length=2mm]}] (8.6,3.2) -- (12.4,3.2);
+    \node[horizonbox] at (12,3.2) {};
+    \draw[brace, blue!50] (-0.5,2.6) -- (6.5,2.6);
+    \node[font=\tiny, text=blue!60!black] at (3,2.25) {Train: graph through 2009};
+    \node[font=\tiny, text=red!60!black] at (8,2.65) {Score};
+    \node[font=\tiny, text=green!50!black] at (12.8,3.2) {Realize?};
+    \node[annot, anchor=east] at (-1,4.9) {Held-out test:};
+    \foreach \x in {0,2,4} { \node[trainbox] at (\x,4.9) {}; }
+    \draw[black!30, thick, dashed] (5.3,4.3) -- (5.3,5.5);
+    \node[evalbox, fill=red!25] at (8,4.9) {};
+    \node[evalbox, fill=red!25] at (10,4.9) {};
+    \draw[green!50!black, very thick, -{Latex[length=2mm]}] (10.6,4.9) -- (14.4,4.9);
+    \node[horizonbox] at (14,4.9) {};
+    \draw[brace, blue!50] (-0.5,4.3) -- (4.5,4.3);
+    \node[font=\tiny, text=blue!60!black] at (2,3.95) {Train: 1990--2005 only};
+    \node[font=\tiny, text=black!50] at (5.3,5.7) {\textit{cutoff}};
+    \node[font=\tiny, text=red!60!black] at (9,4.35) {Never seen during training};
+    \node[font=\tiny, text=green!50!black] at (14.8,4.9) {Realize?};
+    \node[trainbox, minimum width=0.6cm, minimum height=0.4cm] at (0.3,6.3) {};
+    \node[font=\tiny, anchor=west] at (0.7,6.3) {Training data};
+    \node[evalbox, minimum width=0.6cm, minimum height=0.4cm] at (3.3,6.3) {};
+    \node[font=\tiny, anchor=west] at (3.7,6.3) {Scoring cutoff};
+    \node[horizonbox, minimum width=0.6cm, minimum height=0.4cm] at (6.3,6.3) {};
+    \node[font=\tiny, anchor=west] at (6.7,6.3) {Realization window};
+  \end{tikzpicture}
+  \fignotes{At each cutoff, the graph uses only papers published before that date (blue). Candidates are scored at the cutoff (red), and realizations are checked over the horizon window (green). The bottom row shows the held-out era test from Appendix~\ref{app:temporal-generalization}: train on 1990--2005 and evaluate on the unseen 2010--2015 era.}
+\end{figure}
+
+\begin{tcolorbox}[colback=gray!3,colframe=black!18,title=How to read the benchmark]
+The benchmark is evaluated on direct-link benchmark anchors because later link appearance is the clean event that can be dated. The most intuitive metric is \emph{future links per 100 suggested anchors}: among 100 surfaced missing links, how many later appear as realized directed relations in the literature? Recall@100 asks what share of all future realized links are captured in a 100-anchor shortlist. Mean reciprocal rank rewards putting realized links nearer the top. When I discuss current suggestions, I translate anchors back into path-rich or mechanism-rich questions because that is the object a researcher would actually inspect.
+\end{tcolorbox}
@@ -370 +565 @@ For each cutoff year, the graph is built from the historical stock only. Realiza
-In plain language, it is a rich-get-richer rule: already central concepts attract more future links. This is the right benchmark because the literature is not generated by neutral exploration alone. Topics with existing visibility, existing datasets, recognizable methods, and established readership often attract still more work. If a graph-based score cannot outperform that baseline in the benchmark, that is a substantive result rather than a disappointment.
+In plain language, it is a rich-get-richer rule: already central concepts attract more future links. This is the right benchmark because the literature is not generated by neutral exploration alone. Topics with existing visibility, existing datasets, recognizable methods, and established readership often attract still more work. If a graph-based score cannot outperform that baseline in the benchmark, that is a substantive result rather than a disappointment. The paper widens the benchmark family with degree plus recency and directed closure as stronger transparent checks, then asks whether a learned reranker built on the same graph candidate universe can beat that harder set.
@@ -372 +567,3 @@ In plain language, it is a rich-get-richer rule: already central concepts attrac
-Preferential attachment is also the main benchmark because cumulative advantage is the main economic null in this setting. Standard graph baselines such as common-neighbors, Katz-style scores, or embedding methods are useful future appendix comparisons, but they are not the primary benchmark here because the paper is not asking a generic network-completion question.
+\paragraph{Co-occurrence as a benchmark.} Much of the recent work on predicting future research connections does not use directed or typed edges at all. Krenn and Zeilinger~\citeyearpar{krenn2020predicting} build a semantic network from 750{,}000 quantum physics papers in which an edge means two concepts co-appear in the same paper. Gu and Krenn~\citeyearpar{gu2025impact4cast} extend this to 2.4 million papers across the sciences, again using undirected co-occurrence. That approach has real advantages: it requires no extraction of causal direction or claim metadata, it scales easily to any corpus where concepts can be tagged, and it has proven effective for cross-science link prediction. The question for this paper is whether the harder extraction---directed causal edges, typed by method, stability, and argument role---adds screening value beyond what co-occurrence alone delivers. I therefore include a co-occurrence baseline that scores each candidate pair by how many papers mention both endpoints, ignoring edge direction, causal presentation, and all path structure.
+
+This gives the benchmark a simple layered structure. Preferential attachment is the cumulative-advantage null. Co-occurrence asks whether undirected co-mention is enough. The transparent graph score is the readable screening layer. The learned reranker is the strongest graph-based screen once those harder transparent baselines are in place.
@@ -376 +573 @@ Preferential attachment is also the main benchmark because cumulative advantage
-\paragraph{Horizon choice.} The main horizons are 3, 5, 10, and 15 years because they correspond to distinct practical windows. Three years is a short-run scouting horizon. Five years is a natural publication and diffusion window in economics. Ten years captures slower movement in topics that take longer to propagate through papers, methods, and field conventions. Fifteen years is still empirically useful in the fuller published-journal sample and is promoted into the main paper because many slower literatures are only partly visible at shorter horizons. Twenty years remains an appendix extension.
+\paragraph{Horizon choice.} The main horizons are 5, 10, and 15 years. Five years is a natural publication and diffusion window in economics. Ten years captures slower movement in topics that take longer to propagate through papers, methods, and field conventions. Fifteen years remains empirically useful because many slower literatures are only partly visible at shorter windows. Three years and twenty years are kept as appendix extensions, but the main benchmark comparison is now centered on 5, 10, and 15 years.
@@ -380 +577 @@ Preferential attachment is also the main benchmark because cumulative advantage
-I first ask whether the method beats a simple popularity-based rule at the very top of the ranking. It usually does not. I then ask whether the graph-based score becomes more useful once a researcher is willing to inspect a broader shortlist, weight later links by downstream reuse, and look at where in the literature local structure does more of the screening work.
+I begin with the strict top of the transparent ranking and compare it with a simple popularity-based rule. I then ask what changes once the same candidate universe is reranked with learned graph features, whether broader shortlists change the interpretation, and where in the literature local structure is most informative. I end by returning to the richer human-facing question objects that the system is meant to surface.
@@ -382,3 +579 @@ I first ask whether the method beats a simple popularity-based rule at the very
-\begin{tcolorbox}[colback=gray!3,colframe=black!18,title=How to read the benchmark]
-The most intuitive body metric is \emph{future links per 100 suggested questions}: among 100 surfaced questions, how many later appear as realized directed links in the literature. Recall@100 asks what share of all future realized links are captured in a 100-question shortlist. Mean reciprocal rank rewards putting those realized links nearer the top of the same shortlist.
-\end{tcolorbox}
+One point matters for all of the results that follow. The benchmark now runs from 1990 through 2015 rather than only on the denser post-2000 era. That does not overturn the ranking comparison, but it does change how the time dimension should be read. The 1990 and 1995 cells are not only thinner. They also surface different kinds of objects: support is younger, recent-share measures are higher, and diversity and stability are lower. So when the later-era results look cleaner, the right interpretation is not that the early years were merely noisy. It is that the early literature graph is a different regime. Appendix Table~\ref{tab:early-late-regime} makes that difference explicit.
@@ -386 +581 @@ The most intuitive body metric is \emph{future links per 100 suggested questions
-\subsection{Popularity at the strict shortlist}
+\subsection{Popularity and co-occurrence at the strict shortlist}
@@ -388 +583 @@ The most intuitive body metric is \emph{future links per 100 suggested questions
-At the strict top of the ranking, the simple popularity-based rule still wins. In network terms that rule is preferential attachment. The easiest way to read the magnitude is in future links captured inside a 100-question shortlist: preferential attachment places about 8.3, 12.0, 23.3, and 36.3 future directed links inside the top 100 at \(h=3,5,10,15\), while the graph-based score places about 5.7, 8.7, 16.3, and 26.3. So the popularity benchmark buys roughly 2.6, 3.3, 7.0, and 10.0 extra realized directed links inside the same 100-candidate shortlist. Put differently, preferential attachment retrieves roughly 40 percent more realized directed links than the graph score, depending on the horizon. The normalized Recall@100 and MRR statistics tell the same story.
+At the strict top of the transparent ranking, the transparent graph score already beats the simple popularity-based rule. In network terms that popularity rule is preferential attachment. The easiest way to read the magnitude is in later-realized links per 100 surfaced questions. At \(h=5\), the transparent score places about 5.7 later-realized links inside the top 100, compared with 1.7 for preferential attachment. At \(h=10\), the comparison is 11.2 versus 4.3. At \(h=15\), it is 13.0 versus 5.0. In Recall@100 terms, the same ordering is 0.085 versus 0.038 at \(h=5\), 0.089 versus 0.045 at \(h=10\), and 0.084 versus 0.036 at \(h=15\) (Figure~\ref{fig:main-benchmark}).
@@ -391 +586 @@ At the strict top of the ranking, the simple popularity-based rule still wins. I
-  \caption{Preferential attachment remains stronger at the strict shortlist margin}
+  \caption{Main benchmark: the transparent score beats popularity, and early years are a distinct regime}
@@ -394,2 +589,2 @@ At the strict top of the ranking, the simple popularity-based rule still wins. I
-  \includegraphics[width=0.92\linewidth]{mainline_full_rolling_vs_pref.png}
-  \fignotes{The left panel asks what share of later-realized links are captured inside a 100-question shortlist (Recall@100). The right panel asks how highly those later-realized links are placed within the same shortlist (MRR). Each bar is the mean across eligible rolling cutoffs for a given horizon, with bootstrap confidence intervals. For readers who prefer a more concrete scale, the corresponding mean hits inside the top-100 shortlist are about \(5.7, 8.7, 16.3,\) and \(26.3\) for the graph score and \(8.3, 12.0, 23.3,\) and \(36.3\) for preferential attachment across \(h=3,5,10,15\).}
+  \includegraphics[width=0.96\linewidth]{main_benchmark_refreshed.png}
+  \fignotes{Left: share of later-realized links captured in a 100-question shortlist (Recall@100) on the main 1990--2015 benchmark. Right: early-versus-late Recall@100 on the same benchmark, where early means 1990 and 1995 and late means 2000 through 2015 where horizon-valid. The later era is not just larger; it is a different regime.}
@@ -398 +593,49 @@ At the strict top of the ranking, the simple popularity-based rule still wins. I
-The small normalized values are real, but they are not trivial. This is a severe screening task over a very large candidate universe. On average, the future contains about 2{,}955 realized directed links at \(h=3\), 4{,}994 at \(h=5\), 13{,}221 at \(h=10\), and 29{,}809 at \(h=15\). So the top-100 shortlist is not being asked to recover a handful of outcomes. It is being asked to pull forward a small fraction of a very large future stock. That is why the benchmark should be read as a scarce-reading-time problem, not as a classifier accuracy problem.
+The small normalized values are real, but they are not trivial. This is a severe screening task over a very large candidate universe. On average, each cutoff-year cell contains about 73 realized directed links at \(h=5\), 154 at \(h=10\), and 183 at \(h=15\). So the top-100 shortlist is not being asked to recover a handful of outcomes. It is being asked to pull forward a small fraction of a large future stock. That is why the benchmark should be read as a scarce-reading-time problem, not as a classifier accuracy problem.
+
+The strict-headline result is therefore no longer ``popularity wins outright.'' The better reading is that even a transparent graph score improves on pure popularity, but only modestly relative to what the learned reranker can do on the same candidate universe.
+
+A natural question is whether the richer directed extraction is doing anything useful at all at this margin beyond co-mention. I therefore keep an undirected co-occurrence baseline as an auxiliary appendix check. But the main current comparison is now simpler: on the 1990--2015 benchmark, the transparent directed score improves on preferential attachment, and the learned reranker improves further on both. So the central issue is no longer whether the graph does anything at all. It is how much additional screening value the richer graph structure creates once the candidate universe, retrieval layer, and reranker are kept separate.
+
+But this strict result belongs to the transparent score, not to every graph-based screen built on the same candidate universe.
+
+\subsection{The learned reranker rescues the benchmark}
+
+The family-aware method-v2 refresh keeps the ontology fixed and changes only the method
+layer. On the headline \texttt{path\_to\_direct} family, with \texttt{causal\_claim} as the main anchor
+and \texttt{identified\_causal\_claim} retained as a stricter nested continuity layer, the learned
+reranker now clearly beats both the transparent score and preferential attachment. At
+\(h=5\), the best reranker reaches precision@100 of 0.105, Recall@100 of 0.138, and MRR
+of 0.0133, versus 0.057, 0.085, and 0.0078 for the transparent score and 0.017, 0.038,
+and 0.0021 for preferential attachment. At \(h=10\), the same comparison is 0.207,
+0.139, and 0.0103 versus 0.112, 0.089, and 0.0078 and 0.043, 0.045, and 0.0020. At
+\(h=15\), it is 0.264, 0.154, and 0.0116 versus 0.130, 0.084, and 0.0073 and 0.050,
+0.036, and 0.0019.
+
+The winning reranker is horizon-specific rather than universal: \texttt{glm\_logit +
+family\_aware\_boundary\_gap} at \(h=5\), \texttt{pairwise\_logit +
+family\_aware\_composition} at \(h=10\), and \texttt{glm\_logit + quality} at \(h=15\).
+That is a healthier result than freezing one
+configuration by fiat, because it shows the family-aware signal survives a conservative
+retune rather than depending on a single lucky cell. So the benchmark is best read in two
+layers. The reranker decides \emph{which} questions to show: it is the graph-based
+benchmark winner on the main top-\(K\) screening metrics for the refreshed headline
+family. The transparent score explains \emph{why} a question is structurally interesting:
+path support, gap structure, topology, and provenance. Table~\ref{tab:benchmark-summary-main}
+summarizes the refreshed comparison.
+
+\begin{table}[t]
+  \caption{Headline benchmark summary on the main 1990--2015 \texttt{path\_to\_direct} benchmark}
+  \label{tab:benchmark-summary-main}
+  \centering
+  \small
+  \begin{tabular}{L{0.34\linewidth}ccc}
+    \toprule
+    Model & \(h{=}5\) & \(h{=}10\) & \(h{=}15\) \\
+    \midrule
+    Preferential attachment & 0.017 / 0.038 / 0.0021 & 0.043 / 0.045 / 0.0020 & 0.050 / 0.036 / 0.0019 \\
+    Transparent graph score & 0.057 / 0.085 / 0.0078 & 0.112 / 0.089 / 0.0078 & 0.130 / 0.084 / 0.0073 \\
+    Learned reranker & \textbf{0.105 / 0.138 / 0.0133} & \textbf{0.207 / 0.139 / 0.0103} & \textbf{0.264 / 0.154 / 0.0116} \\
+    \bottomrule
+  \end{tabular}
+  \fignotes{Each cell reports precision@100 / Recall@100 / mean reciprocal rank, averaged across the main 1990--2015 cutoff grid. The benchmark object is the headline family \texttt{path\_to\_direct} on the broader \texttt{causal\_claim} anchor. Relative to the transparent score, the reranker raises Recall@100 by about 0.052 at \(h=5\), 0.050 at \(h=10\), and 0.070 at \(h=15\). Relative to preferential attachment, the corresponding gains are about 0.100, 0.094, and 0.118.}
+\end{table}
@@ -400 +643,6 @@ The small normalized values are real, but they are not trivial. This is a severe
-The right conclusion from the strict headline is not ``the graph score fails.'' It is narrower and more interesting. If the decision problem is to identify the single most likely next direct link under a very tight reading budget, cumulative advantage remains very hard to beat. The literature keeps returning to already central concepts. The next question is whether that headline survives once the screening frontier widens and we ask where the literature is more or less popularity-dominated.
+The paper-facing concentration layer is also horizon-specific: \texttt{sink\_plus\_diversification}
+at \(h=5\) and \(h=15\), and \texttt{diversification\_only} at \(h=10\). That improves the
+shortlist without degrading the main metrics, but it does not fully eliminate endpoint
+crowding. Repeated targets such as \texttt{Willingness to Pay.}, \texttt{Renewable Energy}, and \texttt{R\&D}
+still recur often enough that the paper should describe concentration as improved rather
+than solved.
@@ -404 +652 @@ The right conclusion from the strict headline is not ``the graph score fails.''
-The first way to move from prediction toward allocation is to relax the top-100 bottleneck. Economists rarely consume one candidate suggestion and stop; they inspect a shortlist. The attention-allocation outputs therefore ask what happens as that shortlist expands from \(K=50\) to \(K=1000\). I summarize that margin using ``future links per 100 suggested questions,'' which is just the shortlist precision rescaled into a more readable unit.
+The first way to move from prediction toward allocation is to relax the top-100 bottleneck. Economists rarely consume one candidate suggestion and stop; they inspect a shortlist. The attention-allocation outputs therefore ask what happens as that shortlist expands from \(K=50\) to \(K=1000\). I summarize that margin using ``future links per 100 suggested questions''---out of 100 suggestions, how many later appear? In this subsection the object is still the transparent score, because that is the score whose mechanics can be read directly question by question.
@@ -406 +654 @@ The first way to move from prediction toward allocation is to relax the top-100
-The result is again mixed but informative. At \(h=3\), preferential attachment places about 11.0 future links per 100 suggestions at \(K=100\), compared with 5.75 for the graph score. By \(K=1000\), the two rules are essentially tied in practical terms: preferential attachment yields about 4.25 future links per 100 while the graph score yields about 4.70. The same pattern appears at \(h=5\): the gap is 14.75 versus 8.25 at \(K=100\), but 6.83 versus 7.10 by \(K=1000\). At \(h=10\), the tight-budget gap remains larger, yet even there the frontier narrows substantially, from 27.5 versus 17.75 at \(K=100\) to 13.6 versus 13.5 by \(K=1000\). The point is not that the graph score suddenly becomes the dominant forecaster. It is that a winner-take-all top-rank view overstates how far popularity dominates the broader reading lists that real researchers actually inspect.
+The result is informative (Figure~\ref{fig:attention-frontier-main}), but it is no longer the same result as in the earlier draft. On the current 1990--2015 benchmark, the transparent score already leads preferential attachment at \(K=50\) and \(K=100\) at all three main horizons. At \(h=10\), for example, the transparent score yields about 13.0 future links per 100 suggestions at \(K=50\) and 11.2 at \(K=100\), versus 1.3 and 4.3 for preferential attachment. The key frontier lesson is therefore not that popularity wins the tight shortlist and then fades. It is that the transparent score's advantage is concentrated in tighter shortlists and narrows sharply once the reading list expands toward \(K=500\) or \(K=1000\).
@@ -409 +657 @@ The result is again mixed but informative. At \(h=3\), preferential attachment p
-  \caption{The attention-allocation frontier softens the strict-shortlist headline}
+  \caption{The attention-allocation frontier shows where the transparent score's edge fades}
@@ -412,2 +660,10 @@ The result is again mixed but informative. At \(h=3\), preferential attachment p
-  \includegraphics[width=0.97\linewidth]{attention_allocation_frontier_main.png}
-  \fignotes{Each panel reports mean future links per 100 surfaced suggestions as the shortlist expands from \(K=50\) to \(K=1000\). In plain terms, the figure asks what happens as a researcher becomes willing to inspect more suggestions. Preferential attachment remains stronger at very small \(K\), but the gap shrinks sharply as that shortlist widens.}
+  \includegraphics[width=0.97\linewidth]{attention_allocation_frontier_refreshed.png}
+  \fignotes{Each panel reports mean future links per 100 surfaced suggestions as the shortlist expands from \(K=50\) to \(K=1000\) on the main 1990--2015 benchmark, using horizon-valid cutoff cells. The transparent graph score leads at \(K=50\) and \(K=100\) for all three main horizons. By \(K=500\), the gap is small. By \(K=1000\), the two rules are nearly tied at \(h=5\) and preferential attachment is slightly ahead at \(h=10\) and \(h=15\).}
+\end{figure}
+
+\begin{figure}[t]
+  \caption{No simple score dominates at every shortlist size}
+  \label{fig:precision-at-k}
+  \centering
+  \includegraphics[width=0.97\linewidth]{precision_at_k_curves_refreshed.png}
+  \fignotes{Each panel reports mean precision@\(K\) across the main 1990--2015 horizon-valid cutoff grid, with log-scale \(K\). The transparent graph score is strongest at the very tight shortlist margin (\(K=25\) and \(K=50\)) at all three main horizons. Co-occurrence is slightly strongest at intermediate shortlist sizes (\(K=100\) and \(K=200\), and also \(K=500\) at \(h=10\) and \(h=15\)). By \(K=1000\), the simple-score family largely converges, with directed degree product slightly ahead at \(h=10\) and \(h=15\).}
@@ -416 +672 @@ The result is again mixed but informative. At \(h=3\), preferential attachment p
-That makes the current paper's answer to the title more precise. If ``what should economics ask next?'' is interpreted as ``what is the single most likely next direct link?'', preferential attachment wins. If it is interpreted as ``which questions should a researcher read, scope, or test next under a realistic shortlist budget?'', the graph-based object becomes more relevant. It remains weaker at the very top rank, but it moves materially closer once the screening problem looks more like actual research browsing.
+Figure~\ref{fig:precision-at-k} makes the current paper's answer to the title more precise. Among the simple scores, there is no single winner across shortlist sizes. The transparent graph score is strongest at the first reading tranche, which is exactly where a researcher decides which 25, 50, or 100 questions deserve inspection first. Co-occurrence becomes slightly stronger at intermediate shortlist sizes, and by very broad lists the simple scores largely converge. That is why the transparent score should be read as an interpretable strict-shortlist screen rather than as a universal winner across every attention budget, and why the learned reranker matters: it is the layer that stabilizes screening quality once the benchmark is no longer a single hand-tuned heuristic. This is exactly the margin emphasized by Kleinberg et al.~\citeyearpar{kleinberg2015prediction}: the gain comes from improving which cases are inspected first, not from winning an effectively exhaustive ranking. It also fits Agrawal, McHale, and Oettl's~\citeyearpar{agrawal2024ai} view of AI-assisted discovery as prioritized search and the economics-of-ideas view in Bloom et al.~\citeyearpar{bloom2020ideas} and Jones~\citeyearpar{jones2009burden} that frontier navigation becomes harder as the stock of existing work expands.
@@ -422 +678 @@ Future appearance is not the only margin that matters. A later realized link can
-The answer is again disciplined rather than triumphant. Weighted MRR still favors preferential attachment at each of the main horizons: about 0.001523 versus 0.001383 at \(h=3\), 0.001154 versus 0.000943 at \(h=5\), and 0.000809 versus 0.000568 at \(h=10\). So the strict-headline result is not only about low-value fills. Central concepts still capture more of the heavily reused future links. But the broader weighted frontier is less one-sided than the weighted MRR line alone suggests. At \(K=1000\), weighted recall is nearly tied at \(h=3\) and \(h=10\): preferential attachment reaches about 0.01762 and 0.01495, while the graph score reaches about 0.01729 and 0.01488. The gap is still larger at \(h=5\), but even there it is far smaller than the tight-rank headline would suggest.
+The refreshed weighted result is disciplined but more favorable to the graph score than the older draft. Once future links are weighted by later reuse, the transparent graph score beats preferential attachment on weighted MRR at all three main horizons. At \(h=10\), for example, weighted MRR is about 0.0105 for the transparent score versus 0.0022 for preferential attachment. The weighted recall frontier still bends back toward popularity as \(K\) becomes very broad, but the strict-shortlist weighted margin is now clearly on the graph side (Figure~\ref{fig:impact-weighted-main}).
@@ -425 +681 @@ The answer is again disciplined rather than triumphant. Weighted MRR still favor
-  \caption{Value-weighting changes the scale of the benchmark but does not overturn the headline}
+  \caption{Value-weighting strengthens the strict-shortlist case for the transparent score}
@@ -428,2 +684,2 @@ The answer is again disciplined rather than triumphant. Weighted MRR still favor
-  \includegraphics[width=0.97\linewidth]{impact_weighted_main.png}
-  \fignotes{The left panel reports weighted MRR by horizon, where future realized links are weighted by later reuse. The right panels report weighted recall frontiers over shortlist size \(K\). Preferential attachment still dominates the tighter top ranks, but the weighted frontier narrows materially at broad lists.}
+  \includegraphics[width=0.97\linewidth]{impact_weighted_main_refreshed.png}
+  \fignotes{The left panel reports weighted MRR by horizon, where future realized links are weighted by later reuse. The transparent graph score is higher than preferential attachment at all three main horizons. The right panels report weighted recall frontiers over shortlist size \(K\). The transparent score leads at the strict shortlist margin, especially at \(K=50\), and remains ahead through \(K=500\) at \(h=15\). By \(K=1000\), preferential attachment is again slightly ahead.}
@@ -432 +688 @@ The answer is again disciplined rather than triumphant. Weighted MRR still favor
-That result matters for how the title should be read. It shows that the paper is not merely reclassifying trivial future links as success. Weighting by downstream reuse leaves the top-rank popularity story intact. The more favorable reading for the graph score enters instead through broader attention frontiers and through the kinds of literatures in which local structure does more screening work.
+That result matters for how the title should be read. It shows that the paper is not merely reclassifying trivial future links as success. Weighting by downstream reuse does not erase the graph signal; if anything, it sharpens the strict-shortlist case for the transparent score. But it does not make popularity irrelevant either. At very broad reading lists, central concepts still reclaim some of the weighted frontier. So the value-weighted evidence reinforces the same budget logic as the binary frontier: local graph structure helps most when the reading problem is selective, while popularity becomes a stronger guide once the shortlist becomes very broad.
@@ -434 +690 @@ That result matters for how the title should be read. It shows that the paper is
-This is also where the paper's credibility story enters. The graph is not built from raw co-occurrence. It already carries stability, causal-presentation, evidence-type, and edge-role metadata from the paper-local extraction layer. Appendix~\ref{app:credibility-audit} shows that directed causal rows have mean stability around 0.93, compared with about 0.87 for undirected contextual rows, and that over 90 percent of directed causal rows fall into the high-stability band. So the method-family heterogeneity results below are not just subfield color. They are part of the paper's broader claim that some local graph neighborhoods are more credible terrain for screening than others, even though the current main score does not yet fully weight those signals.
+This is also where the paper's evidence-quality dimension enters. The graph is not built from raw co-occurrence. It already carries stability, causal-presentation, evidence-type, and edge-role metadata from the paper-local extraction layer. Appendix~\ref{app:credibility-audit} shows that directed causal rows have mean stability around 0.93, compared with about 0.87 for undirected contextual rows, and that over 90 percent of directed causal rows fall into the high-stability band. So the method-family heterogeneity results below are not just subfield color. They are part of the paper's broader claim that some local graph neighborhoods are more credible terrain for screening than others, even though the current main score does not yet fully weight those signals.
@@ -438 +694 @@ This is also where the paper's credibility story enters. The graph is not built
-The pooled top-100 comparison hides meaningful variation. The most useful way to read the atlas is not as a search for one subgroup in which the graph score cleanly ``wins.'' It is a map of where cumulative advantage is more dominant and where the nearby structure of the literature adds more screening value. Once the frontier is evaluated over broader fixed-\(K\) and percentile-\(K\) shortlists, the graph score becomes substantially more competitive than the strict top-100 headline suggests. In the pooled frontier view, its percentile-\(K\) advantage is slightly positive at each of \(h=3,5,10,15\), even though the top-100 delta is near zero or negative. That already changes the interpretation of the exercise: the model looks weaker as a winner-take-all forecaster than it does as a broader screening rule.
+The strict top-100 comparison hides meaningful variation across reading budgets. On the current benchmark panel, once the same candidates are evaluated over broader fixed-\(K\) and pool-share shortlists, the transparent score looks materially stronger than the strict top-100 headline suggests (Figure~\ref{fig:pooled-frontier}). At \(h=10\) and \(h=15\), for example, the mean top-100 recall gap remains about \(+0.044\), but the broader frontier delta is about \(+0.032\) in both cases. The right interpretation is therefore not that the graph score fails outside a winner-take-all contest. It is that its comparative advantage is largest when the reading problem is still selective and then flattens as the shortlist becomes very broad.
@@ -441 +697 @@ The pooled top-100 comparison hides meaningful variation. The most useful way to
-  \caption{The pooled frontier view is more favorable to the graph score than the strict top-100 headline}
+  \caption{Broader shortlist views are more favorable to the graph score than the strict top-100 headline}
@@ -444,2 +700,2 @@ The pooled top-100 comparison hides meaningful variation. The most useful way to
-  \includegraphics[width=0.92\linewidth]{pooled_frontier_main.png}
-  \fignotes{The pooled frontier figure reports the graph score's relative recall advantage over preferential attachment. Positive values favor the graph score. The lighter horizon lines correspond to shorter horizons and the darker lines to longer horizons. The key interpretation is that the graph score becomes more competitive once the shortlist expands beyond the strict top-100 comparison.}
+  \includegraphics[width=0.92\linewidth]{pooled_frontier_main_refreshed.png}
+  \fignotes{The figure reports the transparent graph score's relative recall advantage over preferential attachment on the refreshed historical benchmark panel. The left panel uses fixed shortlists. The right panel uses pool-share shortlists equal to 1, 2, 5, and 10 percent of the 5,000-candidate retrieval pool. Positive values favor the graph score. The main pattern is that the graph score looks strongest once the reading problem is allowed to expand beyond the strict top-100 slice, but its edge still fades as the shortlist becomes very broad.}
@@ -448 +704 @@ The pooled top-100 comparison hides meaningful variation. The most useful way to
-The subgroup results sharpen this interpretation. Journal tier matters. Adjacent journals are more favorable terrain for the graph score than the core: the pooled percentile-frontier advantage is about \(0.000320,0.000275,0.000201,\) and \(0.000155\) at \(h=3,5,10,15\) in adjacent journals, compared with \(0.000134,0.000109,0.000058,\) and \(0.000038\) in core journals. Method family matters as well. Design-based causal slices are much more favorable than panel- or time-series-heavy slices: the pooled percentile-frontier delta for the design-based group is about \(0.000717,0.001029,0.000354,\) and \(0.000063\) at \(h=3,5,10,15\), while the panel/time-series group is negative at every one of those horizons.
+The subgroup results sharpen this interpretation (Figure~\ref{fig:method-forest}). Journal tier matters: adjacent journals are now clearly more favorable terrain than the core on the broader frontier view, with frontier deltas around \(+0.066\) to \(+0.070\) in adjacent journals versus roughly \(+0.013\) to \(+0.022\) in the core. Method family matters as well. Design-based causal slices remain strongly positive at all main horizons, while panel- and time-series-heavy slices are close to zero by \(h=10\) and \(h=15\) rather than strongly negative.
@@ -454,2 +710,2 @@ The subgroup results sharpen this interpretation. Journal tier matters. Adjacent
-  \includegraphics[width=0.88\linewidth]{method_theory_forest_main.png}
-  \fignotes{This figure compares broad method families. The practical reading is simple: design-based causal work is materially more favorable terrain for the graph score than panel- or time-series-heavy work.}
+  \includegraphics[width=0.88\linewidth]{method_theory_forest_main_refreshed.png}
+  \fignotes{This figure compares broad method families on the refreshed benchmark panel. Design-based causal work is materially more favorable terrain for the graph score than panel- or time-series-heavy work. In the latter slices, the broader-frontier advantage is near zero at the longer horizons.}
@@ -458,11 +714 @@ The subgroup results sharpen this interpretation. Journal tier matters. Adjacent
-Funding adds nuance rather than a single clean pattern. In the coarse funded-versus-unfunded split, the funded literature is actually less favorable to the graph score: the pooled percentile-frontier delta is negative at all main horizons for funded work and positive at all main horizons for unfunded work. That does not mean funding suppresses good ideas. It means that, in this benchmark, funded realizations look more popularity-dominated on average. The appendix therefore treats funding as suggestive rather than central, and Appendix Figure~\ref{fig:funding-source} is useful mainly because it shows that the funded pattern is not uniform. Among the stable high-support funders, the Economic and Social Research Council is the clearest positive outlier, while the large China and Germany groups are closer to zero and the U.S. National Science Foundation is roughly neutral.
-
-The topic split makes the same point in more familiar language. The graph score looks strongest in health-care systems and quality-of-life topics, in labor-market-and-inequality questions, and in several banking, housing, and macro-policy clusters. It looks weaker in a smaller set of environmental-policy and discrete-choice clusters. That should not be over-read as a ranking of subfields. It is a map of where the pooled average hides concrete heterogeneity.
-
-\begin{figure}[t]
-  \caption{Economics-facing topic heterogeneity}
-  \label{fig:topic-heatmap-main}
-  \centering
-  \includegraphics[width=0.90\linewidth]{subfield_heatmap_main.png}
-  \fignotes{The main topic heatmap prioritizes the most populous economics-facing topic groups rather than all broad adjacent categories. Cell color reports the pooled percentile-frontier advantage of the graph score over preferential attachment, while the annotations report the top-100 hit delta in basis points.}
-\end{figure}
+Funding adds nuance rather than one clean sign pattern. In the coarse funded-versus-unfunded split, unfunded work is consistently positive at all three main horizons, while funded work is close to zero at \(h=5\), negative at \(h=10\), and positive again at \(h=15\). That is not a stable enough pattern to make funding central in the main text. It is still useful in the appendix because the interaction plot shows that the relevant contrast is not simply funded versus unfunded. The strongest positive cells are unfunded-adjacent slices, while funded-core slices are the most popularity-dominated.
@@ -470 +716 @@ The topic split makes the same point in more familiar language. The graph score
-The robust main-text message is therefore restrained but substantive. Broader frontier shortlists soften the pooled headline. Adjacent journals look better than the core. Design-based slices look better than panel or time series. Several concrete economics topics look better than the pooled average. Funding seems to matter, but mostly as a secondary institutional layer on top of the more basic popularity-versus-structure comparison. If the title is read as a question about where a structural screen is most useful, this subsection gives the clearest answer: not everywhere equally, but especially in adjacent, design-based, and several concrete economics-facing topic clusters.
+The refreshed main-text message is therefore narrower but cleaner. Broader shortlist views are more favorable to the graph score than the strict top-100 headline. Adjacent journals look better than the core on those broader frontiers. Design-based slices look much better than panel or time series. Funding patterns are mixed and should be read cautiously rather than as a central result.
@@ -472 +718 @@ The robust main-text message is therefore restrained but substantive. Broader fr
-\subsection{Path development beyond direct-link closure}
+\subsection{Path development and the richer surfaced object}
@@ -477 +723 @@ The robust main-text message is therefore restrained but substantive. Broader fr
-The direct-link framing is not the only way research can evolve. A literature can also move in the reverse direction: starting from a direct claim, later work can add mediating paths around it rather than closing a previously missing direct relation. I therefore distinguish two simple transition types on length-2 structure. ``Path to direct'' means that a supporting \(u \rightarrow w \rightarrow v\) path already exists at \(t-1\), the direct \(u \rightarrow v\) link does not, and that direct link then appears by \(t+h\). ``Direct to path'' means the direct link exists first, but a supporting mediator path appears only later.
+The direct-link framing is not the only way research can evolve. Park, Leahey, and Funk~\citeyearpar{park2023disruptive} document a broad decline in disruptive science, which in the language of this graph means the literature increasingly thickens around existing claims rather than opening genuinely new direct connections. A literature can move in the reverse direction from what the benchmark measures: starting from a direct claim, later work can add mediating paths around it rather than closing a previously missing direct relation. I therefore distinguish two simple transition types on length-2 structure (Figure~\ref{fig:candidate-schematic}). ``Path to direct'' means that a supporting \(u \rightarrow w \rightarrow v\) path already exists at \(t-1\), the direct \(u \rightarrow v\) link does not, and that direct link then appears by \(t+h\). ``Direct to path'' means the direct link exists first, but a supporting mediator path appears only later.
@@ -483,2 +729,2 @@ The direct-link framing is not the only way research can evolve. A literature ca
-  \includegraphics[width=0.88\linewidth]{path_evolution_comparison.png}
-  \fignotes{This figure compares two transition types on length-2 graph structure. ``Path to direct'' means a local path exists first and the missing direct edge later appears. ``Direct to path'' means a direct edge exists first and a supporting mediator path appears only later. The unit of analysis is the eligible concept pair at each cutoff-period and horizon cell. Shares are computed relative to eligible pair stocks in the corresponding transition class. The figure should be read as a graph-evolution result rather than a forecast metric: it shows that mechanism-deepening around existing direct claims is often more common than direct-link closure.}
+  \includegraphics[width=0.88\linewidth]{path_evolution_comparison_refreshed.png}
+  \fignotes{``Path to direct'': a local path exists first and the direct link appears later. ``Direct to path'': the direct link exists first and a mediating path appears later. Mechanism-deepening around existing claims dominates at all horizons.}
@@ -487,3 +733 @@ The direct-link framing is not the only way research can evolve. A literature ca
-The aggregate comparison yields a striking result. Direct-to-path transitions dominate path-to-direct transitions in every cutoff-period block and at every horizon currently studied. At \(h=10\), for example, the direct-to-path share rises from roughly 0.049 in the 1980s to 0.089 in the 1990s, 0.178 in the 2000s, and 0.355 in the 2010s. The corresponding path-to-direct shares are much smaller: about 0.023, 0.014, 0.015, and 0.020. So the literature often elaborates mechanisms around claims it already treats as direct rather than closing a missing direct link implied by nearby paths.
-
-\subsubsection{Where path closure is more common}
+The aggregate comparison yields the same qualitative result on the refreshed stack, but with more disciplined magnitudes (Figure~\ref{fig:path-evolution}). Direct-to-path transitions dominate path-to-direct transitions in every cutoff-period block and at every horizon. The cleanest way to state this is in transition rates, because the eligible sets differ. At \(h=10\), the direct-to-path transition share rises from about \(0.009\) in the 1990s to \(0.043\) in the 2000s and \(0.121\) in the 2010s, while the corresponding path-to-direct shares are about \(0.003\), \(0.007\), and \(0.014\). The literature therefore still elaborates mechanisms around claims it already treats as direct much more often than it closes a missing direct link implied by nearby paths. That pattern is independently supported by recent topological work: Foster, Ziegelmeier, and Evans~\citeyearpar{foster2025gaps} show that papers which open structural gaps in the knowledge network are more cited and more disruptive than papers that merely introduce novel combinations without opening gaps. The present finding is the directed-graph analog: the literature thickens around existing direct claims more often than it closes the structural gaps implied by nearby paths.
@@ -491 +735 @@ The aggregate comparison yields a striking result. Direct-to-path transitions do
-The journal split is especially revealing. At \(h=3,5,10,15\), the share of realized path-related transitions that take the path-to-direct form is about 0.571, 0.579, 0.529, and 0.471 in adjacent journals, but only about 0.442, 0.443, 0.400, and 0.360 in the core. So adjacent journals are much more path-closure heavy. The core is more likely to elaborate around existing direct links.
+The pattern varies across the literature in economically interpretable ways. Adjacent journals are relatively more path-closure heavy than the core, but direct-to-path still dominates in both tiers. At \(h=5\), the share of realized transitions taking the path-to-direct form is about \(0.45\) in adjacent journals versus \(0.28\) in the core. Finance remains more direct-to-path heavy throughout. Figure~\ref{fig:path-source-mix} reports the journal-tier split.
@@ -493 +737 @@ The journal split is especially revealing. At \(h=3,5,10,15\), the share of real
-\begin{figure}[t]
+\begin{figure}[h]
@@ -497,12 +741,2 @@ The journal split is especially revealing. At \(h=3,5,10,15\), the share of real
-  \includegraphics[width=0.90\linewidth]{path_transition_mix_by_source.png}
-  \fignotes{The figure reports the mix of realized path-related transitions by journal tier. The reported quantity is the share of realized transitions that take the path-to-direct form rather than the direct-to-path form. A higher value therefore means more direct-link closure relative to mechanism-deepening around existing direct edges. The unit of analysis is the realized transition within each journal-tier-by-horizon cell. Adjacent journals are consistently more path-to-direct heavy than core journals, although direct-to-path remains important in both.}
-\end{figure}
-
-The broad subfield split points in the same direction. Economics and Econometrics is relatively balanced at short horizons, with path-to-direct shares of about 0.528 and 0.532 at \(h=3\) and \(h=5\), before turning more direct-to-path heavy by \(h=10\) and longer horizons. Finance is more direct-to-path heavy throughout: the path-to-direct share is only about 0.418, 0.425, 0.398, and 0.366 at \(h=3,5,10,15\). So the path result is not just a pooled artifact. It varies in economically interpretable ways across the literature.
-
-\begin{figure}[t]
-  \caption{Path transition mix by broad subfield}
-  \label{fig:path-subfield-main}
-  \centering
-  \includegraphics[width=0.88\linewidth]{path_transition_mix_by_subfield.png}
-  \fignotes{This figure reports the share of realized path-related transitions that take the path-to-direct form by broad subfield and horizon. Economics and Econometrics is more balanced than Finance at short horizons, but both become more direct-to-path heavy at longer horizons. The result supports the main interpretation that graph evolution often proceeds by mechanism-deepening around known direct claims.}
+  \includegraphics[width=0.90\linewidth]{path_transition_mix_by_source_refreshed.png}
+  \fignotes{Share of realized path-related transitions taking the path-to-direct form by journal tier and horizon on the refreshed stack. Adjacent journals are consistently more path-closure heavy than the core, but direct-to-path remains the larger transition type in both tiers.}
@@ -511 +745 @@ The broad subfield split points in the same direction. Economics and Econometric
-\subsubsection{Current path-rich examples}
+\subsubsection{Current surfaced examples}
@@ -513 +747 @@ The broad subfield split points in the same direction. Economics and Econometric
-The recommendation layer already hints at what path-rich questions look like. By path-rich, I mean questions supported by many nearby chains of connections rather than by one isolated bridge. Investment \(\rightarrow\) carbon emissions is supported by 38 observed paths through concepts such as economic growth, technological innovation, and economic development. Public debt \(\rightarrow\) CO\(_2\) emissions has 23 supporting paths through growth, financial development, and renewable energy consumption. Monetary policy \(\rightarrow\) energy consumption has 23 supporting paths through income, output, and income inequality. These examples are not historical validation evidence, but they do show why the path-based object is concrete enough to inspect in the public interface rather than treat as an abstract graph statistic.
+The recommendation layer is easiest to understand once the hierarchy is explicit. The benchmark is still recorded on direct-link anchors. The surfaced object a researcher reads is usually a path or mechanism question. Context-transfer and evidence-type prompts are generated only when the graph's evidence metadata is strong. Family-aware comparison is a later extension, not the paper's main benchmark.
@@ -516,2 +750,2 @@ The recommendation layer already hints at what path-rich questions look like. By
-  \caption{Selected path-rich candidate questions}
-  \label{tab:path-examples-main}
+  \caption{Curated main-text examples from the refreshed current frontier}
+  \label{tab:curated-examples-main}
@@ -519 +753,2 @@ The recommendation layer already hints at what path-rich questions look like. By
-  \begin{tabular}{L{0.34\linewidth}L{0.11\linewidth}L{0.45\linewidth}}
+  \small
+  \begin{tabular}{L{0.20\linewidth}L{0.19\linewidth}L{0.35\linewidth}L{0.18\linewidth}}
@@ -521 +756 @@ The recommendation layer already hints at what path-rich questions look like. By
-    Candidate question & Supporting paths & Example mediators \\
+    Example role & Anchor or pair & Surfaced question & What it illustrates \\
@@ -523,5 +758,4 @@ The recommendation layer already hints at what path-rich questions look like. By
-    Investment \(\rightarrow\) carbon emissions & 38 & economic growth; technological innovation; economic development \\
-    Public debt \(\rightarrow\) CO\(_2\) emissions & 23 & economic growth; financial development; renewable energy consumption \\
-    Monetary policy \(\rightarrow\) energy consumption & 23 & income; output; income inequality \\
-    Trade liberalisation \(\rightarrow\) energy consumption & 5 & economic growth; foreign direct investment; trade liberalization \\
-    Urbanization \(\rightarrow\) output growth & 17 & CO\(_2\) emissions; energy consumption; energy use \\
+    Anchored policy mechanism & Digital economy \(\rightarrow\) environmental regulation & Does green innovation mediate the digital economy \(\rightarrow\) environmental regulation relation? & Clean policy-facing mechanism question from the top shortlist. \\
+    Trade and innovation bridge & Trade liberalization \(\rightarrow\) R\&D & Does productivity mediate the trade-liberalization \(\rightarrow\) R\&D relation? & Cross-domain bridge with a readable mediator. \\
+    Environmental upgrading & Environmental quality \(\rightarrow\) green innovation & Does policy uncertainty help explain the environmental-quality \(\rightarrow\) green-innovation relation? & Anchored progression question in an environmental-policy neighborhood. \\
+    Innovation and market design & R\&D \(\rightarrow\) carbon emission trading & Does green innovation connect R\&D to carbon-emission trading? & Mechanism-deepening question that links innovation to a policy instrument. \\
@@ -532 +766,12 @@ The recommendation layer already hints at what path-rich questions look like. By
-Taken together, Sections 5.1 to 5.5 imply a cumulative reading of the evidence. The strict top-100 benchmark is harsh and popularity-dominated. Broader attention frontiers soften that headline. Value-weighting changes the scale of the comparison without reversing it. Heterogeneity shows where structural screening is actually more useful. The path audit then explains why even that richer reading still does not exhaust the graph's value: a good share of scientific development takes the form of mechanism-deepening around existing direct claims, not only direct-link closure itself. In that sense, the most useful questions to ask next are often better understood as path-rich research programs than as single isolated missing edges.
+These examples (Table~\ref{tab:curated-examples-main}) reflect what the refreshed current
+frontier actually surfaces. The headline benchmark family is still \texttt{path\_to\_direct}, but
+the strongest surfaced cases are rarely fully open missing edges. They are mostly
+anchored progression cases---internally concentrated in \texttt{causal\_to\_identified}---that
+read more naturally as mechanism questions around claims the literature already partly
+supports. That is a useful empirical finding, not an embarrassment. It means the current
+system's most readable suggestions are not generic “connect any two nodes” gaps, but
+more specific questions about how an already plausible relation should be tightened,
+clarified, or identified. Appendix~\ref{app:path-extensions} collects a short reserve
+table of additional examples chosen to avoid thematic repetition.
+
+Taken together, the evidence is cumulative. Popularity dominates the strict top rank; the reranker rescues the benchmark; broader shortlists, value-weighting, and heterogeneity all confirm that local graph structure is informative once the decision problem resembles actual research browsing. The path-development results add a further dimension: much of scientific development takes the form of mechanism-deepening around existing claims, which means the most useful questions to ask next are often richer than single missing edges.
@@ -536 +781,9 @@ Taken together, Sections 5.1 to 5.5 imply a cumulative reading of the evidence.
-Several limits matter for interpretation. A future realized link is not the same thing as truth, importance, or policy value. The benchmark is about future appearance in the literature, not about a complete normative theory of which questions economists should pursue. If cumulative advantage dominates the future, preferential attachment can outperform even when the graph score is surfacing more genuinely underexplored questions. That is why I treat the prospective benchmark as informative but not exhaustive.
+The benchmark tested a specific tension: does the nearby structure of a field carry screening information beyond what cumulative advantage provides? The answer is layered. Popularity dominates the strict top rank, but the learned reranker beats every baseline at every horizon once graph features are allowed to reweight. Directed features alone outperform co-occurrence, the reranker generalizes forward to a held-out era, and the graph-based edge is strongest when the local graph is rich enough to support selective screening rather than when the neighborhood is maximally thin. Local graph structure is not a replacement for cumulative advantage, but it is informative enough to improve screening once the decision problem resembles actual research browsing rather than winner-take-all prediction.
+
+That interpretation also clarifies what the system does and does not do. It does not replace field knowledge. It does not replace causal identification. It does not replace paper-level judgment about feasibility, data access, or policy importance. What it can do is help order a large set of candidate next questions so that scarce reading and design effort are spent on questions that are open, locally supported, and concrete enough to inspect. In that sense, the paper is about screening under attention constraints, not automated scientific decision-making.
+
+Several limits remain important. First, the reranker is a linear model with 34 manually engineered features, not a richer representation learner---though the grouped decomposition in Appendix~\ref{app:reranker-design} still shows a substantively interpretable signal. Once broad support-graph popularity is separated from directed causal centrality, the reranker loads positively on directed causal degree, recency, and evidence quality, while broad support degree enters with a negative sign.\footnote{Gu and Krenn~\citeyearpar{gu2025impact4cast} use 141 features and a deep neural network for a similar task. A richer model class is a natural extension, though the present paper deliberately keeps the benchmark family small and interpretable.} It also generalizes forward. A held-out era test (Appendix~\ref{app:temporal-generalization}, Figure~\ref{fig:temporal-generalization-main}) selects reranker configurations using 1990--2005 cutoffs only and then evaluates them on the fully unseen 2010--2015 era. In absolute \(P@100\) terms, the reranker's gap over preferential attachment is larger in the held-out era than in the earlier training-era cells. That is a stronger temporal transfer than the single-holdout design in Gu and Krenn~\citeyearpar{gu2025impact4cast}. But the reranker still has systematic blind spots: it succeeds where the local graph already contains usable structure and misses structurally surprising connections in neighborhoods that remain sparse even after the current extraction and normalization steps. Those missed realizations are the ``alien'' territory of Sourati et al.~\citeyearpar{sourati2023accelerating}, and they mark the natural boundary of any graph-based screen.
+
+Second, I tested whether incorporating researcher positioning improves screening, following Sourati et al.~\citeyearpar{sourati2023accelerating}, who find that author-awareness improves discovery prediction by up to 400 percent in biomedicine. In economics at the concept granularity and candidate-pool depth used in this paper (top 10{,}000 candidates by graph score), author expertise is fully saturated: every candidate pair has author overlap---a median of 69 authors who have published on both endpoint concepts---and author features add no incremental signal after controlling for endpoint degree.\footnote{This saturation partly reflects the candidate pool: the top 10{,}000 pairs by graph score are well-connected by construction, so they attract many researchers. A deeper candidate pool including sparser pairs would likely show less saturation. The author measure is also cumulative: any author who ever published on both concepts counts, regardless of whether they are currently active. A recency-weighted or active-researcher measure would be stricter. Leng, Wang, and Yuan~\citeyearpar{leng2024hypothesis} use graph-based metrics to evaluate LLM-generated social-science hypotheses, providing a complementary approach where graph structure also carries the main screening signal.} The likely explanation is domain-specific. Economics has fewer, broader concepts with more overlap in researcher portfolios than the specific material-property combinations studied in biomedicine, where a chemist specializing in one material may have no overlap with a physicist studying a different one. A finer-grained concept inventory, a method-specific notion of expertise (e.g., does the pair have an author with the right identification strategy?), or a recency-weighted author measure might recover the Sourati et al.\ effect in economics. But at the current granularity the incremental signal is in the directed claim structure, not the social network of researchers.
+
+Third, the extraction layer introduces noise. LLM-based extraction is more accurate than keyword co-occurrence but still imperfect. The pipeline records stability and provenance metadata to support auditing (Appendix~\ref{app:credibility-audit}), and the benchmark results are conditional on the concept inventory embedded in the normalization pipeline.
@@ -538 +791,9 @@ Several limits matter for interpretation. A future realized link is not the same
-Direction in the graph records ordered claim relations rather than final causal adjudication. The main score still treats the existence of an edge more seriously than the strength or credibility of the underlying evidence, even though method and stability metadata now exist in the pipeline. That is one reason the next methodological step should probably incorporate stronger credibility weighting and perhaps separate tasks for directed causal emergence, undirected contextual emergence, and path emergence.
+\begin{figure}[t]
+  \caption{Temporal generalization: the reranker generalizes forward, not backward}
+  \label{fig:temporal-generalization-main}
+  \centering
+  \includegraphics[width=0.90\linewidth]{temporal_generalization_refreshed.png}
+  \fignotes{For each main horizon, the reranker is selected using only 1990--2005 cutoff cells and then evaluated on the fully held-out 2010--2015 era. Labels report the reranker's absolute \(P@100\) gap relative to preferential attachment. The held-out gap is larger than the earlier training-era gap at both \(h=5\) and \(h=10\). Full results in Appendix Table~\ref{tab:temporal-generalization}.}
+\end{figure}
+
+Two broader concerns deserve mention. First, the graph does not add the most value where the literature is maximally thin. The refreshed regime split in Appendix~\ref{app:regime-extensions} shows that the transparent score helps more in denser local neighborhoods than in the sparsest ones, and that its relative edge is larger in lower-FWCI slices than in the highest-FWCI ones. So the system is not a machine for solving the hardest ``alien'' cases. It is a machine for reallocating attention inside the large middle of the literature where there is already enough local structure to exploit.\footnote{Tong et al.~\citeyearpar{tong2024automating} compare knowledge-graph-generated hypotheses with LLM-only hypotheses in psychology and find that the graph adds value, validated by domain experts. That comparison has not been run in economics. Ludwig and Mullainathan~\citeyearpar{ludwig2024hypothesis} emphasize that ML-generated hypotheses must be verified as genuinely novel, which the prospective benchmark partially but not fully addresses.} Second, the paper does not test whether a well-prompted language model could generate equally good candidate questions without the graph. That LLM-only baseline is a natural next test.
@@ -540 +801 @@ Direction in the graph records ordered claim relations rather than final causal
-The published-journal corpus is a further deliberate restriction rather than a universal map of all economics research. It gives the project a cleaner realized literature, but it underweights working-paper traffic, seminar diffusion, and some forms of genuinely new frontier language.
+Those limits point to clean next steps rather than a conceptual gap. Natural extensions include stronger credibility weighting inside the screening layer, a separate benchmark for path emergence rather than only direct-link appearance, and supplementary current-usefulness checks. Appendix~\ref{app:current-usefulness} reports two such exercises on the surfaced objects: a small blinded human exercise and a parallel appendix LLM sweep. Both are intentionally secondary to the historical benchmark. The human exercise is mixed rather than one-sided: graph-selected items look somewhat more interpretable and slightly less artifact-like, while preferential-attachment items read slightly more smoothly and there is no overall mean-score advantage. The appendix LLM sweep is more favorable to the graph-based selections, but it is era-sensitive and therefore remains supplementary rather than part of the main benchmark.
@@ -542 +803,3 @@ The published-journal corpus is a further deliberate restriction rather than a u
-These limits do not make the exercise empty. They define its scope. The paper's answer to its own title is narrower than a welfare theorem but still substantive: economics should not decide what to ask next only through cumulative advantage. The most useful surfaced questions are neglected enough to remain open, supported enough to be credible, concrete enough to become papers, and best read at realistic attention frontiers rather than at winner-take-all top ranks. Empirically, that means the strict top-100 shortlist still favors preferential attachment, but broader attention frontiers, value-weighted outcomes, heterogeneity, and path development all make more room for structural screening than the pooled headline alone suggests. A next iteration should add stronger credibility weighting and richer path-based objects, and could also compare explanation or reranking layers across LLMs as a bounded appendix-style extension without changing the current paper's observational core.
+More broadly, the paper sits at an early stage of a larger shift. As AI-assisted discovery tools mature \citep{agrawal2024ai,si2024llmideas}, the question of what to work on will become both more tractable and more consequential. If downstream research tasks become cheap, the remaining scarce input is upstream judgment about which questions deserve attention. The natural extensions are concrete: incorporating researcher expertise to model who is positioned to pursue which questions \citep{sourati2023accelerating}, combining graph structure with LLM-generated natural-language hypotheses \citep{tong2024automating}, and extending the benchmark to predict not only link appearance but the quality of evidence behind the realizing paper. Each of these would strengthen the bridge between a prospective benchmark and a genuinely useful screening tool.
+
+The contribution here is modest but pointed: a prospectively testable benchmark, a readable surfaced object, and an honest comparison with the strongest version of the cumulative-advantage null. Economics should not decide what to ask next only through popularity. The nearby structure of the literature carries screening information that popularity alone misses, and a researcher browsing a realistic shortlist can use that information. If the results hold under expert evaluation, the same logic may eventually inform how funders, editors, and research groups allocate attention across candidate directions---not by replacing judgment, but by widening the set of questions that reach the judgment stage.
@@ -550 +813 @@ These limits do not make the exercise empty. They define its scope. The paper's
-This appendix documents the paper-local extraction layer used in the paper's evaluation. Garg and Fetzer~\citeyearpar{gargfetzer2025causal} show that economics papers can be converted into paper-level claim graphs by prompting a language model to recover nodes, directional relations, and claim metadata from title-and-abstract text. The present paper inherits that paper-local view of extraction but extends it for a different downstream object. Here the graph must support missing-link construction, gap-versus-boundary distinctions, causal versus noncausal splitting, and later node normalization into a reusable concept ontology. That requires a somewhat richer paper-local schema than a simple causal-claim inventory.
+This appendix documents the paper-local extraction layer used in the evaluation. Garg and Fetzer~\citeyearpar{gargfetzer2025causal} show that economics papers can be converted into paper-level claim graphs by prompting a language model to recover nodes, directional relations, and claim metadata from title-and-abstract text. The present paper inherits that paper-local view but extends it for a different downstream object: a reusable graph that can support missing-link construction, gap-versus-boundary distinctions, causal versus noncausal splitting, and later node normalization.
@@ -559 +822 @@ The benchmark uses a fixed system prompt and a minimal user prompt template. The
-\promptfile{../prompts/frontiergraph_extraction_v2/system_prompt.md}
+  \promptfile{../prompts/frontiergraph_extraction_v2/system_prompt.md}
@@ -562 +825 @@ The benchmark uses a fixed system prompt and a minimal user prompt template. The
-\promptfile{../prompts/frontiergraph_extraction_v2/user_prompt_template.md}
+  \promptfile{../prompts/frontiergraph_extraction_v2/user_prompt_template.md}
@@ -583,5 +846,5 @@ The model returns a paper-local graph with \texttt{nodes} and \texttt{edges}. Th
-  Unit of analysis (\texttt{study\_context.unit\_of\_analysis}) & array of enumerated strings & Explicit unit of analysis linked to the node, if stated. & Keeps sample and scope off the concept label while preserving paper-local context. \\
-  Start year (\texttt{study\_context.start\_year}) & array of integers & Explicit start years if stated. & Preserves local scope without creating separate concept nodes for years. \\
-  End year (\texttt{study\_context.end\_year}) & array of integers & Explicit end years if stated. & Same reason as start year. \\
-  Countries (\texttt{study\_context.countries}) & array of strings & Explicit countries if stated. & Preserves local setting without baking geography into concept identity unless essential. \\
-  Context note (\texttt{study\_context.context\_note}) & string & Residual local scope text such as ``older workers'' or ``rural counties''. & Retains paper-local nuance for audit and display while leaving the node label concept-level. \\
+  Unit of analysis\\(\texttt{study\_context.unit\_of\_analysis}) & array of enumerated strings & Explicit unit of analysis linked to the node, if stated. & Keeps sample and scope off the concept label while preserving paper-local context. \\
+  Start year\\(\texttt{study\_context.start\_year}) & array of integers & Explicit start years if stated. & Preserves local scope without creating separate concept nodes for years. \\
+  End year\\(\texttt{study\_context.end\_year}) & array of integers & Explicit end years if stated. & Same reason as start year. \\
+  Countries\\(\texttt{study\_context.countries}) & array of strings & Explicit countries if stated. & Preserves local setting without baking geography into concept identity unless essential. \\
+  Context note\\(\texttt{study\_context.context\_note}) & string & Residual local scope text such as ``older workers'' or ``rural counties''. & Retains paper-local nuance for audit and display while leaving the node label concept-level. \\
@@ -645 +908,3 @@ The model returns a paper-local graph with \texttt{nodes} and \texttt{edges}. Th
-Node normalization is a major measurement problem in its own right. Paper-local concept strings vary in wording, scope, and granularity. Candidate generation, path counts, and missingness all depend on node identity. So unlike a field-level descriptive exercise, this paper cannot treat node definition as secondary.
+Node normalization is central because candidate generation, path counts, and missingness all depend on node identity. Paper-local concept strings vary in wording, scope, and granularity, so this paper cannot treat node definition as secondary.
+
+\subsection{Why an open-world ontology is needed here}
@@ -647 +912 @@ Node normalization is a major measurement problem in its own right. Paper-local
-\subsection{Why a native ontology is needed here}
+Garg and Fetzer~\citeyearpar{gargfetzer2025causal} use paper-local extracted objects for a different downstream task. The present paper asks a more node-sensitive question. Here the downstream object is a reusable concept graph in which a candidate next paper is a missing link between \emph{specific concepts}. In that setting, concept identity cannot be handled at a broad field level. The benchmark needs to preserve distinctions such as public debt versus public investment, or monetary policy versus energy consumption.
@@ -649 +914 @@ Node normalization is a major measurement problem in its own right. Paper-local
-Garg and Fetzer~\citeyearpar{gargfetzer2025causal} use the extracted paper-level objects for a different downstream task. The present paper asks a more node-sensitive question. Here the downstream object is a reusable concept graph in which a candidate next paper is a missing link between \emph{specific concepts}. In that setting, concept identity cannot be handled at a broad field level. The distinction between public debt and public investment, or between monetary policy and energy consumption, is exactly the distinction the benchmark needs to preserve. The native ontology is therefore best understood as an extension of the earlier paper's extraction logic to a setting in which node identity does much more of the empirical work.
+The difficulty is that the extraction layer and the ontology layer speak slightly different languages. The extraction layer produces paper-local operational phrases such as ``gdp per capita'', ``renewable energy consumption'', or ``financial frictions''. The ontology layer, by construction, contains more canonical concept labels. A useful grounding system therefore cannot be binary. If it only keeps exact or near-exact matches, it overselects the cleanest, most standard vocabulary and risks dropping real economics concepts from the graph. If it accepts every nearest neighbor, it introduces false precision. The frozen ontology design used here is therefore \emph{open-world}: it allows exact grounding, broader grounding, lower-confidence candidate bands, and unresolved labels that remain visible for later review rather than disappearing from the graph.
@@ -663,4 +928,4 @@ Garg and Fetzer~\citeyearpar{gargfetzer2025causal} use the extracted paper-level
-    \node[box1] (raw) {\textbf{Paper labels}\\[0.25em]cleaned strings};
-    \node[box2, right=of raw] (heads) {\textbf{Head concepts}\\[0.25em]high-support clusters};
-    \node[box3, right=of heads] (maps) {\textbf{Tail matching}\\[0.25em]lexical + embedding\\quality bands};
-    \node[box4, right=of maps] (graph) {\textbf{Research graph}\\[0.25em]accepted matches\\tail recovery\\provenance};
+    \node[box1] (raw) {\textbf{Extracted labels}\\[0.25em]paper-local strings\\and surface forms};
+    \node[box2, right=of raw] (heads) {\textbf{Frozen ontology v2.3}\\[0.25em]154{,}359 rows\\with provenance};
+    \node[box3, right=of heads] (maps) {\textbf{Tiered grounding}\\[0.25em]exact passes +\\embedding retrieval};
+    \node[box4, right=of maps] (graph) {\textbf{Open-world grounding}\\[0.25em]reviewed overlay\\freeze pass\\provenance};
@@ -671 +936 @@ Garg and Fetzer~\citeyearpar{gargfetzer2025causal} use the extracted paper-level
-  \fignotes{This figure summarizes the ontology pipeline used in the benchmark. High-support labels are clustered into head concepts, lower-support labels are matched with lexical rules and embedding-based ranking, and unresolved tail labels are recovered with stored provenance and quality bands. The key substantive point is that the fuller force-mapped corpus remains in the graph while mapping source and confidence are preserved.}
+  \fignotes{This figure summarizes the frozen ontology v2.3 grounding pipeline used in the benchmark. Paper-local labels are matched to a structured-source ontology by exact label and surface-form passes first, then by embedding retrieval. Lower-confidence labels are not simply dropped: broader grounding is allowed, reviewed overlay outcomes remain explicit, and unresolved labels remain visible with stored provenance.}
@@ -676 +941 @@ Garg and Fetzer~\citeyearpar{gargfetzer2025causal} use the extracted paper-level
-The ontology build proceeds in stages.
+The ontology build now proceeds in five stages (Figure~\ref{fig:normalization-flow}; Table~\ref{tab:mapping-stages} summarizes each stage).
@@ -678 +943 @@ The ontology build proceeds in stages.
-\paragraph{Head-pool construction.} The pipeline first constructs a head pool from the raw normalized label inventory using coverage and support logic. Labels can enter the head pool because they exceed support thresholds in distinct papers and journals, or because they are needed to cover enough of the observed mass of node instances. The code scores candidate head labels using support in papers, journals, instances, distinct partners, and distinct edge papers.
+\paragraph{Ontology assembly.} The frozen ontology baseline starts from five structured source families rather than from an endogenous head-pool build. JEL provides the controlled economics taxonomy. Wikidata adds identifier-grounded concepts and aliases. OpenAlex topics and keywords add current research vocabulary. An economics-filtered Wikipedia crawl adds fine-grained named concepts, policies, instruments, and episodes that appear in paper-level extraction labels but are absent from the four structured sources. The freeze also carries forward a small reviewed family layer from earlier enrichment work. The resulting v2.3 baseline contains 154{,}359 rows: 129{,}032 Wikipedia rows, 9{,}271 OpenAlex keywords, 8{,}383 Wikidata concepts, 5{,}001 JEL concepts, 1{,}876 OpenAlex topics, and 796 reviewed family rows.
@@ -680 +945 @@ The ontology build proceeds in stages.
-\paragraph{Accepted head concepts.} Selected head labels are then clustered into accepted native concepts. Exact and reviewed same-label constraints are combined with blocked-pair and isolate constraints so that obviously compatible head labels cluster while problematic merges can be prevented. The accepted clusters become concept IDs of the form \texttt{FG3C...}, each with a preferred label and alias set.
+\paragraph{Label inventory and exact grounding.} The extraction corpus contributes 1{,}389{,}907 unique normalized labels from 242{,}595 papers. Mapping begins with exact matches on the extracted label itself and then exact matches on stored surface forms, including stripped parenthetical variants. These deterministic passes solve the easy cases without using embeddings.
@@ -682 +947 @@ The ontology build proceeds in stages.
-\paragraph{Hard mappings.} Labels that are not already accepted heads are next mapped with conservative lexical and embedding-based rules. Exact accepted labels map directly. Otherwise the pipeline checks no-parenthesis signatures, acronym and punctuation signatures, singularized signatures, and a small reviewed embedding layer. These mappings are high-confidence enough to write into the hard mapping tables.
+\paragraph{Embedding retrieval and confidence bands.} Labels that remain unresolved after the exact passes are embedded and searched against the ontology with FAISS nearest-neighbour retrieval. The rank-1, rank-2, and rank-3 ontology candidates are stored for audit. The resulting grounding is tiered rather than binary: \texttt{linked} for scores at or above 0.85, \texttt{soft} for 0.75--0.85, \texttt{candidate} for 0.65--0.75, \texttt{rescue} for 0.50--0.65, and \texttt{unresolved} below 0.50. Across the 1{,}389{,}907 normalized extracted labels, the score-band counts are 92{,}249 linked, 224{,}043 soft, 524{,}551 candidate, 539{,}120 rescue, and 9{,}944 unresolved. At the primary 0.75 threshold, 316{,}292 unique labels and 553{,}015 label occurrences attach directly to ontology concepts before any reviewed open-world layer is applied. Lower-confidence bands are kept visible rather than silently discarded.
@@ -684 +949 @@ The ontology build proceeds in stages.
-\paragraph{Soft mappings.} The remaining labels move to the soft stage. If a label has an embedding and a shortlist of plausible head labels, the pipeline uses shortlist embedding matching. If a shortlist is ambiguous but the label still has an embedding, the pipeline uses a global embedding search over the embedded head inventory. Labels with a unique lexical shortlist but no embedding can also be soft-mapped lexically. Labels that still do not map are written into the pending table.
+\paragraph{Reviewed open-world grounding.} Low-confidence labels are then audited with an overlay-first review pass. That layer keeps broader attachment to an existing concept, alias addition, proposed concept-family promotion, explicit rejection, and unresolved outcomes separate rather than forcing everything into one nearest-neighbour merge. Broader grounding is allowed when the ontology only contains a more general concept. This is intentional. For example, grounding ``gdp per capita'' to the broader concept ``GDP'' can be more informative than dropping the label entirely. Raw labels and raw edges are preserved throughout, so ontology weakness does not mechanically create spurious graph gaps.
@@ -686 +951 @@ The ontology build proceeds in stages.
-\paragraph{Pending labels and tail recovery.} The long unresolved tail matters in this project because dropping unmapped labels changes the candidate universe and can mechanically over-concentrate the benchmark on well-mapped central concepts. The canonical benchmark therefore adds a force-mapped tail recovery stage. Unresolved labels are embedded in batches, matched to the existing head concepts, and written back as \texttt{force\_embedding\_backoff} mappings with stored cosine similarity, runner-up margin, and quality band. This stage is what lets the fuller benchmark retain 230{,}479 mapped papers rather than only the stricter mapped-core subset.
+\paragraph{Freeze pass and reviewed hierarchy.} The conservative v2.3 freeze turns that reviewed grounding work into a stable paper-facing ontology layer. It preserves raw \texttt{label}, \texttt{source}, \texttt{parent\_label}, and \texttt{root\_label} fields, adds paper-facing \texttt{display\_label} cleanup where needed, and records reviewed \texttt{effective\_parent\_*} and \texttt{effective\_root\_*} fields as hierarchy overlays. In the freeze pass, 602 rows receive \texttt{display\_label} cleanup, 22 rows are explicitly treated as allowed broad roots, 4 are marked as ambiguous containers, 13{,}820 rows retain a reviewed effective parent, and only 2 additional strict duplicate merges are accepted. No further intermediate-parent promotion clears the conservative bar. The remaining too-broad backlog is parked explicitly rather than patched silently: 77 cases are acceptable broad roots, 247 remain dirty parent zones, 124 point to a missing standard intermediate, and 279 stay unresolved holdouts.
@@ -696,6 +961,5 @@ The ontology build proceeds in stages.
-    Head pool & Selects high-support labels by coverage and support thresholds. & Defines a stable candidate set from which reusable native concepts can be built. \\
-    Accepted heads & Clusters compatible head labels into native concept IDs. & Creates the ontology's concept inventory. \\
-    Hard mapping & Uses exact, lexical-signature, and reviewed embedding rules. & Resolves easy cases conservatively before any softer inference. \\
-    Soft mapping & Uses shortlist or global embedding matching, plus unique lexical shortlists. & Maps the middle tail without forcing every label immediately. \\
-    Pending labels & Stores unresolved labels and why they failed to map. & Makes the missing tail auditable instead of silently dropping it. \\
-    Force-mapped tail recovery & Assigns unresolved labels to existing head concepts with stored score, margin, and quality band. & Expands benchmark coverage while preserving mapping provenance and confidence. \\
+    Ontology assembly & Combines JEL, Wikidata, OpenAlex topics, OpenAlex keywords, and filtered Wikipedia into one deduplicated concept inventory. & Gives the graph a broad structured concept vocabulary rather than relying on a single taxonomy. \\
+    Exact grounding & Applies exact label, exact surface-form, and stripped-parenthesis matches. & Solves easy cases deterministically before any embedding step. \\
+    Embedding grounding & Uses nearest-neighbour embedding retrieval and stores rank-1 to rank-3 candidates. & Grounds the harder middle of the label distribution while keeping retrieval provenance. \\
+    Reviewed open-world grounding & Keeps broader attachments, alias additions, proposed family rows, explicit rejections, and unresolved outcomes separate. & Prevents the ontology tail from being treated as either fully trusted or silently dropped. \\
+    Freeze pass & Adds \texttt{display\_label} cleanup, reviewed \texttt{effective\_*} hierarchy overlays, and conservative duplicate review while preserving raw fields. & Stabilizes the paper-facing ontology baseline without rewriting source truth. \\
@@ -706 +970 @@ The ontology build proceeds in stages.
-\subsection{Why the force-mapped fuller corpus is now canonical}
+\subsection{Why the raw graph is preserved while the ontology layer stays tiered}
@@ -708 +972 @@ The ontology build proceeds in stages.
-The fuller force-mapped corpus is the canonical benchmark because the alternative was to let mapping quality mechanically determine which literatures count as candidate-generating. That would have overselected the cleanest, most repetitive, and most central concept strings. The force-mapped layer does introduce weaker mappings, which is why provenance and confidence are kept. But that is preferable to treating the well-mapped core as if it were the whole literature. The benchmark therefore uses the fuller graph while keeping mapping source and confidence available for later sensitivity checks.
+The key choice is not to let ontology confidence determine which literatures count as candidate-generating. If low-confidence labels were simply dropped, the benchmark would overselect the cleanest, most repetitive, and most canonical concept strings. It would also risk creating spurious novelty whenever a real but underrepresented concept failed to receive a clean ontology attachment. The solution used here is therefore to preserve the raw extraction graph while treating ontology grounding as a tiered interpretive layer. High-confidence grounded labels can be aggregated immediately. Lower-confidence labels can still receive broader grounding or reviewed unresolved status. The v2.3 freeze then stabilizes the paper-facing ontology layer without pretending the remaining tail has been solved.
@@ -713 +977 @@ The fuller force-mapped corpus is the canonical benchmark because the alternativ
-Table~\ref{tab:corpus-summary} collects the main corpus counts that define the empirical universe. The two most important transitions are from the selected journal papers to papers with extracted edges, and then from raw extracted edges to normalized evaluation links. The latter step is what makes the missing-link benchmark coherent across papers.
+This appendix supports the main benchmark comparison by collecting the sample counts, core benchmark tables, and significance summaries that sit behind Section 5. The aim is to document the benchmark cleanly, not to introduce a second empirical object. Table~\ref{tab:corpus-summary} summarizes the two most important transitions: from selected journal papers to papers with extracted edges, and then from raw extracted edges to normalized evaluation links. The frozen ontology baseline is reported separately in the same table because the ontology inventory and the active benchmark graph are now distinct objects.
@@ -727 +991 @@ Table~\ref{tab:corpus-summary} collects the main corpus counts that define the e
-    Unique concepts in evaluation graph & 6{,}752 \\
+    Frozen ontology baseline concepts & 154{,}359 \\
@@ -735 +999,7 @@ Table~\ref{tab:corpus-summary} collects the main corpus counts that define the e
-The mainline evaluation table is reported in the refreshed benchmark outputs and reproduced in the manuscript build. The important comparative fact is stable even before the longer appendix tables are read: preferential attachment remains stronger at the strict top-100 margin, while the graph score catches up materially as the shortlist grows. The significance tests are paired over common cutoff-year cells, with bootstrap confidence intervals reported for Recall@100 and mean reciprocal rank.
+The stricter \texttt{identified\_causal\_claim} layer is retained as a nested continuity
+benchmark. I do not use it as the refreshed headline task, because it is much sparser than
+the broader \texttt{causal\_claim} anchor used in the main text. But it is still useful as a
+conservative reference object, especially for readers who want continuity with the
+credibility-focused specification. Table~\ref{tab:strict-main-benchmark} reports that
+continuity benchmark, and Table~\ref{tab:strict-significance} reports the paired bootstrap
+comparison against preferential attachment on the same stricter layer.
@@ -738 +1008 @@ The mainline evaluation table is reported in the refreshed benchmark outputs and
-  \caption{Strict shortlist benchmark across the four main horizons}
+  \caption{Nested continuity benchmark on the stricter \texttt{identified\_causal\_claim} layer}
@@ -741 +1011 @@ The mainline evaluation table is reported in the refreshed benchmark outputs and
-  \begin{tabular}{lcccc}
+  \begin{tabular}{lccc}
@@ -743 +1013 @@ The mainline evaluation table is reported in the refreshed benchmark outputs and
-    Metric & \(h=3\) & \(h=5\) & \(h=10\) & \(h=15\) \\
+    Metric & \(h=5\) & \(h=10\) & \(h=15\) \\
@@ -745,4 +1015,4 @@ The mainline evaluation table is reported in the refreshed benchmark outputs and
-    Recall@100, graph-based score & 0.003239 & 0.002518 & 0.001956 & 0.001494 \\
-    Recall@100, preferential attachment & 0.003826 & 0.003105 & 0.002784 & 0.002138 \\
-    MRR, graph-based score & 0.000811 & 0.000524 & 0.000334 & 0.000227 \\
-    MRR, preferential attachment & 0.000901 & 0.000637 & 0.000420 & 0.000281 \\
+    Recall@100, graph-based score & 0.002518 & 0.001956 & 0.001494 \\
+    Recall@100, preferential attachment & 0.003105 & 0.002784 & 0.002138 \\
+    MRR, graph-based score & 0.000524 & 0.000334 & 0.000227 \\
+    MRR, preferential attachment & 0.000637 & 0.000420 & 0.000281 \\
@@ -754 +1024 @@ The mainline evaluation table is reported in the refreshed benchmark outputs and
-  \caption{Paired bootstrap comparison: graph-based score minus preferential attachment}
+  \caption{Paired bootstrap continuity comparison: graph-based score minus preferential attachment}
@@ -757 +1027,244 @@ The mainline evaluation table is reported in the refreshed benchmark outputs and
-  \begin{tabular}{lcccc}
+  \begin{tabular}{lccc}
+    \toprule
+    Quantity & \(h=5\) & \(h=10\) & \(h=15\) \\
+    \midrule
+    \(\Delta\) Recall@100 & $-0.000588$ & $-0.000828$ & $-0.000644$ \\
+    \(p\)-value for \(\Delta\) Recall@100 & 0.064 & $<0.001$ & $<0.001$ \\
+    \(\Delta\) MRR & $-0.000113$ & $-0.000086$ & $-0.000054$ \\
+    \(p\)-value for \(\Delta\) MRR & $<0.001$ & $<0.001$ & $<0.001$ \\
+    \bottomrule
+  \end{tabular}
+\end{table}
+
+\begin{table}[h]
+  \caption{Expanded reranker benchmark on the refreshed headline family}
+  \label{tab:expanded-reranker-benchmark}
+  \centering
+  \small
+  \begin{tabular}{L{0.08\linewidth}L{0.34\linewidth}ccc}
+    \toprule
+    Horizon & Selected reranker & P@100 & Recall@100 & MRR \\
+    \midrule
+    \(h=5\) & \shortstack[l]{\texttt{glm\_logit +}\\ \texttt{family\_aware\_boundary\_gap}\\ (\(\alpha=0.20\), pool \(=5000\))} & 0.105 & 0.1376 & 0.0133 \\
+    \(h=10\) & \shortstack[l]{\texttt{pairwise\_logit +}\\ \texttt{family\_aware\_composition}\\ (\(\alpha=0.10\), pool \(=5000\))} & 0.207 & 0.1391 & 0.0103 \\
+    \(h=15\) & \shortstack[l]{\texttt{glm\_logit + quality}\\ (\(\alpha=0.05\), pool \(=5000\))} & 0.264 & 0.1541 & 0.0116 \\
+    \bottomrule
+  \end{tabular}
+  \fignotes{These are the horizon-specific winners on the main 1990--2015 \texttt{path\_to\_direct} benchmark. Relative to the transparent score, the Recall@100 gain is about 0.052 at \(h=5\), 0.050 at \(h=10\), and 0.070 at \(h=15\). Relative to preferential attachment, the gain is about 0.100, 0.094, and 0.118.}
+\end{table}
+
+Table~\ref{tab:expanded-reranker-benchmark} clarifies the current benchmark object. The main comparison is no longer an undifferentiated missing-link pool. It is the broader \texttt{path\_to\_direct} family on the \texttt{causal\_claim} anchor, with a richer local evidence object and horizon-specific family-aware rerankers. The result is not one universal model. It is a stable shortlist of rerankers that all beat the transparent retrieval layer on the main metrics. The secondary \texttt{direct\_to\_path} family remains part of the design and of the path-development evidence, but I do not fold it into this main reranker table until it has been refreshed to the same non-sampled standard.
+
+\begin{table}[h]
+  \caption{Early and late benchmark cells are different regimes}
+  \label{tab:early-late-regime}
+  \centering
+  \small
+  \begin{tabular}{llccccc}
+    \toprule
+    Horizon & Era & Cutoffs & Mean eval positives & Winner R@100 & Support age & Endpoint recent share \\
+    \midrule
+    \(h=5\) & Early (1990--1995) & 2 & 12.5 & 0.071 & 11.1 & 0.413 \\
+    \(h=5\) & Late (2000--2015) & 4 & 103.0 & 0.171 & 20.6 & 0.314 \\
+    \(h=10\) & Early (1990--1995) & 2 & 32.5 & 0.109 & 11.7 & 0.430 \\
+    \(h=10\) & Late (2000--2015) & 4 & 214.5 & 0.154 & 20.4 & 0.320 \\
+    \(h=15\) & Early (1990--1995) & 2 & 55.5 & 0.174 & 11.5 & 0.435 \\
+    \(h=15\) & Late (2000--2015) & 3 & 268.0 & 0.141 & 18.5 & 0.323 \\
+    \bottomrule
+  \end{tabular}
+  \fignotes{Early means the 1990 and 1995 cutoffs; late means 2000 through 2015 where the horizon is valid. Mean eval positives is the average number of realized positives in the cutoff-year cell. Winner R@100 uses the horizon-specific adopted reranker winner from Table~\ref{tab:expanded-reranker-benchmark}. Support age is the mean support age for the winner's surfaced top-100. Endpoint recent share averages the source and target recent-share measures in that same surfaced top-100. The early cells are smaller and more recent-surge-like.}
+\end{table}
+
+Table~\ref{tab:early-late-regime} makes the timing issue concrete. At every main horizon, the early cells contain far fewer realized positives and the surfaced top-100 draws on much younger support. The endpoint recent-share measures are also systematically higher in the early era. The later benchmark therefore should not be read as the same environment with less noise. It is a different graph regime with thicker and older local structure.
+
+\section{Learned reranker design}
+\label{app:reranker-design}
+
+This appendix documents the learned reranker used in the expanded benchmark comparison. The reranker operates on the same missing-link candidate universe as the transparent graph score. Its purpose is to ask whether graph-derived features, when allowed to reweight rather than held at fixed coefficients, can beat the stronger transparent baselines that the fixed-weight score does not.
+
+\subsection{Benchmark model inventory}
+
+Table~\ref{tab:benchmark-inventory} summarizes each model in the benchmark family.
+
+\begin{table}[h]
+  \caption{Benchmark model inventory}
+  \label{tab:benchmark-inventory}
+  \centering
+  \small
+  \begin{tabular}{L{0.18\linewidth}L{0.36\linewidth}L{0.10\linewidth}L{0.26\linewidth}}
+    \toprule
+    Model & Input signals & Tunable? & Role in the paper \\
+    \midrule
+    Preferential attachment & Source out-degree \(\times\) target in-degree & No & Cumulative-advantage null \\
+    Degree + recency & Endpoint support degree + recent support prominence & No & Stronger transparent baseline \\
+    Directed closure & Path support + mediator count + local closure density & No & Stronger transparent baseline \\
+    Transparent graph score & Path support + gap + motif support \(-\) hub penalty (fixed weights) & No & Interpretable screening layer \\
+    Learned reranker & Up to 34 graph-derived features across 5 nested families & Yes (\(L_2\)) & Strongest graph-based benchmark \\
+    \bottomrule
+  \end{tabular}
+\end{table}
+
+\subsection{Feature families}
+
+The reranker's features are organized into five nested families. Each family adds to the previous, so the complexity gradient is itself interpretable. Table~\ref{tab:feature-families} lists the families and their contents.
+
+\begin{table}[h]
+  \caption{Feature families in the learned reranker}
+  \label{tab:feature-families}
+  \centering
+  \small
+  \begin{tabular}{L{0.15\linewidth}rL{0.60\linewidth}}
+    \toprule
+    Family & Features & What it adds \\
+    \midrule
+    Base & 1 & The transparent graph score itself. \\
+    Structural & 14 & Path support, motif bonus, gap bonus, hub penalty, mediator and motif counts, co-occurrence count and trend, same-field indicator, endpoint degree products for both direct and support subgraphs. \\
+    Dynamic & 21 & Support age, recency of most recent supporting edge, recent-window degree and incident counts for each endpoint, recent-share fractions. \\
+    Composition & 31 & Mean stability, evidence-type diversity, venue diversity, source diversity, and mean field-weighted citation impact at each endpoint and at the pair level. \\
+    Boundary + gap & 34 & Whether the two endpoints sit in different field groups with no co-occurrence, whether the pair has path support despite a missing direct link, and the local closure density around the pair. \\
+    \bottomrule
+  \end{tabular}
+\end{table}
+
+Every feature is computed from the historical graph through year \(t-1\). The reranker sees no paper text, no future edges or degrees, and no author or institutional identity. That constraint is what keeps the exercise a graph-screening benchmark rather than a free-form prediction model.
+
+\subsection{Training design}
+
+The walk-forward panel is constructed as follows. At each cutoff year \(t\), the training corpus contains all edges published through year \(t-1\). The candidate pool is the set of missing directed links at that cutoff. Features are enriched from the training corpus only. The binary label records whether the candidate edge first appears during \([t,\,t+h]\).
+
+At evaluation time, the model is trained on all cutoff-year cells strictly before \(t\) and evaluated on the cell at \(t\). This prevents any information from the evaluation cutoff from entering the training set.
+
+Two model families are tested. The first is a class-balanced logistic regression that produces calibrated probabilities. The second is a pairwise ranking model (RankNet-style) that learns from positive-versus-negative feature differences, optimizing the order of candidates directly. Both use \(L_2\) (ridge) regularization. The regularization strength \(\alpha\) is drawn from \(\{0.01, 0.05, 0.10, 0.20\}\). Features are standardized using training-set statistics before fitting.
+
+\subsection{Best configurations}
+
+On the current main benchmark, the best reranker at \(h=5\) uses the interpretable logistic model with the boundary + gap feature family and \(\alpha=0.20\). The best at \(h=10\) uses the pairwise ranking model with the composition feature family and \(\alpha=0.10\). At \(h=15\), the winning specification shifts to the logistic model with the broader quality feature family and \(\alpha=0.05\). The difference is substantively interpretable. At shorter horizons, the boundary and gap flags---which capture cross-group bridging and path-implied missingness---add the most screening value. At intermediate horizons, evidence-composition features---stability, diversity, and citation impact---matter more. By \(h=15\), the broader sharpness-quality bundle performs best.
+
+\subsection{Single-feature importance}
+
+To understand what drives the reranker, I evaluate each of the 34 features as a standalone ranker in an auxiliary diagnostic run on the same candidate family. This is directly comparable to the single-feature ablation in Gu and Krenn~\citeyearpar{gu2025impact4cast}, who rank 141 features by predictive power in their cross-science knowledge graph. Table~\ref{tab:single-feature-top10} reports the top 10 features by precision@100 in that diagnostic.
+
+\begin{table}[h]
+  \caption{Top 10 single features: the strongest standalone predictor requires directed extraction}
+  \label{tab:single-feature-top10}
+  \centering
+  \small
+  \begin{tabular}{rL{0.18\linewidth}L{0.10\linewidth}ccL{0.18\linewidth}L{0.10\linewidth}cc}
+    \toprule
+    & \multicolumn{4}{c}{\(h=5\)} & \multicolumn{4}{c}{\(h=10\)} \\
+    Rank & Feature & Family & P@100 & Hits & Feature & Family & P@100 & Hits \\
+    \midrule
+    1 & Direct degree product & structural & 0.100 & 10.0 & Target direct in-degree & structural & 0.197 & 19.7 \\
+    2 & Target recent incident count & dynamic & 0.083 & 8.3 & Direct degree product & structural & 0.183 & 18.3 \\
+    3 & Target direct in-degree & structural & 0.082 & 8.2 & Target recent incident count & dynamic & 0.173 & 17.3 \\
+    4 & Path support & structural & 0.075 & 7.5 & Path support & structural & 0.143 & 14.3 \\
+    5 & Hub penalty & structural & 0.075 & 7.5 & Hub penalty & structural & 0.142 & 14.2 \\
+    6 & Co-occurrence count & structural & 0.057 & 5.7 & Co-occurrence count & structural & 0.113 & 11.3 \\
+    7 & Transparent score & base & 0.057 & 5.7 & Transparent score & base & 0.112 & 11.2 \\
+    8 & Motif bonus & structural & 0.048 & 4.8 & Motif bonus & structural & 0.093 & 9.3 \\
+    9 & Motif count & structural & 0.042 & 4.2 & Motif count & structural & 0.088 & 8.8 \\
+   10 & Closure density & boundary + gap & 0.042 & 4.2 & Closure density & boundary + gap & 0.088 & 8.8 \\
+    \bottomrule
+  \end{tabular}
+\end{table}
+
+Three results stand out. First, directed-causal-degree features remain the strongest standalone signals. At \(h=5\), the direct degree product---the product of source causal out-degree and target causal in-degree---reaches 0.100 precision@100, compared with 0.057 for both raw co-occurrence count and the transparent score. At \(h=10\), target causal in-degree leads at 0.197, followed by the direct degree product at 0.183. These are popularity-style signals, but they are computed on the \emph{directed causal subgraph}. They cannot be recovered from undirected co-occurrence alone.
+
+Second, topology features still carry independent screening signal. Path support and the hub penalty rank fourth and fifth at both \(h=5\) and \(h=10\), ahead of raw co-occurrence count and ahead of the transparent score. So the reranker is not just reweighting centrality. Local path structure matters even as a standalone ranking rule.
+
+Third, no single feature matches the full reranker on the same walk-forward benchmark. The value of the reranker is therefore still in the combination. But the single-feature ranking shows clearly that the strongest individual signals are not generic co-occurrence alone; they come from directed causal centrality plus local topology. Figure~\ref{fig:feature-importance-bars} shows the \(h=5\) ranking as a bar chart colored by feature family.
+
+\begin{figure}[h]
+  \caption{Single-feature importance ranking by family (\(h=5\))}
+  \label{fig:feature-importance-bars}
+  \centering
+  \includegraphics[width=0.82\linewidth]{feature_importance_h5_refreshed.png}
+  \fignotes{Each bar shows precision@100 when candidates are ranked by that single feature alone. Color indicates feature family: blue = structural, red = boundary/gap, salmon = composition, light blue = dynamic, gray = base. The top feature (direct degree product) requires the directed causal extraction and cannot be computed from co-occurrence.}
+\end{figure}
+
+\subsection{What the reranker learns}
+
+The single-feature ranking above shows which features carry standalone screening signal. But the raw-feature decomposition remains collinear. In the refreshed diagnostic, the top recent-support and support-degree measures have VIFs between 14 and 32 (Figure~\ref{fig:vif-comparison}), and raw-feature importance rankings vary materially across model families: Spearman rank correlations are 0.28 for logistic versus gradient boosting, 0.39 for logistic versus random forest, and 0.53 for gradient boosting versus random forest. When features overlap that much, Shapley or coefficient credit can move sharply across correlated inputs even when the model's total prediction is stable.
+
+To resolve this, I group the 34 features into nine interpretable families, chosen \emph{a priori} by what each feature measures rather than by statistical clustering: directed causal degree (endpoint degree on the causal subgraph), support degree (broader subgraph), recency (recent activity and incident counts), co-occurrence (paper co-mentions), path/topology (path support, motifs, hub penalty), evidence quality (stability, evidence diversity), impact (FWCI), boundary/gap flags, and field structure.\footnote{The grouping is defined before seeing the decomposition results, which prevents data-snooping. Within each group, the first principal component (PC1) explains 40--81 percent of the variance, confirming the groups are internally coherent. Using PC1 + PC2 does not materially change the ranking of the top families.} I compute the first principal component within each group as a summary score, estimate a logistic reranker on those standardized group scores, and then inspect both group-level coefficient magnitudes and grouped SHAP plots (Figure~\ref{fig:grouped-shap}).
+
+\begin{figure}[h]
+  \caption{Group-level importance after resolving multicollinearity}
+  \label{fig:grouped-shap}
+  \centering
+  \includegraphics[width=0.82\linewidth]{grouped_shap_importance_refreshed.png}
+  \fignotes{Each bar shows the absolute logistic coefficient on the standardized within-group PC1 score, with bootstrap 95\% confidence intervals. The sign annotation shows the coefficient direction. Support degree is largest in magnitude but negative; directed causal degree, recency, and evidence quality are the strongest positive groups. Group-level VIF stays below 5.}
+\end{figure}
+
+Three results stand out. First, the largest coefficient by magnitude is support degree (1.28, bootstrap CI [1.09, 1.51]), but it enters with a \emph{negative} sign. Once directed causal degree is controlled for, broad support-graph popularity hurts rather than helps. The model is learning to separate concepts that are prominent in causal work from concepts that are merely popular overall. Second, the strongest \emph{positive} groups are directed causal degree (0.88, [0.78, 0.99]), recency (0.85, [0.68, 1.02]), and evidence quality (0.59, [0.47, 0.71]). So the reranker loads on a mix of causal centrality, recent activation, and the quality of the underlying evidence base. Third, co-occurrence remains useful (0.37, [0.28, 0.46]), but it is not the whole story. In economics, the central distinction is not simply between more versus less popular concepts. It is whether that centrality lives in the causal graph or only in the broader support graph.
+
+\begin{figure}[h]
+  \caption{Multi-model comparison on grouped feature families}
+  \label{fig:grouped-multi-model}
+  \centering
+  \includegraphics[width=0.92\linewidth]{grouped_multi_model_refreshed.png}
+  \fignotes{Tree-based models rank directed causal degree first. The grouped logistic model instead puts the largest weight on negative support degree, followed by recency and directed causal degree. Rank correlations across grouped models are moderate rather than perfect, but the main families are more legible than in the raw-feature decomposition.}
+\end{figure}
+
+The grouped decomposition improves interpretability more than it delivers a single invariant ranking. The gradient-boosting and random-forest models both rank directed causal degree first, while the grouped logistic model places the largest absolute weight on negative support degree and then on recency and directed causal degree. The grouped rank correlations are 0.30, 0.70, and 0.78 across model pairs: materially better than the raw-feature decomposition for two of the three pairs, but not close to unanimity. The right conclusion is therefore modest. Grouping makes the substantive families readable and reduces collinearity enough for stable sign interpretation, but model family still matters.
+
+\paragraph{Robustness of the grouped decomposition.} Figures~\ref{fig:grouped-beeswarm} and~\ref{fig:grouped-correlation} confirm that the grouping resolves the multicollinearity problem and produces stable, interpretable results.
+
+\begin{figure}[h]
+  \caption{Grouped SHAP beeswarm: direction and heterogeneity of group contributions}
+  \label{fig:grouped-beeswarm}
+  \centering
+  \includegraphics[width=0.82\linewidth]{grouped_beeswarm_refreshed.png}
+  \fignotes{Each dot is one candidate pair. Horizontal position shows the group's SHAP contribution to the prediction; color shows the group's PC1 value (blue = low, red = high). High directed degree, recency, and evidence quality tend to push predictions up. High support degree pushes predictions \emph{down}, confirming the negative coefficient on broad support-graph popularity.}
+\end{figure}
+
+\begin{figure}[h]
+  \caption{Variance inflation factor: before and after feature grouping}
+  \label{fig:vif-comparison}
+  \centering
+  \includegraphics[width=0.92\linewidth]{vif_comparison_refreshed.png}
+  \fignotes{Left: the top raw-feature VIFs range from roughly 14 to 32 for recent-support and support-degree measures, indicating material multicollinearity. Right: after grouping into nine interpretable families, all grouped VIFs fall below 5. The grouping reduces the instability enough for coherent family-level interpretation.}
+\end{figure}
+
+\begin{figure}[h]
+  \caption{Group-level correlation matrix}
+  \label{fig:grouped-correlation}
+  \centering
+  \includegraphics[width=0.72\linewidth]{grouped_correlation_refreshed.png}
+  \fignotes{Pairwise correlations between the nine group-level PC1 scores. The strongest remaining correlation is between support degree and recency (about 0.86), so the grouped features are not orthogonal. But the grouped VIFs remain below 5, which is enough for substantially cleaner interpretation than at the raw-feature level.}
+\end{figure}
+
+\subsection{Failure mode profiles}
+
+To understand what the reranker gets wrong, I compare the feature profiles of its top-100 hits (realized links) and misses (unrealized links), averaged across cutoffs at \(h=5\) (Table~\ref{tab:failure-modes}).
+
+\begin{table}[h]
+  \caption{Reranker top-100 failure mode profiles (\(h=5\), mean across cutoffs)}
+  \label{tab:failure-modes}
+  \centering
+  \begin{tabular}{lrrrrr}
+    \toprule
+    & Hits & Misses & Missed realized \\
+    & (top-100, realized) & (top-100, not realized) & (rank $>$ 500, realized) \\
+    \midrule
+    Count & 18 & 82 & 241 \\
+    Mean co-occurrence & 209 & 103 & 26 \\
+    Mean direct degree product & 3{,}413 & 3{,}288 & 290 \\
+    Mean pair FWCI & 5.35 & 5.55 & 5.71 \\
+    \bottomrule
+  \end{tabular}
+  \fignotes{Hits and misses are from the reranker's top-100 predictions. ``Missed realized'' are links that the reranker ranks below 500 but that do appear within the horizon. Hits have much higher co-occurrence, confirming that the reranker succeeds on well-studied pairs. Missed realized links are in sparse neighborhoods with low degree products---the ``alien'' territory of Sourati et al.~\citeyearpar{sourati2023accelerating} where no model based on existing graph structure is likely to perform well.}
+\end{table}
+
+The pattern is clear. The reranker's successful predictions are concentrated among pairs that already have dense co-occurrence and high directed degree products. The links it misses---those that do realize but rank poorly---sit in sparse neighborhoods where popularity signals are weak and the graph provides little local structure to exploit. Those missed realizations have slightly \emph{higher} endpoint FWCI, suggesting they are structurally surprising connections between reputable concepts rather than noise. This is the natural boundary of any graph-based screen: connections that arise from genuinely new combinations, serendipity, or shifts in methodology are hard to predict from existing structure alone.
+
+\subsection{Temporal generalization}
+\label{app:temporal-generalization}
+
+A natural concern is that the walk-forward reranker may perform well only because all cutoff years were used during model development. To test temporal generalization, I select reranker configurations using only 1990--2005 cutoff cells and then evaluate them on the fully held-out era of 2010--2015, which the model never saw during development or selection. During held-out evaluation, the graph itself is still built using only pre-cutoff evidence, but reranker training is frozen to the pre-2010 schedule.
+
+\begin{table}[h]
+  \caption{Temporal generalization: held-out absolute precision gaps remain large}
+  \label{tab:temporal-generalization}
+  \centering
+  \begin{tabular}{llcccc}
@@ -759 +1272,2 @@ The mainline evaluation table is reported in the refreshed benchmark outputs and
-    Quantity & \(h=3\) & \(h=5\) & \(h=10\) & \(h=15\) \\
+    & & \multicolumn{2}{c}{Precision@100} & \multicolumn{2}{c}{Abs.\ reranker $-$ PA} \\
+    Era & Model & \(h=5\) & \(h=10\) & \(h=5\) & \(h=10\) \\
@@ -761,4 +1275,4 @@ The mainline evaluation table is reported in the refreshed benchmark outputs and
-    \(\Delta\) Recall@100 & $-0.000587$ & $-0.000588$ & $-0.000828$ & $-0.000644$ \\
-    \(p\)-value for \(\Delta\) Recall@100 & 0.740 & 0.064 & $<0.001$ & $<0.001$ \\
-    \(\Delta\) MRR & $-0.000090$ & $-0.000113$ & $-0.000086$ & $-0.000054$ \\
-    \(p\)-value for \(\Delta\) MRR & $<0.001$ & $<0.001$ & $<0.001$ & $<0.001$ \\
+    Train era (1990--2005) & Reranker & 0.053 & 0.133 & $+0.045$ & $+0.113$ \\
+    Train era (1990--2005) & Pref.\ attach.\ & 0.008 & 0.020 & --- & --- \\
+    Held-out era (2010--2015) & Reranker & 0.210 & 0.375 & $+0.175$ & $+0.285$ \\
+    Held-out era (2010--2015) & Pref.\ attach.\ & 0.035 & 0.090 & --- & --- \\
@@ -766,0 +1281 @@ The mainline evaluation table is reported in the refreshed benchmark outputs and
+  \fignotes{At \(h=5\), the train-era winner is \texttt{glm\_logit + family\_aware\_composition} with \(\alpha=0.20\); at \(h=10\), it is \texttt{glm\_logit + quality} with \(\alpha=0.10\). Percent lifts are not reported because the train-era preferential-attachment benchmark is close to zero, which makes relative comparisons unstable. The table therefore reports levels and absolute \(P@100\) gaps. On that scale, the reranker generalizes cleanly forward and retains a larger margin over preferential attachment in the held-out era.}
@@ -768,0 +1284,7 @@ The mainline evaluation table is reported in the refreshed benchmark outputs and
+The result is reassuring, but the right comparison is in levels rather than percentages. Because train-era preferential-attachment precision is very close to zero, percentage lifts are mechanically unstable. In absolute \(P@100\) terms, the reranker still generalizes cleanly forward. At \(h=5\), its gap over preferential attachment rises from \(+0.045\) in the 1990--2005 cells to \(+0.175\) in the held-out 2010--2015 era. At \(h=10\), the gap rises from \(+0.113\) to \(+0.285\). The likely explanation is that the literature graph is thicker in later years, giving the reranker more structure to exploit. But the central conclusion does not depend on that interpretation: the learned graph features do not collapse out of sample when applied to a later era.
+
+\subsection{Regime and horizon extensions}
+\label{app:regime-extensions}
+
+Two appendix-only extensions help interpret the benchmark boundary more concretely. Figure~\ref{fig:regime-split-refresh} asks where the transparent graph score gains the most over preferential attachment once the candidate universe is split by local density and by endpoint FWCI. Figure~\ref{fig:auxiliary-horizon-refresh} extends the transparent benchmark itself to shorter and longer horizons than the paper's main \(5, 10,\) and \(15\)-year design.
+
@@ -770,2 +1292,2 @@ The mainline evaluation table is reported in the refreshed benchmark outputs and
-  \caption{Main horizon comparison with bootstrap confidence intervals}
-  \label{fig:benchmark-ci-appendix}
+  \caption{Regime splits: the transparent score helps more in dense than sparse neighborhoods}
+  \label{fig:regime-split-refresh}
@@ -773,2 +1295,2 @@ The mainline evaluation table is reported in the refreshed benchmark outputs and
-  \includegraphics[width=0.72\linewidth]{ci_recall_at_100.png}
-  \fignotes{This appendix figure reports bootstrap confidence intervals for Recall@100 by model and horizon using the canonical evaluation table. The unit of analysis is the rolling cutoff-year benchmark cell. The confidence bands quantify uncertainty from the small number of pooled cutoffs, not uncertainty over the full universe of possible research questions.}
+  \includegraphics[width=0.92\linewidth]{regime_split_delta_refreshed.png}
+  \fignotes{Each bar reports the transparent score's mean \(P@100\) advantage over preferential attachment on the current `1990--2015` benchmark panel. Left: candidates split by within-cell median co-occurrence density. Right: candidates split by within-cell median pair FWCI. The refreshed result is not that the graph helps most where the literature is thinnest. Its edge is largest in denser local neighborhoods, and it is relatively larger in lower-FWCI slices than in the highest-FWCI ones.}
@@ -777 +1299,7 @@ The mainline evaluation table is reported in the refreshed benchmark outputs and
-The candidate-kind split also matters for interpretation. The direct benchmark is carried mainly by the directed causal task. The undirected contextual task is substantively useful for the fuller graph and for the heterogeneity atlas, but it contributes much less to strict top-100 shortlists because contextual relations are far more diffuse. That is why the main text can focus on directed causal emergence without pretending that the undirected structure is unimportant.
+\begin{figure}[h]
+  \caption{Auxiliary horizons: the transparent benchmark scales with horizon but remains a retrieval layer}
+  \label{fig:auxiliary-horizon-refresh}
+  \centering
+  \includegraphics[width=0.92\linewidth]{auxiliary_horizon_comparison_refreshed.png}
+  \fignotes{This appendix-only display uses the already-refreshed retrieval-budget run on the effective corpus and a fixed pool of 5{,}000 candidates. As the horizon lengthens, the transparent score's top-100 hit rate rises because many more future links become eligible realizations. But top-100 recall remains tiny at every horizon, while the pool recall ceiling stays well above the visible shortlist yield. That is why the paper treats the transparent score as a retrieval layer and then studies reranking and attention budgets separately.}
+\end{figure}
@@ -779 +1307 @@ The candidate-kind split also matters for interpretation. The direct benchmark i
-\section{Heterogeneity atlas extensions}
+\section{Heterogeneity appendix figures}
@@ -782 +1310 @@ The candidate-kind split also matters for interpretation. The direct benchmark i
-The full heterogeneity atlas reports pooled and kind-split results over 5-year cutoffs, fixed-\(K\) and percentile-\(K\) frontiers, and a wider horizon set out to 20 years. The main text uses only the most interpretable cuts. The appendix records the rest so that the paper does not overclaim from one pooled average.
+The refreshed appendix keeps only the heterogeneity displays that have been rebuilt on the current historical benchmark panel. The main text uses the overall frontier and method-family split. This appendix adds the time-period heatmap and the funding-by-source interaction.
@@ -785,2 +1313,2 @@ The full heterogeneity atlas reports pooled and kind-split results over 5-year c
-  \caption{Time-period heterogeneity in the pooled frontier comparison}
-  \label{fig:time-heatmap}
+  \caption{Corpus and graph growth: 242{,}595 papers, 1976--2026}
+  \label{fig:corpus-growth}
@@ -788,2 +1316,2 @@ The full heterogeneity atlas reports pooled and kind-split results over 5-year c
-  \includegraphics[width=0.88\linewidth]{time_period_heatmap_main.png}
-  \fignotes{Rows correspond to cutoff-period bins and columns to horizons. Cell color reports the pooled percentile-frontier advantage of the graph score over preferential attachment. The annotations report the strict top-100 delta. The figure shows that the pooled frontier view remains more favorable than the top-100 view across much of the time dimension, but the advantage attenuates at longer horizons.}
+  \includegraphics[width=0.88\linewidth]{corpus_growth.png}
+  \fignotes{Panel A: papers per year in the selected journal corpus. Panel B: cumulative concept vocabulary growth. Panel C: cumulative edge growth by type (directed causal in blue, undirected contextual in gray). Panel D: causal edge share over time, reflecting the credibility revolution in economics---the share of directed causal edges rises from under 4\% in the early corpus to over 10\% by the 2020s.}
@@ -793,2 +1321,2 @@ The full heterogeneity atlas reports pooled and kind-split results over 5-year c
-  \caption{Funding and journal-tier interactions}
-  \label{fig:funding-source}
+  \caption{Time-period heterogeneity in the refreshed benchmark-panel frontier}
+  \label{fig:time-heatmap}
@@ -796,2 +1324,2 @@ The full heterogeneity atlas reports pooled and kind-split results over 5-year c
-  \includegraphics[width=0.88\linewidth]{funding_source_interaction_main.png}
-  \fignotes{This interaction view combines funding status and journal tier. The main text uses funding cautiously because coverage is uneven and because the resulting cells mix institutional composition with scientific behavior. The figure is still useful because it shows that several of the most popularity-dominated cells are funded-journal combinations rather than an undifferentiated funded literature.}
+  \includegraphics[width=0.88\linewidth]{time_period_heatmap_main_refreshed.png}
+  \fignotes{Rows correspond to cutoff-period bins and columns to horizons. Cell color reports the broader-frontier advantage of the graph score over preferential attachment on the refreshed benchmark panel. The annotations report the strict top-100 recall gap. The strongest frontier advantage appears in the 2000s cells; the 1990s are thinner and more uneven, while the 2010s remain positive but smaller.}
@@ -801,2 +1329,2 @@ The full heterogeneity atlas reports pooled and kind-split results over 5-year c
-  \caption{Stable top-funder extensions}
-  \label{fig:top-funders}
+  \caption{Funding and journal-tier interactions}
+  \label{fig:funding-source}
@@ -804,2 +1332,2 @@ The full heterogeneity atlas reports pooled and kind-split results over 5-year c
-  \includegraphics[width=0.88\linewidth]{top_funder_heatmap_appendix.png}
-  \fignotes{Only high-support funders are shown. The stable set requires at least 800 future edges and at least three eligible cutoff cells across the main horizons. In the present atlas that keeps the Economic and Social Research Council, the National Natural Science Foundation of China, the Deutsche Forschungsgemeinschaft, and the U.S. National Science Foundation. The figure is an appendix result because funder-level interpretation mixes institution, geography, topic composition, and metadata coverage.}
+  \includegraphics[width=0.88\linewidth]{funding_source_interaction_main_refreshed.png}
+  \fignotes{This interaction view combines funding status and journal tier on the refreshed benchmark panel. The main message is not that funding has one stable sign. It is that the strongest positive cells are unfunded-adjacent slices, while funded-core slices are the most popularity-dominated. Because the funded cells are thinner and composition-sensitive, the paper treats this figure as suggestive rather than central.}
@@ -811 +1339 @@ The full heterogeneity atlas reports pooled and kind-split results over 5-year c
-The main score does not yet fully weight evidence quality, but the benchmark object is not blind to it either. The extraction layer already records stability, causal presentation, evidence type, and related claim metadata. The tables below should therefore be read as a quality audit of the empirical object rather than as a replacement ranking model. They show that directed causal rows are a smaller but relatively high-stability slice of the graph, that design-heavy method families remain well represented inside that slice, and that the current benchmark is not built from unstructured co-occurrence counts.
+The main score does not yet fully weight evidence quality, but the benchmark object is not blind to it either. The extraction layer already records stability, causal presentation, evidence type, and related claim metadata. Tables~\ref{tab:credibility-edge-kind}, \ref{tab:credibility-by-evidence-type}, and~\ref{tab:credibility-stability-band} should therefore be read as a quality audit of the empirical object rather than as a replacement ranking model. They show that directed causal rows are a smaller but relatively high-stability slice of the graph, that design-heavy method families remain well represented inside that slice, and that the current benchmark is not built from unstructured co-occurrence counts.
@@ -813 +1341,45 @@ The main score does not yet fully weight evidence quality, but the benchmark obj
-\input{../outputs/paper/14_title_revision/credibility_appendix_tables.tex}
+\begin{table}[h]
+  \caption{Credibility audit by edge kind}
+  \label{tab:credibility-edge-kind}
+  \centering
+  \begin{tabular}{lrrrr}
+    \toprule
+    Edge kind & Rows & Papers & Mean stability & Explicit-causal share \\
+    \midrule
+    Directed causal & 89{,}737 & 23{,}213 & 0.930 & 69.0\% \\
+    Undirected contextual & 1{,}181{,}277 & 221{,}192 & 0.868 & 45.3\% \\
+    \bottomrule
+  \end{tabular}
+\end{table}
+
+\begin{table}[h]
+  \caption{Directed-causal credibility audit by evidence type}
+  \label{tab:credibility-by-evidence-type}
+  \centering
+  \begin{tabular}{lrrr}
+    \toprule
+    Evidence type & Rows & Mean stability & Explicit-causal share \\
+    \midrule
+    Panel FE / TWFE & 44{,}106 & 0.938 & 68.8\% \\
+    Difference-in-differences & 16{,}658 & 0.933 & 75.1\% \\
+    Experiment & 15{,}616 & 0.900 & 56.7\% \\
+    Event study & 6{,}247 & 0.940 & 73.5\% \\
+    Instrumental variables & 5{,}601 & 0.933 & 78.3\% \\
+    Regression discontinuity & 1{,}509 & 0.922 & 80.3\% \\
+    \bottomrule
+  \end{tabular}
+\end{table}
+
+\begin{table}[h]
+  \caption{Stability-band split by edge kind}
+  \label{tab:credibility-stability-band}
+  \centering
+  \begin{tabular}{lrrr}
+    \toprule
+    Edge kind & High stability & Mid stability & Low stability \\
+    \midrule
+    Directed causal & 91.8\% & 5.6\% & 2.6\% \\
+    Undirected contextual & 85.4\% & 5.1\% & 9.5\% \\
+    \bottomrule
+  \end{tabular}
+\end{table}
@@ -818 +1390,29 @@ The main score does not yet fully weight evidence quality, but the benchmark obj
-The main text focuses on the aggregate transition comparison, the journal split, the broad economics-versus-finance contrast, and a short table of path-rich examples. The appendix therefore only keeps the supplementary interpretation notes.
+The main text keeps only one curated table of surfaced examples so that the benchmark hierarchy stays visible. This appendix adds a short reserve table of additional examples chosen to avoid thematic repetition (Table~\ref{tab:reserve-examples-appendix}). Each row comes from a distinct source-target neighborhood, and only one additional CO\(_2\)-centered example is allowed.
+
+\begin{table}[h]
+  \caption{Reserve surfaced examples for the appendix}
+  \label{tab:reserve-examples-appendix}
+  \centering
+  \small
+  \begin{tabular}{L{0.20\linewidth}L{0.19\linewidth}L{0.35\linewidth}L{0.18\linewidth}}
+    \toprule
+    Pair & Surface family & Surfaced question & Why it is kept in reserve \\
+    \midrule
+    Tariffs \(\rightarrow\) CO\(_2\) emissions & Baseline path question & What nearby pathways could connect tariffs to CO\(_2\) emissions? & Trade-and-environment baseline from a distinct neighborhood. \\
+    Digital economy \(\rightarrow\) energy intensity & Baseline path question & What nearby pathways could connect digital economy to energy intensity? & Innovation-and-energy example from a separate neighborhood. \\
+    Renewable energy \(\rightarrow\) willingness to pay & Baseline mechanism question & Which mechanisms most plausibly connect renewable energy to willingness to pay? & Compact mechanism example outside the main overlay set. \\
+    Industrial structure \(\rightarrow\) technological innovation & Baseline path question & What nearby pathways could connect industrial structure to technological innovation? & Structural-transformation example without reusing suppressed headline rows. \\
+    \bottomrule
+  \end{tabular}
+\end{table}
+
+These reserve examples are not meant to compete with the four main-text examples. They simply show a bit more of the surfaced shortlist after curation while the main text keeps the benchmark hierarchy visible.
+
+\section{Supplementary current-usefulness validation}
+\label{app:current-usefulness}
+
+These checks ask a different question from the historical benchmark. The benchmark itself remains prospective and vintage-respecting: freeze the graph at \(t{-}1\), rank candidates, and check which ones later appear. The supplementary usefulness checks instead ask whether the surfaced object reads as a useful and intelligible research question to a current reader. They therefore speak to presentation quality and semantic coherence, not to historical forecasting.
+
+The human exercise uses a small blinded pack built from the refreshed \texttt{path\_to\_direct} frontier. It compares 12 graph-selected items with 12 preferential-attachment-selected items drawn from the same candidate universe, with repeated sources and targets capped within arm so the exercise does not collapse into a single crowded endpoint neighborhood. Each item is shown as a raw triplet plus a short construction note, and raters score readability, interpretability, usefulness, and artifact risk. Here readability is intentionally narrow: it measures whether the labels are clean and easy to parse, not whether the underlying idea is substantively better. On this 24-item pack, the overall mean score is identical across arms at 3.22. Graph-selected items score somewhat higher on interpretability (3.17 versus 2.92), slightly higher on usefulness (3.00 versus 2.92), and slightly lower on artifact risk (1.58 versus 1.67), while preferential-attachment items score higher on readability (3.83 versus 3.50). The right reading is therefore cautious external validation, not a broad human-rated advantage.
+
+The appendix LLM usefulness sweep applies the same current-usefulness object on a much larger grid. The model sees only a raw triplet \(A \rightarrow B \rightarrow C\) plus a short construction note explaining that the middle node is an intervening concept from the literature graph; it may represent a mechanism, channel, condition, policy lever, or other bridge. It is explicitly instructed not to judge novelty at the cutoff, likely future success, or topic importance. On the full 1990--2015 grid, using 17 exercises, top-250 shortlists, and three arms (adopted, transparent, and preferential attachment), the pooled ordering is adopted \(>\) transparent \(>\) preferential attachment on this current-usefulness rubric. But the comparison is era-sensitive: in the early era the transparent objects can look slightly cleaner than adopted ones, whereas in the later era adopted clearly looks better. For that reason, the LLM exercise is reported only as supplementary appendix evidence and not as part of the main historical benchmark.
```
