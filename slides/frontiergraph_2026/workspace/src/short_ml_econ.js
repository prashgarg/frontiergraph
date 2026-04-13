const pptxgen = require("pptxgenjs");
const {
  COLORS,
  PAGE,
  makeDeck,
  addSlideBase,
  addFooter,
  addAppendixButton,
  addBackButton,
  addBulletCue,
  addSmallCitations,
  addImagePanel,
  addInfoCard,
  addNetworkBackdrop,
  finalizeSlide,
} = require("./common");

const ROOT =
  "/Users/prashgarg/Library/CloudStorage/Dropbox-PrashantGarg/Prashant Garg/GraphDir";

const ASSETS = {
  extraction: `${ROOT}/paper/mermaid/method_figure_a.png`,
  matching: `${ROOT}/paper/mermaid/method_figure_3_custom.png`,
  anchor: `${ROOT}/paper/mermaid/method_figure_5_custom.png`,
  pairedBenchmark: `${ROOT}/outputs/paper/149_dual_family_main_pairing/dual_family_main_benchmark.png`,
  pathEvolution: `${ROOT}/outputs/paper/138_path_evolution_refresh/figures/path_evolution_comparison.png`,
  currentFrontier: `${ROOT}/outputs/paper/154_dual_family_extension_pairing/dual_family_current_frontier_summary.png`,
  heterogeneity: `${ROOT}/outputs/paper/154_dual_family_extension_pairing/dual_family_heterogeneity_comparison.png`,
  usefulness: `${ROOT}/outputs/paper/164_paired_historical_usefulness_comparison/paired_historical_usefulness_summary.png`,
};

function makeSectionTag(slide, text) {
  slide.addShape("roundRect", {
    x: 0.58,
    y: 1.08,
    w: 1.72,
    h: 0.26,
    rectRadius: 0.03,
    fill: { color: COLORS.blueLight },
    line: { color: COLORS.blue, pt: 0.8 },
  });
  slide.addText(text, {
    x: 0.58,
    y: 1.13,
    w: 1.72,
    h: 0.12,
    align: "center",
    fontSize: 10,
    bold: true,
    color: COLORS.blue,
    margin: 0,
  });
}

async function build() {
  const pptx = makeDeck();
  pptx.title = "What Should Economics Ask Next?";

  const slides = [];

  // 1. Title
  {
    const slide = pptx.addSlide();
    slide.background = { color: COLORS.bg };
    addNetworkBackdrop(slide);
    slide.addText("What Should Economics Ask Next?", {
      x: 0.7,
      y: 1.0,
      w: 7.15,
      h: 0.65,
      fontSize: 22,
      bold: true,
      color: COLORS.ink,
      margin: 0,
    });
    slide.addText("Prashant Garg", {
      x: 0.74,
      y: 1.92,
      w: 2.2,
      h: 0.18,
      fontSize: 13,
      color: COLORS.ink,
      bold: true,
      margin: 0,
    });
    slide.addText("Imperial College London", {
      x: 0.74,
      y: 2.18,
      w: 2.8,
      h: 0.16,
      fontSize: 11,
      color: COLORS.muted,
      margin: 0,
    });
    slide.addText("github.com/prashgarg/frontiergraph", {
      x: 0.74,
      y: 2.42,
      w: 3.6,
      h: 0.16,
      fontSize: 10,
      color: COLORS.blue,
      margin: 0,
      hyperlink: { url: "https://github.com/prashgarg/frontiergraph", tooltip: "Project repository" },
    });
    slide.addText("Economics, machine learning, and metascience", {
      x: 0.74,
      y: 3.05,
      w: 4.45,
      h: 0.18,
      fontSize: 11,
      color: COLORS.muted,
      italic: true,
      margin: 0,
    });
    slide.addShape("roundRect", {
      x: 7.35,
      y: 0.95,
      w: 5.1,
      h: 4.95,
      rectRadius: 0.05,
      fill: { color: "FFF8EE" },
      line: { color: COLORS.border, pt: 1.2 },
    });
    slide.addText("Question choice is the scarce input.", {
      x: 7.78,
      y: 1.35,
      w: 4.2,
      h: 0.25,
      fontSize: 14,
      bold: true,
      color: COLORS.ink,
      margin: 0,
    });
    addBulletCue(slide, 7.8, 1.9, 4.05, [
      "Published work leaves structured gaps.",
      "Some later papers add mechanisms.",
      "Others make direct links explicit.",
      "The graph helps decide what to inspect first.",
    ], { fontSize: 12.5, gap: 0.52, dotColor: COLORS.rust });
    slides.push(slide);
  }

  // 2. Motivation
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Motivation", "Question choice remains weakly formalized");
    addBulletCue(slide, 0.95, 1.72, 10.95, [
      "Choosing what to work on is one of the least formalized decisions in science.",
      "The stock of published work is large, fragmented, and hard to navigate.",
      "Researchers still face a conservative-search bias even when riskier moves matter.",
      "If AI lowers downstream costs, the bottleneck shifts further upstream toward question choice.",
    ], { fontSize: 13.4, gap: 0.74 });
    addSmallCitations(slide, "Jones (2009); Bloom et al. (2020); Foster, Rzhetsky, and Evans (2015)", 1.12, 5.35, 10.4);
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // 3. This paper
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Overview", "This paper");
    addInfoCard(slide, {
      x: 0.82,
      y: 1.55,
      w: 7.2,
      h: 3.4,
      title: "We build and test",
      subtitle: "dated graph + walk-forward evaluation",
      items: [
        "a dated graph from published economics-facing papers",
        "paper-local extraction, then cross-paper matching",
        "still-open questions are ranked at t and checked against later publication",
      ],
      fontSize: 12,
      gap: 0.84,
    });
    addInfoCard(slide, {
      x: 8.35,
      y: 1.55,
      w: 4.18,
      h: 3.4,
      title: "We learn",
      subtitle: "substantive result",
      items: [
        "the graph helps in two distinct historical families",
        "economics more often thickens mechanisms than later states locally implied direct links",
      ],
      fontSize: 11.8,
      gap: 1.0,
      fillColor: "FFF8EE",
    });
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // 4. Two objects
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Empirical object", "Two dated question objects");
    slide.addShape("roundRect", {
      x: 0.78,
      y: 1.35,
      w: 5.7,
      h: 4.25,
      rectRadius: 0.05,
      fill: { color: "FFFDFC" },
      line: { color: COLORS.border, pt: 1.0 },
    });
    slide.addShape("roundRect", {
      x: 6.86,
      y: 1.35,
      w: 5.7,
      h: 4.25,
      rectRadius: 0.05,
      fill: { color: "FFFDFC" },
      line: { color: COLORS.border, pt: 1.0 },
    });
    slide.addText("Direct-to-path", {
      x: 1.02,
      y: 1.72,
      w: 1.6,
      h: 0.16,
      fontSize: 12,
      bold: true,
      color: COLORS.blue,
      margin: 0,
    });
    slide.addText("Path-to-direct", {
      x: 7.08,
      y: 1.72,
      w: 1.7,
      h: 0.16,
      fontSize: 12,
      bold: true,
      color: COLORS.rust,
      margin: 0,
    });
    addBulletCue(slide, 1.02, 2.08, 4.85, [
      "the literature already contains a direct relation",
      "later work adds a clearer mediating path around it",
      "this is the mechanism-thickening object",
    ], { fontSize: 12.2, gap: 0.72, dotColor: COLORS.blue });
    addBulletCue(slide, 7.08, 2.08, 4.85, [
      "the literature already contains nearby support",
      "the direct relation itself is still missing",
      "later work states that direct link explicitly",
    ], { fontSize: 12.2, gap: 0.72, dotColor: COLORS.rust });
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // 5. Method bridge
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Method bridge", "From published papers to dated candidate questions");
    const stages = [
      ["papers", 0.95],
      ["paper-local graphs", 3.25],
      ["shared graph", 5.95],
      ["dated candidates", 8.4],
      ["future realization", 10.95],
    ];
    stages.forEach(([label, x], i) => {
      slide.addShape("roundRect", {
        x,
        y: 2.15,
        w: i === 4 ? 1.45 : 1.9,
        h: 1.2,
        rectRadius: 0.04,
        fill: { color: i < 2 ? "EEF3FB" : "FFF8EE" },
        line: { color: i < 2 ? COLORS.blue : COLORS.border, pt: 1.0 },
      });
      slide.addText(label, {
        x: x + 0.12,
        y: 2.52,
        w: i === 4 ? 1.2 : 1.65,
        h: 0.2,
        fontSize: 14,
        bold: true,
        color: COLORS.ink,
        align: "center",
        margin: 0,
      });
      if (i < stages.length - 1) {
        slide.addShape("chevron", {
          x: x + (i === 4 ? 1.45 : 1.92),
          y: 2.54,
          w: 0.34,
          h: 0.3,
          fill: { color: COLORS.sand },
          line: { color: COLORS.border, pt: 0.6 },
        });
      }
    });
    slide.addText("Freeze the literature at t-1, rank still-open directed questions, then check which later appear during [t, t+h].", {
      x: 1.0,
      y: 4.35,
      w: 11.05,
      h: 0.18,
      fontSize: 12.2,
      color: COLORS.ink,
      align: "center",
      margin: 0,
    });
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // 6. Extraction
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Pipeline", "Each paper becomes a local graph");
    addImagePanel(slide, "One excerpt -> one paper-local graph", ASSETS.extraction, 0.9, 1.42, 11.55, 4.55);
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // 7. Matching
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Pipeline", "Candidate questions only exist after cross-paper matching");
    addImagePanel(slide, "Two paper-local graphs -> one shared candidate neighborhood", ASSETS.matching, 0.85, 1.42, 11.65, 4.6);
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // 8. Benchmark anchor
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Benchmark logic", "The benchmark event is narrower than the surfaced question");
    addImagePanel(slide, "What gets backtested versus what a reader would inspect", ASSETS.anchor, 1.0, 1.46, 11.35, 4.45);
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // 9. Main paired benchmark
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Historical result", "The graph improves on popularity in both families");
    addImagePanel(slide, "Paired short-list benchmark", ASSETS.pairedBenchmark, 0.78, 1.35, 12.0, 4.3);
    addBulletCue(slide, 0.9, 5.86, 12.0, [
      "Direct-to-path yields denser shortlists: more later realizations per 100 suggestions.",
      "Path-to-direct captures a larger share of all later-realized links; reranking improves both.",
    ], { fontSize: 12.2, gap: 0.46, dotColor: COLORS.rust });
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // 10. Substantive takeaway
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Substantive result", "Mechanism thickening is more common than direct closure");
    addImagePanel(slide, "How the two forms of progress compare", ASSETS.pathEvolution, 0.85, 1.45, 11.55, 4.45);
    slide.addText("The literature more often deepens mechanisms around existing claims than later closes locally implied direct links.", {
      x: 1.1,
      y: 6.0,
      w: 11.0,
      h: 0.18,
      fontSize: 12.4,
      bold: true,
      color: COLORS.ink,
      margin: 0,
      align: "center",
    });
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // 11. Surfaced examples now
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Current frontier", "What the graph surfaces now");
    const cards = [
      {
        x: 0.82,
        title: "Direct-to-path",
        subtitle: "known relation, missing mechanism",
        color: COLORS.blue,
        questions: [
          "Could digital financial inclusion support employment through labour matching or market access?",
          "Could tax refunds lift productivity through liquidity and investment?",
          "Could nutrition information shift willingness to pay through health-salience channels?",
        ],
      },
      {
        x: 6.82,
        title: "Path-to-direct",
        subtitle: "nearby support, missing direct relation",
        color: COLORS.rust,
        questions: [
          "Could trade liberalization raise R&D?",
          "Could the digital economy strengthen environmental regulation?",
          "Could renewable energy reshape urbanization?",
        ],
      },
    ];
    cards.forEach((card) => {
      slide.addShape("roundRect", {
        x: card.x,
        y: 1.45,
        w: 5.45,
        h: 4.95,
        rectRadius: 0.05,
        fill: { color: "FFFDFC" },
        line: { color: COLORS.border, pt: 1.0 },
      });
      slide.addText(card.title, {
        x: card.x + 0.28,
        y: 1.72,
        w: 1.7,
        h: 0.16,
        fontSize: 12,
        bold: true,
        color: card.color,
        margin: 0,
      });
      slide.addText(card.subtitle, {
        x: card.x + 0.28,
        y: 1.97,
        w: 2.8,
        h: 0.14,
        fontSize: 10,
        italic: true,
        color: COLORS.muted,
        margin: 0,
      });
      addBulletCue(slide, card.x + 0.28, 2.38, 4.7, card.questions, {
        fontSize: 11.6,
        gap: 0.96,
        dotColor: card.color,
      });
    });
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // 12. Conclusion
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Conclusion", "What we built and learned");
    const items = [
      "built a dated graph from published economics-facing papers",
      "tested two benchmarkable forms of still-open next questions",
      "showed that graph structure helps when reading time is scarce",
      "found that the literature more often thickens mechanisms than it later states locally implied direct links",
    ];
    addBulletCue(slide, 0.9, 1.55, 10.7, items, { fontSize: 13.2, gap: 1.02, dotColor: COLORS.rust });
    slide.addText("Thank you", {
      x: 10.6,
      y: 6.48,
      w: 1.5,
      h: 0.2,
      fontSize: 13,
      color: COLORS.blue,
      bold: true,
      align: "right",
      margin: 0,
    });
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // Appendix 13
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Appendix", "Benchmark detail");
    addImagePanel(slide, "Paired benchmark result", ASSETS.pairedBenchmark, 0.82, 1.42, 12.0, 4.75);
    addFooter(slide, "Appendix detail: paired main benchmark.");
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // Appendix 14
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Appendix", "Method detail");
    addImagePanel(slide, "Extraction and matching", ASSETS.matching, 0.82, 1.35, 5.75, 4.55);
    addImagePanel(slide, "Benchmark anchor versus surfaced question", ASSETS.anchor, 6.75, 1.35, 5.75, 4.55);
    addFooter(slide, "Appendix detail: methodology figures.");
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // Appendix 15
  {
    const slide = pptx.addSlide();
    addSlideBase(slide, "Appendix", "Extra empirical views");
    addImagePanel(slide, "Current frontier summary", ASSETS.currentFrontier, 0.82, 1.3, 5.75, 4.7);
    addImagePanel(slide, "Paired usefulness screen", ASSETS.usefulness, 6.78, 1.3, 5.75, 4.7);
    addFooter(slide, "Appendix detail: surfaced examples and workflow screen.");
    finalizeSlide(slide, pptx);
    slides.push(slide);
  }

  // Navigation buttons
  const mainToAppendix = {
    2: 13,
    3: 13,
    4: 14,
    5: 14,
    6: 14,
    7: 14,
    8: 14,
    9: 13,
    10: 15,
    11: 15,
    12: 13,
  };
  Object.entries(mainToAppendix).forEach(([mainIdx, appendixIdx]) => {
    addAppendixButton(slides[Number(mainIdx) - 1], appendixIdx);
  });
  addBackButton(slides[12], 9);
  addBackButton(slides[13], 6);
  addBackButton(slides[14], 11);

  const out = `${ROOT}/slides/frontiergraph_2026/workspace/frontiergraph_short_ml_econ.pptx`;
  await pptx.writeFile({ fileName: out });
  return out;
}

build().catch((err) => {
  console.error(err);
  process.exit(1);
});
