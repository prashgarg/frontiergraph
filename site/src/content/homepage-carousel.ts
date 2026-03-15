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
    kindLabel: "Missing direct question",
    questionTitle: "Public debt and CO2 emissions",
    why: "Public debt already sits near public investment, energy pricing, and emissions in the released graph. The missing direct study is the open question.",
    detailPrefix: "One way in:",
    detail: "Track debt stress episodes through public investment, energy policy, and later emissions.",
  },
  {
    diagramVariant: "directToPath",
    kindLabel: "Mechanism-building pattern",
    questionTitle: "Existing direct claims often attract mechanism papers first.",
    why: "One of the paper's main results is that researchers often elaborate channels around an observed direct link before they close a missing direct link implied by a local path.",
    detailPrefix: "Example:",
    detail: "Education to wage inequality often gets mechanism work through the skill premium or labour sorting.",
    primaryLabel: "Read result",
    primaryHref: "/paper/#53-path-evolution-beyond-direct-link-closure",
  },
  {
    pairKey: "FG3C000014__FG3C000024",
    diagramVariant: "candidateMonetary",
    kindLabel: "Path-rich candidate",
    questionTitle: "Monetary policy and energy consumption",
    why: "Policy shocks already link to durables demand, construction, and industrial borrowing. That makes energy use a concrete follow-up question rather than a speculative leap.",
    detailPrefix: "One way in:",
    detail: "Start with housing, durables, or sector borrowing responses, then trace later energy use.",
  },
];
