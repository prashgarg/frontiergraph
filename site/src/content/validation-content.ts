type ValidationSection = {
  id: string;
  title: string;
  intro: string;
  notes: string[];
};

type ValidationContentArgs = {
  generatedAtLabel: string;
};

type ValidationContent = {
  foundationTitle: string;
  foundationHtml: string[];
  railTitle: string;
  railItems: string[];
  sections: ValidationSection[];
};

export function buildValidationContent({ generatedAtLabel }: ValidationContentArgs): ValidationContent {
  return {
    foundationTitle: "What this page is doing",
    foundationHtml: [
      `FrontierGraph builds on the paper-level claim-graph extraction method introduced in <a href="https://arxiv.org/abs/2501.06873"><em>Causal Claims in Economics</em></a> and documented at <a href="https://www.causal.claims/">causal.claims</a>. That foundational layer is about extracting graph structure from paper text.`,
      `The current public FrontierGraph build is a separate product surface. It adds a specific published-paper corpus, ontology regimes, deterministic ranking, duplicate suppression, and a public presentation layer. This page is a limits-and-checks surface, not a leaderboard of benchmark scores.`,
    ],
    railTitle: "Read this page as an audit note",
    railItems: [
      "Some parts are model-extracted and can be wrong.",
      "Some parts are deterministic and inspectable once the graph exists.",
      "This version explains limits and checks; it does not claim a complete public benchmark suite.",
      `The current public data snapshot was generated on ${generatedAtLabel}.`,
    ],
    sections: [
      {
        id: "model-extracted",
        title: "What is model-extracted",
        intro: "The model is used at the paper-local extraction stage, not for the downstream public ranking.",
        notes: [
          "Nodes, edges, local directionality, and paper-local relation structure are extracted from title and abstract text. That means the extraction can miss nuance that appears only in the body of the paper.",
          "If the paper text is ambiguous, compressed, or unusually phrased, the extracted local graph can be incomplete or slightly wrong even when the downstream ranking is deterministic.",
        ],
      },
      {
        id: "deterministic",
        title: "What is deterministic",
        intro: "Once the extracted graph tables exist, the rest of the public pipeline is rule-based and inspectable.",
        notes: [
          "Ontology comparison, public Baseline exploratory selection, path-support-style scoring, duplicate suppression, public label glossing, and curated front-page rendering are deterministic layers on top of the extracted graph.",
          "Deterministic does not mean correct in every case. It means the same inputs produce the same public surface and the cleanup logic can be inspected directly.",
        ],
      },
      {
        id: "checked",
        title: "What has been checked",
        intro: "The current public product is checked more as a product surface than as a benchmark suite.",
        notes: [
          "The public site and app are smoke-tested for broken routes, missing data, visible broken placeholders, and basic evidence rendering.",
          "The public build also checks curated pair validity, glossary references, safe concept defaults, and representative-paper export constraints.",
        ],
      },
      {
        id: "failure-modes",
        title: "Known failure modes",
        intro: "The current system is useful for discovery, but it has predictable ways to fail.",
        notes: [
          "Dense literatures can look easier to connect because they offer more surrounding structure. Sparse or newly emerging topics can be under-surfaced even when they are substantively important.",
          "Near-synonym cleanup improves the public surface, but it is still a product choice. It should not be read as a final scientific claim about true concept identity.",
        ],
      },
      {
        id: "no-direct-papers",
        title: "What “No direct papers yet” means",
        intro: "It means the current public build did not find direct co-occurrence evidence for that pair in the visible public sample and ontology regime.",
        notes: [
          "It does not mean nobody has ever written about the question anywhere. Close synonyms, alternate labels, different corpora, or newer papers can still contain direct work.",
          "The right next step is to check close synonyms, read the nearby linking ideas, and inspect representative papers before treating the pair as genuinely untouched.",
        ],
      },
      {
        id: "not-benchmarked",
        title: "What is not benchmarked yet",
        intro: "This version does not publish a formal public benchmark table for extraction accuracy or opportunity precision.",
        notes: [
          "That is deliberate. This page is meant to state what has been checked and what still needs more formal evaluation, rather than implying a benchmark suite that is not yet exposed on the public site.",
          "For the extraction foundation, read <a href=\"https://arxiv.org/abs/2501.06873\"><em>Causal Claims in Economics</em></a> and <a href=\"https://www.causal.claims/\">causal.claims</a>. For FrontierGraph-specific definitions, use <a href=\"/method/\">Method</a> and <a href=\"/faq/\">FAQ</a>.",
        ],
      },
    ],
  };
}
