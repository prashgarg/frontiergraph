type HowItWorksQuestion = {
  question: string;
  answerHtml: string[];
};

type HowItWorksTheme = {
  id: string;
  eyebrow: string;
  title: string;
  intro: string;
  questions: HowItWorksQuestion[];
};

export function buildHowItWorksContent(appUrl: string): {
  foundationHtml: string[];
  railItems: string[];
  themes: HowItWorksTheme[];
} {
  return {
    foundationHtml: [
      `FrontierGraph builds on the paper-level claim-graph extraction method introduced in <a href="https://arxiv.org/abs/2501.06873"><em>Causal Claims in Economics</em></a> and the project site <a href="https://www.causal.claims/">causal.claims</a>.`,
      `That foundational work is about extracting paper-local structure from economics papers. FrontierGraph is a separate product layer that uses a public corpus, a ranking layer, and public cleanup rules to surface candidate research questions.`,
    ],
    railItems: [
      "Not a causal estimate",
      "Not a literature review",
      "Not a policy recommendation",
      "Not proof that a question is truly open everywhere",
    ],
    themes: [
      {
        id: "what-it-is",
        eyebrow: "Start here",
        title: "What FrontierGraph is",
        intro: "Use this page to understand what FrontierGraph is trying to do before you decide whether one surfaced question is worth following.",
        questions: [
          {
            question: "What is FrontierGraph actually surfacing?",
            answerHtml: [
              "It surfaces candidate research questions that look open enough to investigate and grounded enough to read seriously. The product is trying to help a researcher decide what might become the next paper, not to declare what the field must do.",
            ],
          },
          {
            question: "What does this help me do in practice?",
            answerHtml: [
              "It helps you move from a broad area to a smaller question that looks worth reading, scoping, or testing next. That is a discovery aid, not a promise that the question is important in every substantive sense.",
            ],
          },
          {
            question: "What is FrontierGraph not?",
            answerHtml: [
              "It is not a causal estimate, not a literature review, and not a truth machine. It helps you notice candidate questions faster, then asks you to verify them yourself.",
            ],
          },
        ],
      },
      {
        id: "read-a-card",
        eyebrow: "Reading guide",
        title: "How to read a research question card",
        intro: "The public cards are intentionally simple. They are meant to help you decide whether to keep reading, not to replace the reading.",
        questions: [
          {
            question: "Does a question title imply causal direction?",
            answerHtml: [
              "Not by itself. The curated front cards use editorial question wording, while the ranked list uses neutral pair wording so storage order does not get mistaken for a causal claim.",
            ],
          },
          {
            question: "What does \"No direct papers yet\" mean?",
            answerHtml: [
              "It means the current public sample does not show direct papers linking the pair in the surfaced form. It does not mean the question has never been studied under synonyms, neighboring labels, or outside the current build.",
            ],
          },
          {
            question: "What does \"Why this question\" show?",
            answerHtml: [
              "It shows the related ideas, papers to start with, exact-question status, and common contexts behind the surfaced question. The goal is to give you enough reason structure to decide whether to investigate further.",
            ],
          },
        ],
      },
      {
        id: "evidence",
        eyebrow: "Trust",
        title: "What sits behind a surfaced question",
        intro: "The product is not just semantic similarity, but it is also not fully automatic proof that a question matters.",
        questions: [
          {
            question: "Is this just embeddings or semantic similarity?",
            answerHtml: [
              "No. The extraction foundation comes from paper-local structure, and the downstream ranking and public cleanup layers are deterministic, inspectable steps built on top of that extracted structure.",
            ],
          },
          {
            question: "What is model-extracted, and what is deterministic?",
            answerHtml: [
              "The model-extracted layer is the paper-level structure recovered from text. Ranking, ontology comparison, duplicate suppression, and the public cleanup steps are deterministic once that extracted layer is fixed.",
            ],
          },
          {
            question: "What should I do after opening one card?",
            answerHtml: [
              `Check close synonyms, read the papers to start with, inspect the related ideas, and decide whether the question looks like a mechanism, outcome, or setting question. If you want the deeper inspection layer, use <a href="${appUrl}">Inspect evidence</a>.`,
            ],
          },
        ],
      },
      {
        id: "limits",
        eyebrow: "Limits",
        title: "What the current public build can miss",
        intro: "The right way to use FrontierGraph is with useful skepticism. It can save time, but it can also miss things or overstate how open a question really is.",
        questions: [
          {
            question: "Why title and abstract?",
            answerHtml: [
              "Title and abstract are where framing, outcomes, mechanisms, and central nouns are most consistently available at scale. The tradeoff is that FrontierGraph sees much less of the identification strategy, robustness discussion, and full-paper nuance.",
            ],
          },
          {
            question: "Can dense literatures be favored?",
            answerHtml: [
              "Yes. Better-covered areas often generate richer surrounding structure, which can make them easier to surface cleanly than very new or very sparse areas.",
            ],
          },
          {
            question: "Can genuinely new ideas be missed or bad links be surfaced?",
            answerHtml: [
              "Yes to both. Sparse new topics can be under-seen, and structurally nearby ideas can still be substantively weak once you read the papers closely.",
            ],
          },
        ],
      },
      {
        id: "under-the-hood",
        eyebrow: "Under the hood",
        title: "Where the technical terms live",
        intro: "Most users do not need the technical glossary on first contact. It is still available when you want exact terms rather than public summaries.",
        questions: [
          {
            question: "Why is Baseline exploratory the default?",
            answerHtml: [
              "Baseline exploratory is the public discovery regime because it keeps the visible surface broad enough to browse without making the public product too dense. It is a navigation choice, not a claim that this ontology layer is final truth.",
            ],
          },
          {
            question: "What is duplicate suppression?",
            answerHtml: [
              "Duplicate suppression is a public cleanup layer that removes near-synonym loops from the visible ranking slice. It is a product decision meant to make the public list less repetitive, not a claim about final ontology truth.",
            ],
          },
          {
            question: "Where do path support, motif completion, and the other exact terms live?",
            answerHtml: [
              `They stay on <a href="/method/">Method</a>, which is the exact glossary for the technical layer. Use this page to interpret the product, and Method when you want the precise scoring language.`,
            ],
          },
        ],
      },
    ],
  };
}
