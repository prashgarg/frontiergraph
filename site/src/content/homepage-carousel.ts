export interface HomepageCarouselSlide {
  pairKey: string;
  sourceLabel: string;
  targetLabel: string;
  mediatorLabels: string[];
  questionTitle: string;
  why: string;
  how: string;
}

export const homepageCarouselSlides: HomepageCarouselSlide[] = [
  {
    pairKey: "FG3C000003__FG3C000208",
    sourceLabel: "public debt",
    targetLabel: "CO2 emissions",
    mediatorLabels: ["fiscal space", "public investment", "energy pricing"],
    questionTitle: "How does public debt shape CO2 emissions?",
    why: "Debt shocks can reshape state capacity, infrastructure spending, and energy policy, but those channels are rarely studied together as an emissions question.",
    how: "Start with debt stress, austerity, or refinancing episodes and track investment, energy use, and emissions after them.",
  },
  {
    pairKey: "FG3C000014__FG3C000024",
    sourceLabel: "monetary policy",
    targetLabel: "energy consumption",
    mediatorLabels: ["durables demand", "construction", "industrial borrowing"],
    questionTitle: "Does monetary policy have an energy-demand channel?",
    why: "Rate shocks clearly move spending and production, but energy demand is rarely the main outcome in monetary papers.",
    how: "Trace policy shocks through housing, durables, and sector energy use instead of stopping at output and inflation.",
  },
  {
    pairKey: "FG3C000012__FG3C000110",
    sourceLabel: "urbanization",
    targetLabel: "output growth",
    mediatorLabels: ["agglomeration", "labor reallocation", "infrastructure density"],
    questionTitle: "When does urbanization translate into output growth?",
    why: "Urbanization is central to many development stories, but it is often treated as background change rather than the main growth question.",
    how: "Use regional urban expansion or city concentration changes to test when denser settlement begins to raise output growth.",
  },
  {
    pairKey: "FG3C000029__FG3C000194",
    sourceLabel: "education",
    targetLabel: "wage inequality",
    mediatorLabels: ["skill premium", "labor sorting", "educational expansion"],
    questionTitle: "How does education reshape wage inequality?",
    why: "Education is central to human-capital debates, but its role in wage dispersion is often treated descriptively rather than as the main question.",
    how: "Compare expansions in schooling access or attainment with later changes in within-cohort wage dispersion.",
  },
];
