export interface FaqQuestion {
  question: string;
  answerHtml: string[];
}

export interface FaqTheme {
  id: string;
  eyebrow: string;
  title: string;
  intro: string;
  questions: FaqQuestion[];
}

export interface FaqContent {
  foundationTitle: string;
  foundationHtml: string[];
  railTitle: string;
  railItems: string[];
  themes: FaqTheme[];
}

interface BuildFaqContentOptions {
  appUrl: string;
  defaultRegime: string;
  generatedAtLabel: string;
}

export function buildFaqContent({ appUrl, defaultRegime, generatedAtLabel }: BuildFaqContentOptions): FaqContent {
  return {
    foundationTitle: "The extraction foundation behind FrontierGraph",
    foundationHtml: [
      `FrontierGraph builds on the paper-level claim-graph extraction approach introduced in <a href="https://arxiv.org/abs/2501.06873"><em>Causal Claims in Economics</em></a> by Prashant Garg and Thierry Fetzer, and on the project website <a href="https://www.causal.claims/">causal.claims</a>. That foundation is about extracting structured claim graphs from economics papers.`,
      `The live FrontierGraph public product is a separate surface built on top of that idea. It uses its own public corpus choice, ontology regimes, ranking layer, duplicate suppression, and product-facing curation decisions.`,
    ],
    railTitle: "What FrontierGraph is not",
    railItems: [
      "Not a causal estimate or identification strategy on its own.",
      "Not a substitute for reading papers or checking the literature manually.",
      "Not proof that a pair is unexplored everywhere or under every wording.",
      "Not a policy recommendation or a claim that a surfaced pair is true.",
    ],
    themes: [
      {
        id: "what-it-is",
        eyebrow: "Orientation",
        title: "What FrontierGraph is",
        intro: "Start here if you want the shortest honest description of the product.",
        questions: [
          {
            question: "What is FrontierGraph actually surfacing?",
            answerHtml: [
              "FrontierGraph surfaces concept pairs that look structurally under-connected relative to the surrounding published-paper graph. In practice, it is trying to show plausible next research directions rather than settled findings or final judgments about importance.",
            ],
          },
          {
            question: "What does “Where do we go next?” mean here?",
            answerHtml: [
              "It means: given the literature that is already visible, where does the graph suggest a promising next question or missing connection. That is a discovery prompt, not a claim that the system knows the single best next paper to write.",
            ],
          },
          {
            question: "What is FrontierGraph not?",
            answerHtml: [
              "It is not a causal claim, a literature review, a truth adjudicator, or a policy recommendation. It is a structured discovery surface that helps you decide what to inspect next and then verify for yourself.",
            ],
          },
        ],
      },
      {
        id: "paper-foundation",
        eyebrow: "Foundation",
        title: "How FrontierGraph relates to the paper",
        intro: "This is where the connection to the underlying research method is made explicit.",
        questions: [
          {
            question: "How is this related to Causal Claims in Economics?",
            answerHtml: [
              `The extraction foundation comes from <a href="https://arxiv.org/abs/2501.06873"><em>Causal Claims in Economics</em></a> and the related project site <a href="https://www.causal.claims/">causal.claims</a>. That work introduced the paper-level graph extraction approach that FrontierGraph builds on.`,
              "FrontierGraph is not just a public copy of that paper or website. It adds a different public corpus, ontology comparison, underexplored-link ranking, duplicate suppression, and a product layer focused on surfacing next-step research questions.",
            ],
          },
          {
            question: "What comes from the paper-level extraction method, and what is new here?",
            answerHtml: [
              "What carries over is the idea of extracting structured graph information from economics papers rather than treating the corpus as unstructured text. What is new here is the public concept surface, the Baseline exploratory default, the ranking of underexplored links, and the public cleanup layer that makes the surfaced list less repetitive.",
            ],
          },
        ],
      },
      {
        id: "read-a-card",
        eyebrow: "Interpretation",
        title: "How to read an opportunity",
        intro: "These answers are about reading the public cards correctly rather than over-interpreting them.",
        questions: [
          {
            question: "Does a surfaced pair imply causal direction?",
            answerHtml: [
              "No. On the public ranked lists, pairs are shown in neutral wording so storage order does not imply causal direction.",
              "Curated cards sometimes present a question in a more natural order because that reads better for a research prompt, but that is editorial framing rather than a claim that the arrow is known to run one way.",
            ],
          },
          {
            question: "What does “No direct papers yet” mean?",
            answerHtml: [
              "It means the current public corpus does not show direct literature contact for that pair in the surfaced recommendation layer. It does not mean nobody has ever studied the question under any wording, in every field, or outside the current public build.",
            ],
          },
          {
            question: "What does “Why this is surfaced” mean?",
            answerHtml: [
              "It is a short summary of the structural evidence behind the card: nearby linking ideas, the observed direct-literature status, and the study settings most visible around the pair. It is there to make the suggestion inspectable without forcing public users to read raw scoring terms.",
            ],
          },
          {
            question: "What should I do after opening one card?",
            answerHtml: [
              "Treat the card as a starting point for validation, not as a finished idea. Check the nearby concepts, search for direct literature under close synonyms, and decide whether the pair points to a mechanism, outcome, or setting that could support a real paper design.",
              `If it still looks plausible, open the <a href="${appUrl}">app</a> or the <a href="/graph/">graph view</a> for a deeper read and use <a href="/method/">Method</a> only when you need the scoring vocabulary.`,
            ],
          },
        ],
      },
      {
        id: "trust-and-evidence",
        eyebrow: "Trust",
        title: "Trust and evidence",
        intro: "These are the questions skeptical readers usually ask first, and they should.",
        questions: [
          {
            question: "Why should I trust this at all?",
            answerHtml: [
              "You should trust it as a structured discovery aid, not as ground truth. The extraction step is model-based, but the ontology comparison, ranking, and suppression layers after extraction are deterministic and inspectable.",
              `The extraction foundation is documented in <a href="https://arxiv.org/abs/2501.06873"><em>Causal Claims in Economics</em></a>, while the FrontierGraph public product adds its own ranking and cleanup choices on top of that foundation.`,
            ],
          },
          {
            question: "Is this just embeddings or semantic similarity?",
            answerHtml: [
              "No. FrontierGraph is built from extracted paper-local graph structure and then ranked with deterministic graph signals such as path support, gap structure, motif completion, mediator structure, co-occurrence scarcity, and hub penalties.",
              "Semantic overlap still matters indirectly through concept extraction and ontology mapping, but the surfaced list is not just a nearest-neighbor similarity table.",
            ],
          },
          {
            question: "What evidence is actually behind a card?",
            answerHtml: [
              "Each card sits on top of observed concept structure extracted from title and abstract text, plus the surrounding graph evidence that links the two sides. Public cards expose a simplified slice of that evidence through direct-literature status, nearby linking ideas, and visible settings.",
            ],
          },
          {
            question: "What kinds of mistakes should I expect?",
            answerHtml: [
              "Expect three main kinds of error: extraction mistakes, ontology-label mismatches, and missing-literature false negatives. You should also expect some surfaced pairs to be structurally interesting but substantively weak once a human reads the underlying literature.",
            ],
          },
        ],
      },
      {
        id: "data-and-coverage",
        eyebrow: "Coverage",
        title: "Data and coverage",
        intro: "This section is about what the system can and cannot see in the current public build.",
        questions: [
          {
            question: "Which papers are included?",
            answerHtml: [
              "The current public build uses a curated published-paper sample built from the FWCI core150 plus adjacent150 source cut and its merged extraction corpus. That keeps the public surface tied to a defined paper set rather than to an unconstrained scrape.",
            ],
          },
          {
            question: "Why title and abstract?",
            answerHtml: [
              "Because title and abstract text are the most consistently available public layer across a large corpus. That makes the system scalable and inspectable, but it also means FrontierGraph misses detail that only appears in full text, appendices, or robustness sections.",
            ],
          },
          {
            question: "How recent is the public build?",
            answerHtml: [
              `The site is a versioned snapshot, not a live crawl of all new papers. The current public export shown on the site was generated on <strong>${generatedAtLabel}</strong>, so you should treat it as a dated release rather than assume it reflects the very latest literature.`,
            ],
          },
          {
            question: "What gets left out?",
            answerHtml: [
              "Very new topics, thinly abstracted papers, fields with weaker concept standardization, and connections that are obvious only in full text are all easier to miss here. A missing link in FrontierGraph should never be read as proof that the broader literature has no relevant work.",
            ],
          },
        ],
      },
      {
        id: "concepts-and-ontology",
        eyebrow: "Ontology",
        title: "Concepts and ontology",
        intro: "These answers explain why the labels and regimes look the way they do.",
        questions: [
          {
            question: "What is Baseline exploratory?",
            answerHtml: [
              `It is the default public concept regime because it keeps the head concept inventory compact while still preserving broad discovery coverage. In other words, it is a navigation-and-discovery choice, not a claim that this regime is the final truth about concept identity.`,
            ],
          },
          {
            question: "What do Broad and Conservative change?",
            answerHtml: [
              "They change how aggressively concept identity is grouped and mapped. Broad tends to widen concept coverage, Conservative tends to tighten it, and Baseline exploratory sits in the middle as the public default for discovery rather than as the only valid ontology view.",
            ],
          },
          {
            question: "Why do some labels sound unusual?",
            answerHtml: [
              "Because the product is still grounded in an ontology built from the literature rather than rewritten into a purely editorial vocabulary. Public pages now gloss the more awkward labels when needed, but some precise labels remain because replacing them would make the meaning worse rather than better.",
            ],
          },
          {
            question: "Why are similar concepts merged or suppressed?",
            answerHtml: [
              "Because the public surface would otherwise be overwhelmed by near-synonym loops and trivial restatements of the same idea. Duplicate suppression is a product cleanup layer on the public ranking surface, not a claim that the underlying ontology has solved concept identity perfectly.",
            ],
          },
        ],
      },
      {
        id: "limits-and-failure",
        eyebrow: "Limits",
        title: "Limits and failure modes",
        intro: "A useful discovery surface still has biases, and they should be named plainly.",
        questions: [
          {
            question: "Can dense literatures be favored?",
            answerHtml: [
              "Yes. Well-covered neighborhoods can generate richer structural evidence, which makes them easier for the ranker to interpret.",
              "That does not mean dense literatures always dominate the top of the list, but it does mean sparse areas can be harder to score confidently.",
            ],
          },
          {
            question: "Can genuinely new ideas be missed?",
            answerHtml: [
              "Yes. If a topic is very new, poorly standardized, or only weakly visible in titles and abstracts, FrontierGraph may not surface it strongly.",
              "The system is better at spotting structurally incomplete neighborhoods than at predicting entirely unseen conceptual inventions.",
            ],
          },
          {
            question: "Can the graph surface spurious links?",
            answerHtml: [
              "Yes. A pair can look structurally promising even if the underlying literature connection turns out to be shallow, mis-specified, or already well known under different wording.",
            ],
          },
          {
            question: "Are these rankings stable truths?",
            answerHtml: [
              "No. They are release-specific outputs of a particular corpus, ontology regime, extraction layer, and ranking design.",
              `That is why the public default stays fixed at <strong>${defaultRegime}</strong> while <a href="/advanced/">Advanced</a> keeps the comparison surfaces visible for sensitivity checks.`,
            ],
          },
        ],
      },
      {
        id: "using-it-well",
        eyebrow: "Workflow",
        title: "Using the product well",
        intro: "This section is about how to get actual research value from the product.",
        questions: [
          {
            question: "Should I start with Opportunities or Graph?",
            answerHtml: [
              "Start with Opportunities. The graph is best used as an orientation and reading surface after a card or concept already looks interesting.",
            ],
          },
          {
            question: "When should I use the app?",
            answerHtml: [
              `Use the <a href="${appUrl}">app</a> when you want deeper controls, broader search, or a direct pair query that goes beyond the simplified public site. The public pages are intentionally lighter and more editorial.`,
            ],
          },
          {
            question: "How do I turn a surfaced pair into a paper idea?",
            answerHtml: [
              "First decide whether the pair is really a mechanism question, an outcome question, or a setting question. Then check the nearby concepts, search close synonyms manually, and ask whether there is a dataset, empirical design, or reviewable sub-question that makes the pair concrete enough to test.",
            ],
          },
        ],
      },
      {
        id: "technical-terms",
        eyebrow: "Glossary",
        title: "Technical terms when you want them",
        intro: "These are short definitions, not the full technical appendix.",
        questions: [
          {
            question: "What is path support?",
            answerHtml: [
              "Path support means the direct pair is weak or missing, but nearby concepts already connect the two sides through observed graph structure. It is one reason a link can look promising before the direct literature is strong.",
            ],
          },
          {
            question: "What is gap bonus?",
            answerHtml: [
              "Gap bonus means the surrounding neighborhood looks fuller than the direct link itself. In plain terms, it flags cases where the local literature structure looks ahead of the direct pair.",
            ],
          },
          {
            question: "What is motif completion?",
            answerHtml: [
              "Motif completion is a repeated local graph pattern that supports the same missing or weak connection. It is useful for ranking, but it stays off the main public cards because most users do not need the raw term to use the product well.",
            ],
          },
          {
            question: "What is duplicate suppression?",
            answerHtml: [
              "Duplicate suppression is the deterministic cleanup layer that removes or downweights near-synonym loops on the public Baseline exploratory surface. For the fuller glossary and the exact vocabulary, use <a href=\"/method/\">Method</a>.",
            ],
          },
        ],
      },
    ],
  };
}
