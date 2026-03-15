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
    kindLabel: "Direct -> path result",
    questionTitle: "The literature often deepens a direct claim before it closes a missing one.",
    why: "In the paper, direct-to-path transitions are much more common than path-to-direct transitions. Researchers often add mechanisms around an existing claim first.",
    detailPrefix: "See:",
    detail: "The path-evolution result in the paper, then use the app to inspect mediator structure around one topic.",
    primaryLabel: "Read result",
    primaryHref: "/paper/#53-path-evolution-beyond-direct-link-closure",
  },
  {
    pairKey: "FG3C000014__FG3C000024",
    diagramVariant: "candidateMonetary",
    kindLabel: "Path-rich question",
    questionTitle: "Does monetary policy have an energy-demand channel?",
    why: "Rate shocks already move housing, durables, and industrial borrowing. Energy demand is often nearby in the graph but not the main outcome.",
    detailPrefix: "Start with:",
    detail: "Follow policy shocks through construction, durables, and sector energy use.",
  },
];
