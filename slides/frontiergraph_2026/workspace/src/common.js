const pptxgen = require("pptxgenjs");
const { imageSizingContain } = require("../pptxgenjs_helpers/image");
const {
  warnIfSlideHasOverlaps,
  warnIfSlideElementsOutOfBounds,
} = require("../pptxgenjs_helpers/layout");

const COLORS = {
  bg: "F6F1E7",
  panel: "FFFDFC",
  ink: "2B2F38",
  muted: "6A7280",
  blue: "426DA9",
  blueLight: "DCE6F4",
  rust: "C96849",
  sand: "E8D8B5",
  border: "D8C6A2",
  green: "537A66",
};

const FONTS = {
  title: "Aptos",
  body: "Aptos",
};

const PAGE = {
  w: 13.333,
  h: 7.5,
  marginX: 0.55,
  marginTop: 0.36,
  marginBottom: 0.34,
};

function makeDeck() {
  const pptx = new pptxgen();
  pptx.layout = "LAYOUT_WIDE";
  pptx.author = "Prashant Garg";
  pptx.company = "Imperial College London";
  pptx.subject = "FrontierGraph seminar deck";
  pptx.lang = "en-GB";
  pptx.theme = {
    headFontFace: FONTS.title,
    bodyFontFace: FONTS.body,
    lang: "en-GB",
  };
  pptx.defineLayout({ name: "FG_WIDE", width: 13.333, height: 7.5 });
  pptx.layout = "FG_WIDE";
  return pptx;
}

function addSlideBase(slide, section, title) {
  slide.background = { color: COLORS.bg };
  slide.addText(section, {
    x: PAGE.marginX,
    y: PAGE.marginTop - 0.02,
    w: 2.0,
    h: 0.16,
    fontFace: FONTS.body,
    fontSize: 10,
    bold: false,
    color: COLORS.muted,
    italic: true,
    margin: 0,
  });
  slide.addText(title, {
    x: PAGE.marginX,
    y: PAGE.marginTop + 0.14,
    w: 9.7,
    h: 0.38,
    fontFace: FONTS.title,
    fontSize: 21,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addShape("line", {
    x: PAGE.marginX,
    y: 0.92,
    w: 12.15,
    h: 0,
    line: { color: COLORS.border, pt: 1.2 },
  });
}

function addFooter(slide, text = "") {
  if (text) {
    slide.addText(text, {
      x: PAGE.marginX,
      y: 7.1,
      w: 7.8,
      h: 0.14,
      fontFace: FONTS.body,
      fontSize: 8.5,
      color: COLORS.muted,
      margin: 0,
    });
  }
}

function addAppendixButton(slide, targetSlide, label = "Appendix") {
  slide.addShape("roundRect", {
    x: 11.88,
    y: 0.28,
    w: 0.9,
    h: 0.24,
    rectRadius: 0.03,
    fill: { color: COLORS.blueLight },
    line: { color: COLORS.blue, pt: 0.9 },
    hyperlink: { slide: targetSlide, tooltip: label },
  });
  slide.addText(label, {
    x: 11.88,
    y: 0.305,
    w: 0.9,
    h: 0.12,
    align: "center",
    fontFace: FONTS.body,
    fontSize: 8,
    color: COLORS.blue,
    bold: true,
    margin: 0,
    hyperlink: { slide: targetSlide, tooltip: label },
  });
}

function addBackButton(slide, targetSlide, label = "Back to main") {
  slide.addShape("roundRect", {
    x: 11.58,
    y: 0.28,
    w: 1.2,
    h: 0.24,
    rectRadius: 0.03,
    fill: { color: COLORS.blueLight },
    line: { color: COLORS.blue, pt: 0.9 },
    hyperlink: { slide: targetSlide, tooltip: label },
  });
  slide.addText(label, {
    x: 11.58,
    y: 0.305,
    w: 1.2,
    h: 0.12,
    align: "center",
    fontFace: FONTS.body,
    fontSize: 8,
    color: COLORS.blue,
    bold: true,
    margin: 0,
    hyperlink: { slide: targetSlide, tooltip: label },
  });
}

function addBulletCue(slide, x, y, w, lines, opts = {}) {
  const fontSize = opts.fontSize || 13;
  const gap = opts.gap || 0.42;
  lines.forEach((line, i) => {
    slide.addShape("ellipse", {
      x,
      y: y + i * gap + 0.08,
      w: 0.08,
      h: 0.08,
      fill: { color: opts.dotColor || COLORS.rust },
      line: { color: opts.dotColor || COLORS.rust, pt: 0.5 },
    });
    slide.addText(line, {
      x: x + 0.16,
      y: y + i * gap,
      w: w - 0.16,
      h: 0.26,
      fontFace: FONTS.body,
      fontSize,
      color: opts.color || COLORS.ink,
      bold: !!opts.bold,
      margin: 0,
    });
  });
}

function addSmallCitations(slide, text, x = PAGE.marginX, y = 6.78, w = 5.5) {
  slide.addText(text, {
    x,
    y,
    w,
    h: 0.18,
    fontFace: FONTS.body,
    fontSize: 8.5,
    color: COLORS.muted,
    italic: true,
    margin: 0,
  });
}

function addImagePanel(slide, title, path, x, y, w, h) {
  slide.addText(title, {
    x,
    y: y - 0.24,
    w,
    h: 0.16,
    fontFace: FONTS.body,
    fontSize: 12,
    color: COLORS.muted,
    bold: true,
    margin: 0,
  });
  slide.addShape("roundRect", {
    x,
    y,
    w,
    h,
    rectRadius: 0.03,
    fill: { color: COLORS.panel },
    line: { color: COLORS.border, pt: 1 },
  });
  slide.addImage({
    path,
    ...imageSizingContain(path, x + 0.06, y + 0.06, w - 0.12, h - 0.12),
  });
}

function addInfoCard(slide, opts) {
  const {
    x,
    y,
    w,
    h,
    title,
    subtitle = "",
    items = [],
    titleColor = COLORS.ink,
    dotColor = COLORS.rust,
    fillColor = "FFFDFC",
    fontSize = 10,
    gap = 0.72,
  } = opts;
  slide.addShape("roundRect", {
    x,
    y,
    w,
    h,
    rectRadius: 0.05,
    fill: { color: fillColor },
    line: { color: COLORS.border, pt: 1.0 },
  });
  slide.addText(title, {
    x: x + 0.22,
    y: y + 0.22,
    w: w - 0.44,
    h: 0.16,
    fontFace: FONTS.body,
    fontSize: 13.5,
    bold: true,
    color: titleColor,
    margin: 0,
  });
  let bulletsY = y + 0.62;
  if (subtitle) {
    slide.addText(subtitle, {
      x: x + 0.22,
      y: y + 0.46,
      w: w - 0.44,
      h: 0.12,
      fontFace: FONTS.body,
      fontSize: 8,
      italic: true,
      color: COLORS.muted,
      margin: 0,
    });
    bulletsY = y + 0.78;
  }
  addBulletCue(slide, x + 0.22, bulletsY, w - 0.44, items, {
    fontSize,
    gap,
    dotColor,
  });
}

function addNetworkBackdrop(slide) {
  const dots = [
    [0.9, 0.95],
    [1.8, 1.4],
    [2.6, 1.0],
    [3.2, 1.8],
    [4.2, 1.15],
    [10.4, 0.9],
    [11.2, 1.45],
    [12.0, 1.0],
    [11.6, 2.1],
  ];
  const lines = [
    [0, 1],
    [1, 2],
    [1, 3],
    [2, 4],
    [5, 6],
    [6, 7],
    [6, 8],
  ];
  lines.forEach(([a, b]) => {
    slide.addShape("line", {
      x: dots[a][0],
      y: dots[a][1],
      w: dots[b][0] - dots[a][0],
      h: dots[b][1] - dots[a][1],
      line: { color: COLORS.border, pt: 1, transparency: 35 },
    });
  });
  dots.forEach(([x, y], i) => {
    slide.addShape("ellipse", {
      x,
      y,
      w: i % 3 === 0 ? 0.16 : 0.11,
      h: i % 3 === 0 ? 0.16 : 0.11,
      fill: { color: i % 2 === 0 ? COLORS.blueLight : COLORS.sand, transparency: 12 },
      line: { color: COLORS.border, pt: 0.6, transparency: 35 },
    });
  });
}

function finalizeSlide(slide, pptx) {
  warnIfSlideHasOverlaps(slide, pptx, { muteContainment: true });
  warnIfSlideElementsOutOfBounds(slide, pptx);
}

module.exports = {
  COLORS,
  FONTS,
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
};
