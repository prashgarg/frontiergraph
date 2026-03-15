export interface HomepageCarouselSlide {
  pairKey?: string;
  diagramVariant: "candidateDebt" | "directToPath" | "candidateMonetary";
  kindLabel: string;
  questionTitle: string;
  why: string;
  detailPrefix: string;
  detail: string;
  primaryLabel?: string;
  primaryHref?: string;
  secondaryLabel?: string;
  secondaryHref?: string;
}

export const homepageCarouselSlides: HomepageCarouselSlide[] = [
  {
    pairKey: "FG3C000003__FG3C000208",
    diagramVariant: "candidateDebt",
    kindLabel: "Path -> direct question",
    questionTitle: "How does public debt shape CO2 emissions?",
    why: "Observed links already connect debt to emissions through public investment and energy pricing. The missing direct study is the candidate question.",
    detailPrefix: "Start with:",
    detail: "Track debt stress episodes through investment, energy policy, and later emissions.",
  },
  {
    diagramVariant: "directToPath",
    kindLabel: "Direct -> path pattern",
    questionTitle: "A direct claim often gets mechanisms before it gets closed alternatives.",
    why: "The paper shows that researchers more often unpack an existing direct relationship into channels than close a missing direct link implied by a path.",
    detailPrefix: "See:",
    detail: "Open the path-evolution result, then inspect how education links to wage inequality through the skill premium and labour sorting.",
    primaryLabel: "Read result",
    primaryHref: "/paper/#53-path-evolution-beyond-direct-link-closure",
  },
  {
    pairKey: "FG3C000014__FG3C000024",
    diagramVariant: "candidateMonetary",
    kindLabel: "Path-rich candidate",
    questionTitle: "Can monetary policy shift energy demand through real-side channels?",
    why: "Rate shocks already move durables demand, construction, and industrial borrowing. Energy use sits close enough in that neighborhood to make a concrete follow-up question.",
    detailPrefix: "Start with:",
    detail: "Follow policy shocks through housing, durables, and sector energy use before asking for a direct reduced-form link.",
  },
];
