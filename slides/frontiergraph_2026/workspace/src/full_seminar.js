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
  pipeline: `${ROOT}/tmp/pdfs/fig2_review/page-07.png`,
  pairedBenchmark: `${ROOT}/outputs/paper/149_dual_family_main_pairing/dual_family_main_benchmark.png`,
  pathEvolution: `${ROOT}/outputs/paper/138_path_evolution_refresh/figures/path_evolution_comparison.png`,
  currentFrontier: `${ROOT}/outputs/paper/154_dual_family_extension_pairing/dual_family_current_frontier_summary.png`,
  heterogeneity: `${ROOT}/outputs/paper/154_dual_family_extension_pairing/dual_family_heterogeneity_comparison.png`,
  usefulness: `${ROOT}/outputs/paper/164_paired_historical_usefulness_comparison/paired_historical_usefulness_summary.png`,
  graphEvolution: `${ROOT}/outputs/paper/155_graph_evolution_appendix/graph_evolution_over_time.png`,
};

function addSimpleTextSlide(slide, section, title, items, footer) {
  addSlideBase(slide, section, title);
  addBulletCue(slide, 0.92, 1.48, 11.3, items, { fontSize: 11, gap: 0.72, dotColor: COLORS.rust });
  addFooter(slide, footer);
}

async function build() {
  const pptx = makeDeck();
  pptx.title = "What Should Science Ask Next? (Seminar)";
  const slides = [];

  {
    const s = pptx.addSlide();
    s.background = { color: COLORS.bg };
    addNetworkBackdrop(s);
    s.addText("What Should Science Ask Next?", {
      x: 0.72, y: 1.0, w: 6.7, h: 0.62, fontSize: 24, bold: true, color: COLORS.ink, margin: 0,
    });
    s.addText("Prashant Garg", {
      x: 0.76, y: 1.95, w: 2.2, h: 0.15, fontSize: 11, bold: true, color: COLORS.ink, margin: 0,
    });
    s.addText("Imperial College London", {
      x: 0.76, y: 2.18, w: 2.8, h: 0.15, fontSize: 9, color: COLORS.muted, margin: 0,
    });
    s.addText("github.com/prashgarg/frontiergraph", {
      x: 0.76, y: 2.42, w: 3.6, h: 0.15, fontSize: 8, color: COLORS.blue, margin: 0,
      hyperlink: { url: "https://github.com/prashgarg/frontiergraph", tooltip: "Project repository" },
    });
    s.addText("Economics seminar version", {
      x: 0.76, y: 3.05, w: 2.4, h: 0.15, fontSize: 9, color: COLORS.muted, italic: true, margin: 0,
    });
    s.addShape("roundRect", {
      x: 7.3, y: 0.95, w: 5.15, h: 5.0, rectRadius: 0.05,
      fill: { color: "FFF8EE" }, line: { color: COLORS.border, pt: 1.2 },
    });
    addBulletCue(s, 7.68, 1.45, 4.2, [
      "question choice is under-formalized",
      "the literature is large and fragmented",
      "some progress adds mechanisms, some states direct links",
      "the graph helps rank what may be worth reading first",
    ], { fontSize: 10.3, gap: 0.74, dotColor: COLORS.green });
    addFooter(s, "Full seminar draft");
    slides.push(s);
  }

  {
    const s = pptx.addSlide();
    addSlideBase(s, "Motivation", "Question choice is a science-wide bottleneck");
    addBulletCue(s, 0.92, 1.48, 6.0, [
      "Choosing what to work on is one of the least formalized decisions in science.",
      "The burden of existing knowledge keeps rising as the stock of work grows.",
      "Conservative search dominates even when riskier exploration matters disproportionately.",
      "If AI lowers downstream costs, the scarce input shifts upstream toward question choice.",
    ], { fontSize: 10.8, gap: 0.72, dotColor: COLORS.rust });
    addInfoCard(s, {
      x: 7.25,
      y: 1.35,
      w: 5.3,
      h: 3.95,
      title: "Three anchor ideas",
      subtitle: "why this is not just an economics problem",
      items: [
        "knowledge burden rises",
        "ideas get harder to find",
        "scientists still search conservatively",
      ],
      titleColor: COLORS.blue,
      dotColor: COLORS.blue,
      fontSize: 10,
      gap: 0.78,
    });
    addSmallCitations(s, "Jones (2009); Bloom et al. (2020); Foster, Rzhetsky, and Evans (2015)", 7.55, 4.78, 4.45);
    addFooter(s, "Motivation connects science-wide concerns to an economics-facing empirical testbed.");
    finalizeSlide(s, pptx);
    slides.push(s);
  }

  {
    const s = pptx.addSlide();
    addSlideBase(s, "Setting", "Why this setting?");
    addBulletCue(s, 0.92, 1.56, 6.15, [
      "The paper uses a published economics-facing corpus because it gives dated, realized research structure.",
      "That makes missing-question backtesting possible without mixing in draft noise.",
      "The object is economics-facing, but the broader question is science-wide.",
    ], { fontSize: 10.9, gap: 0.86, dotColor: COLORS.rust });
    addInfoCard(s, {
      x: 7.28,
      y: 1.45,
      w: 5.2,
      h: 3.5,
      title: "Why published papers?",
      subtitle: "what this setting buys",
      items: [
        "dated structure",
        "observed realizations",
        "clean prospective evaluation",
      ],
      titleColor: COLORS.blue,
      dotColor: COLORS.green,
      fontSize: 10,
      gap: 0.78,
    });
    s.addText("Narrow enough to interpret, broad enough to matter.", {
      x: 7.55,
      y: 4.52,
      w: 4.6,
      h: 0.15,
      fontSize: 9,
      color: COLORS.ink,
      italic: true,
      margin: 0,
      align: "center",
    });
    addFooter(s, "The empirical testbed is narrow enough to be interpretable and broad enough to matter.");
    finalizeSlide(s, pptx);
    slides.push(s);
  }

  {
    const s = pptx.addSlide();
    addSlideBase(s, "Overview", "This paper");
    const cols = [
      {
        x: 0.82,
        title: "We build",
        subtitle: "data object",
        items: ["a dated graph from published economics-facing papers", "paper-local extraction, then cross-paper matching"],
      },
      {
        x: 4.58,
        title: "We test",
        subtitle: "historical screen",
        items: ["rank still-open next questions using only the literature observed at date t-1", "evaluate them prospectively against later publication"],
      },
      {
        x: 8.34,
        title: "We learn",
        subtitle: "substantive implication",
        items: ["the graph helps in two distinct historical families", "the historical result reveals which kind of scientific movement is more common"],
      },
    ];
    cols.forEach((col) => {
      addInfoCard(s, {
        x: col.x,
        y: 1.45,
        w: 3.5,
        h: 3.2,
        title: col.title,
        subtitle: col.subtitle,
        items: col.items,
        fontSize: 9.6,
        gap: 0.86,
        dotColor: COLORS.rust,
      });
    });
    s.addText("The seminar centers the substantive interpretation, not only the benchmark.", {
      x: 1.12,
      y: 5.02,
      w: 11.0,
      h: 0.15,
      fontSize: 9.8,
      color: COLORS.ink,
      italic: true,
      margin: 0,
      align: "center",
    });
    addFooter(s, "The seminar centers the substantive interpretation, not only the benchmark.");
    finalizeSlide(s, pptx);
    slides.push(s);
  }

  {
    const s = pptx.addSlide();
    addSlideBase(s, "Data and object", "Overall pipeline");
    const stages = [
      ["papers", 0.95],
      ["paper-local graphs", 3.25],
      ["shared graph", 5.95],
      ["dated candidates", 8.4],
      ["future realization", 10.95],
    ];
    stages.forEach(([label, x], i) => {
      s.addShape("roundRect", {
        x,
        y: 2.1,
        w: i === 4 ? 1.45 : 1.9,
        h: 1.15,
        rectRadius: 0.04,
        fill: { color: i < 2 ? "EEF3FB" : "FFF8EE" },
        line: { color: i < 2 ? COLORS.blue : COLORS.border, pt: 1.0 },
      });
      s.addText(label, {
        x: x + 0.12,
        y: 2.43,
        w: i === 4 ? 1.2 : 1.65,
        h: 0.2,
        fontSize: 10,
        bold: true,
        color: COLORS.ink,
        align: "center",
        margin: 0,
      });
      if (i < stages.length - 1) {
        s.addShape("chevron", {
          x: x + (i === 4 ? 1.45 : 1.92),
          y: 2.43,
          w: 0.34,
          h: 0.3,
          fill: { color: COLORS.sand },
          line: { color: COLORS.border, pt: 0.6 },
        });
      }
    });
    addBulletCue(s, 1.0, 4.0, 10.8, [
      "Extraction builds one local graph per paper.",
      "Matching creates a shared concept space across papers.",
      "Candidate generation freezes the graph at t-1 and ranks still-open directed questions.",
    ], { fontSize: 10.5, gap: 0.58, dotColor: COLORS.green });
    addFooter(s, "This is the full-paper object in one slide, before we split into the two historical families.");
    finalizeSlide(s, pptx);
    slides.push(s);
  }

  const imageSlides = [
    ["Method", "Each paper becomes a local graph", ASSETS.extraction, "Paper-local extraction gives the first reusable object."],
    ["Method", "Candidate questions appear only after cross-paper matching", ASSETS.matching, "Cross-paper matching is what turns paper-local fragments into shared candidate structure."],
    ["Method", "Why node normalization matters", ASSETS.matching, "Normalization is central because candidate generation, paths, and missingness all depend on concept identity."],
    ["Empirical object", "Two graph-grounded next-question objects", ASSETS.anchor, "The benchmark event is narrower than the surfaced question."],
  ];
  imageSlides.forEach(([section, title, path, footer]) => {
    const s = pptx.addSlide();
    addSlideBase(s, section, title);
    addImagePanel(s, "", path, 0.85, 1.35, 11.7, 4.9);
    addFooter(s, footer);
    finalizeSlide(s, pptx);
    slides.push(s);
  });

  {
    const s = pptx.addSlide();
    addSimpleTextSlide(s, "Evaluation", "Historical evaluation design", [
      "Freeze the graph at t-1.",
      "Rank still-open directed candidates.",
      "Ask which questions later appear during [t, t+h].",
      "Keep the benchmark event separate from the richer reader-facing surfaced question.",
    ], "This is what makes the exercise prospective rather than narrative.");
    finalizeSlide(s, pptx);
    slides.push(s);
  }

  const resultSlides = [
    ["Historical result", "Paired historical benchmark", ASSETS.pairedBenchmark, "Graph-based screening improves on popularity in both families."],
    ["Substantive result", "How the literature moves", ASSETS.pathEvolution, "The literature more often thickens mechanisms than it later states locally implied direct links."],
    ["Extra empirical view", "Where the graph helps", ASSETS.heterogeneity, "This stays secondary to the main historical and substantive comparison."],
  ];
  resultSlides.forEach(([section, title, path, footer]) => {
    const s = pptx.addSlide();
    addSlideBase(s, section, title);
    addImagePanel(s, "", path, 0.82, 1.35, 11.85, 4.85);
    addFooter(s, footer);
    finalizeSlide(s, pptx);
    slides.push(s);
  });

  {
    const s = pptx.addSlide();
    addSlideBase(s, "Interpretation", "Why the families differ");
    const panels = [
      {
        x: 0.88,
        title: "Direct-to-path",
        color: COLORS.blue,
        items: [
          "smaller candidate universe",
          "higher later realizations per shortlist",
          "benchmark event: a mechanism appears around an already known relation",
        ],
      },
      {
        x: 6.9,
        title: "Path-to-direct",
        color: COLORS.rust,
        items: [
          "larger candidate universe",
          "higher recall of all later-realized links",
          "benchmark event: a locally supported direct relation later becomes explicit",
        ],
      },
    ];
    panels.forEach((panel) => {
      s.addShape("roundRect", {
        x: panel.x,
        y: 1.48,
        w: 5.45,
        h: 3.9,
        rectRadius: 0.05,
        fill: { color: "FFFDFC" },
        line: { color: COLORS.border, pt: 1.0 },
      });
      s.addText(panel.title, {
        x: panel.x + 0.26,
        y: 1.78,
        w: 1.7,
        h: 0.16,
        fontSize: 12,
        bold: true,
        color: panel.color,
        margin: 0,
      });
      addBulletCue(s, panel.x + 0.26, 2.16, 4.75, panel.items, {
        fontSize: 10,
        gap: 0.88,
        dotColor: panel.color,
      });
    });
    s.addText("These are different denominators, not inconsistent results. One family is better for finding high-hit mechanism thickening; the other is better for recovering a broader set of later explicit links.", {
      x: 1.15,
      y: 5.88,
      w: 11.0,
      h: 0.26,
      fontSize: 10,
      color: COLORS.ink,
      margin: 0,
      align: "center",
    });
    addFooter(s, "Direct-to-path and path-to-direct are not mirror images; they reward different kinds of success.");
    finalizeSlide(s, pptx);
    slides.push(s);
  }

  {
    const s = pptx.addSlide();
    addSlideBase(s, "Current frontier", "What the graph surfaces now");
    s.addText("Illustrative cleaned renderings of current frontier items", {
      x: 0.9,
      y: 1.18,
      w: 5.0,
      h: 0.14,
      fontSize: 8,
      color: COLORS.muted,
      italic: true,
      margin: 0,
    });
    const cards = [
      {
        x: 0.88,
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
        x: 6.9,
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
      s.addShape("roundRect", {
        x: card.x,
        y: 1.45,
        w: 5.45,
        h: 4.48,
        rectRadius: 0.05,
        fill: { color: "FFFDFC" },
        line: { color: COLORS.border, pt: 1.0 },
      });
      s.addText(card.title, {
        x: card.x + 0.26,
        y: 1.74,
        w: 1.7,
        h: 0.16,
        fontSize: 12,
        bold: true,
        color: card.color,
        margin: 0,
      });
      s.addText(card.subtitle, {
        x: card.x + 0.26,
        y: 1.98,
        w: 2.9,
        h: 0.14,
        fontSize: 8,
        italic: true,
        color: COLORS.muted,
        margin: 0,
      });
      addBulletCue(s, card.x + 0.26, 2.36, 4.75, card.questions, {
        fontSize: 9.8,
        gap: 0.9,
        dotColor: card.color,
      });
    });
    addFooter(s, "The path-to-direct side is already cleaner publicly. The direct-to-path side is promising but still needs more manual relabeling.");
    finalizeSlide(s, pptx);
    slides.push(s);
  }

  {
    const s = pptx.addSlide();
    addSlideBase(s, "Interpretation", "What this changes");
    addBulletCue(s, 0.92, 1.56, 6.15, [
      "Question choice can be partly disciplined rather than treated as pure intuition.",
      "The graph is most useful for directing scarce reading time, not replacing judgment.",
      "Mechanism thickening appears to be a central mode of scientific progress.",
    ], { fontSize: 10.9, gap: 0.88, dotColor: COLORS.rust });
    addInfoCard(s, {
      x: 7.28,
      y: 1.45,
      w: 5.2,
      h: 3.55,
      title: "Practical reading rule",
      subtitle: "how I would actually use this",
      items: [
        "use the graph to choose what to inspect first",
        "compare the two families rather than forcing one object",
        "treat ranked questions as a disciplined shortlist, not an oracle",
      ],
      titleColor: COLORS.blue,
      dotColor: COLORS.green,
      fontSize: 10,
      gap: 0.76,
    });
    addFooter(s, "This is the slide to linger on in discussion.");
    finalizeSlide(s, pptx);
    slides.push(s);
  }

  {
    const s = pptx.addSlide();
    addSlideBase(s, "Limits", "What this does not do");
    const limitCards = [
      ["Not all imagination", "It does not rank all scientific imagination."],
      ["Imperfect identity", "It does not solve concept identity perfectly."],
      ["Judgment still matters", "It does not remove the need for field knowledge or judgment."],
      ["Cleanly dateable only", "It benchmarks only objects that can be dated cleanly in the observed literature."],
    ];
    limitCards.forEach(([title, body], i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = col === 0 ? 0.92 : 6.72;
      const y = row === 0 ? 1.55 : 3.7;
      s.addShape("roundRect", {
        x,
        y,
        w: 5.55,
        h: 1.55,
        rectRadius: 0.05,
        fill: { color: "FFFDFC" },
        line: { color: COLORS.border, pt: 1.0 },
      });
      s.addText(title, {
        x: x + 0.24,
        y: y + 0.22,
        w: 2.8,
        h: 0.16,
        fontSize: 11,
        bold: true,
        color: COLORS.ink,
        margin: 0,
      });
      s.addText(body, {
        x: x + 0.24,
        y: y + 0.58,
        w: 4.95,
        h: 0.45,
        fontSize: 9.6,
        color: COLORS.ink,
        margin: 0,
      });
    });
    addFooter(s, "The limits are part of the design, not afterthoughts.");
    finalizeSlide(s, pptx);
    slides.push(s);
  }

  {
    const s = pptx.addSlide();
    addSlideBase(s, "Next steps", "Where this can go next");
    const nextCards = [
      ["Longer path support", "ask whether slightly more distant support improves novelty without losing too much coherence"],
      ["Context extension", "take known relations and ask where they remain under-tested across settings"],
      ["LLM workflow layers", "use screening models as a practical refinement layer on top of graph-ranked shortlists"],
      ["Node activation", "treat the appearance of entirely new concepts as a separate frontier object"],
    ];
    nextCards.forEach(([title, body], i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = col === 0 ? 0.92 : 6.72;
      const y = row === 0 ? 1.55 : 3.7;
      s.addShape("roundRect", {
        x,
        y,
        w: 5.55,
        h: 1.55,
        rectRadius: 0.05,
        fill: { color: "FFFDFC" },
        line: { color: COLORS.border, pt: 1.0 },
      });
      s.addText(title, {
        x: x + 0.24,
        y: y + 0.22,
        w: 3.5,
        h: 0.16,
        fontSize: 11,
        bold: true,
        color: COLORS.blue,
        margin: 0,
      });
      s.addText(body, {
        x: x + 0.24,
        y: y + 0.56,
        w: 5.0,
        h: 0.52,
        fontSize: 9.3,
        color: COLORS.ink,
        margin: 0,
      });
    });
    addFooter(s, "These are research directions, not slide filler.");
    finalizeSlide(s, pptx);
    slides.push(s);
  }

  {
    const s = pptx.addSlide();
    addSlideBase(s, "Conclusion", "Conclusion");
    const cols = [
      ["Build", "Build a dated graph from published research."],
      ["Test", "Use it to rank still-open next questions prospectively."],
      ["Learn", "Learn not only whether the graph works, but what kind of scientific movement is more common."],
    ];
    cols.forEach(([title, body], i) => {
      const x = 0.92 + i * 4.0;
      s.addShape("roundRect", {
        x,
        y: 1.68,
        w: 3.5,
        h: 2.15,
        rectRadius: 0.05,
        fill: { color: "FFFDFC" },
        line: { color: COLORS.border, pt: 1.0 },
      });
      s.addText(title, {
        x: x + 0.22,
        y: 1.94,
        w: 1.0,
        h: 0.16,
        fontSize: 12,
        bold: true,
        color: i === 2 ? COLORS.rust : COLORS.blue,
        margin: 0,
      });
      s.addText(body, {
        x: x + 0.22,
        y: 2.36,
        w: 2.95,
        h: 0.72,
        fontSize: 9.8,
        color: COLORS.ink,
        margin: 0,
      });
    });
    s.addText("The benchmark is the credibility layer. The contribution is the claim about how science moves and how researchers can choose what to inspect next.", {
      x: 1.15,
      y: 4.55,
      w: 11.0,
      h: 0.24,
      fontSize: 10.2,
      color: COLORS.ink,
      italic: true,
      align: "center",
      margin: 0,
    });
    addFooter(s, "Full seminar version.");
    finalizeSlide(s, pptx);
    slides.push(s);
  }

  // Appendix slides
  [
    ["Appendix", "Extra benchmark detail", ASSETS.pairedBenchmark],
    ["Appendix", "Current frontier and usefulness", ASSETS.usefulness],
    ["Appendix", "Graph evolution", ASSETS.graphEvolution],
  ].forEach(([section, title, path]) => {
    const s = pptx.addSlide();
    addSlideBase(s, section, title);
    addImagePanel(s, "", path, 0.82, 1.35, 11.85, 4.85);
    addFooter(s, `Appendix: ${title.toLowerCase()}.`);
    finalizeSlide(s, pptx);
    slides.push(s);
  });

  const appendixStart = slides.length - 2;
  for (let i = 1; i < appendixStart - 1; i++) addAppendixButton(slides[i], appendixStart);
  addBackButton(slides[appendixStart - 1], 11);
  addBackButton(slides[appendixStart], 15);
  addBackButton(slides[appendixStart + 1], 18);

  const out = `${ROOT}/slides/frontiergraph_2026/workspace/frontiergraph_full_seminar.pptx`;
  await pptx.writeFile({ fileName: out });
  return out;
}

build().catch((err) => {
  console.error(err);
  process.exit(1);
});
