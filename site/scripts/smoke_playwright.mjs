import { chromium } from "playwright";

import fs from "node:fs";
import path from "node:path";

const baseUrl = process.argv[2] || "http://127.0.0.1:4173";
const screenshotDir = process.argv[3] || "";

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function textDoesNotContain(page, forbidden) {
  const bodyText = await page.locator("body").innerText();
  for (const token of forbidden) {
    assert(!bodyText.includes(token), `Page contains forbidden token: ${token}`);
  }
}

async function expectRedirect(page, path, expectedPathname) {
  await page.goto(`${baseUrl}${path}`, { waitUntil: "domcontentloaded" });
  await page.waitForURL(new RegExp(`${expectedPathname.replaceAll("/", "\\/")}$`));
}

async function captureSet(browser, routes) {
  if (!screenshotDir) return;
  fs.mkdirSync(screenshotDir, { recursive: true });
  const viewports = [
    { suffix: "desktop", width: 1440, height: 1100 },
    { suffix: "tablet", width: 900, height: 1180 },
    { suffix: "mobile", width: 390, height: 844 },
  ];

  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height } });
    for (const route of routes) {
      await page.goto(`${baseUrl}${route.path}`, { waitUntil: "networkidle" });
      await page.screenshot({
        path: path.join(screenshotDir, `${route.name}_${viewport.suffix}.png`),
        fullPage: true,
      });
    }
    await page.close();
  }
}

async function main() {
  const browser = await chromium.launch({
    channel: "chrome",
    headless: true,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  const errors = [];
  page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(`console:${msg.text()}`);
  });

  await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");
  await textDoesNotContain(page, ["NaN", "undefined", "sqlite3.OperationalError", "For academics", "A simple analogy", "Why this exists"]);
  const homeHeroText = (await page.locator("h1").first().textContent()) || "";
  assert(/Organizing open questions in economics\./i.test(homeHeroText), "Homepage hero missing");
  const nav = page.getByRole("navigation");
  assert(await nav.getByRole("link", { name: /^Home$/ }).isVisible(), "Home nav missing");
  assert(await nav.getByRole("link", { name: /^Questions$/ }).isVisible(), "Questions nav missing");
  assert(await nav.getByRole("link", { name: /^Explorer$/ }).isVisible(), "Explorer nav missing");
  assert(await nav.getByRole("link", { name: /^Paper$/ }).isVisible(), "Paper nav missing");
  assert(await nav.getByRole("link", { name: /^Downloads$/ }).isVisible(), "Downloads nav missing");
  assert((await page.getByRole("button", { name: /Dark mode/i }).count()) === 0, "Dark mode toggle should be removed");
  assert((await nav.getByRole("link", { name: /How it works/i }).count()) === 0, "How it works should not remain in nav");
  assert((await nav.getByRole("link", { name: /^Method$/ }).count()) === 0, "Method should not remain in nav");
  assert(await page.getByRole("link", { name: /^Browse questions$/ }).first().isVisible(), "Homepage CTA missing");
  assert(await page.getByRole("link", { name: /^Literature Graph$/ }).first().isVisible(), "Homepage literature CTA missing");
  assert(await page.getByRole("link", { name: /^Paper$/ }).first().isVisible(), "Homepage paper CTA missing");
  assert(await page.getByRole("link", { name: /^Download data$/ }).first().isVisible(), "Homepage data CTA missing");
  assert(await page.getByText(/^What$/).first().isVisible(), "Homepage what card missing");
  assert(await page.getByText(/^Why$/).first().isVisible(), "Homepage why card missing");
  assert(await page.getByText(/How to read the map/i).isVisible(), "Homepage graph explainer section missing");
  assert(await page.getByRole("link", { name: /About the project/i }).isVisible(), "Homepage about link missing");
  const feedbackTrigger = page.getByRole("button", { name: /^Give feedback$/ });
  assert(await feedbackTrigger.isVisible(), "Site feedback trigger missing");
  await feedbackTrigger.click();
  await page.locator(".feedback-dialog[open]").waitFor({ timeout: 5000 });
  assert(await page.locator(".feedback-dialog[open]").isVisible(), "Feedback dialog should open");
  await page.getByRole("button", { name: /Cancel/i }).click();
  assert((await page.locator('[data-role="home-editorial-carousel"]').count()) === 0, "Homepage should not show the old editorial carousel");
  assert(await page.locator('[data-role="homepage-scale-strip"]').isVisible(), "Homepage release strip missing");

  await page.goto(`${baseUrl}/questions/`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");
  await textDoesNotContain(page, ["NaN", "undefined", "sqlite3.OperationalError"]);
  assert(await page.getByRole("heading", { name: /Curated research questions\./i }).isVisible(), "Questions hero missing");
  assert(
    await page.getByText(/Start with a tighter front stack of mechanism questions/i).isVisible(),
    "Questions hero explanation missing",
  );
  const mechanismSection = page.locator('[data-role="mechanism-front-carousel"]');
  assert(await mechanismSection.getByRole("heading", { name: /^Mechanism questions$/ }).isVisible(), "Mechanism section missing");
  assert(
    (await mechanismSection.locator('[data-role="editorial-carousel-slide"]').count()) >= 10,
    "Mechanism section should expose multiple curated carousel slides",
  );
  assert(
    (await mechanismSection.locator('a[href*="/graph/"][href*="family=mechanism"]').count()) >= 10,
    "Mechanism carousel should deep-link into the graph with family=mechanism",
  );
  assert((await page.locator('[data-role^="field-carousel-"]').count()) >= 4, "Questions page should expose field carousels");
  assert((await page.locator('[data-role^="use-case-carousel-"]').count()) >= 1, "Questions page should expose a use-case carousel");
  assert(await page.getByRole("heading", { name: /^Macro and finance$/ }).isVisible(), "Macro carousel missing");
  assert(await page.getByRole("heading", { name: /^Innovation and productivity$/ }).isVisible(), "Innovation carousel missing");
  assert(await page.getByRole("heading", { name: /^Climate and energy$/ }).isVisible(), "Climate carousel missing");
  assert(await page.getByRole("heading", { name: /^Labor and household$/ }).isVisible(), "Labor carousel missing");
  assert(await page.getByRole("heading", { name: /^Longer-horizon project ideas$/ }).isVisible(), "Use-case carousel missing");
  const rankedSection = page.locator('[data-role="overall-ranked-questions"]');
  assert(await rankedSection.getByRole("heading", { name: /^Broader mechanism archive$/ }).isVisible(), "Questions archive heading missing");
  assert((await rankedSection.locator(".opportunity-card").count()) >= 12, "Mechanism archive should expose multiple cards");
  assert((await page.getByRole("link", { name: /How it works/i }).count()) === 0, "Questions page should not point to How it works");
  assert((await page.getByText(/Questions with stronger nearby evidence/i).count()) === 0, "Legacy use-case shelf should be removed");
  assert((await page.getByText(/Broader project candidates/i).count()) === 0, "Legacy use-case shelf should be removed");
  assert((await page.getByText(/Open questions with little direct work/i).count()) === 0, "Legacy use-case shelf should be removed");
  assert((await page.getByText(/current public release/i).count()) === 0, "Questions page should not repeat current public release copy on cards");
  assert((await page.getByText(/already sit near the same short paths and papers/i).count()) === 0, "Questions page should not use the old fallback copy");

  await page.goto(`${baseUrl}/graph/`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-role="search-input"]');
  await textDoesNotContain(page, ["NaN", "undefined", "sqlite3.OperationalError"]);
  assert(await page.getByRole("heading", { name: /Pick a topic and inspect why a surfaced question appears nearby\./i }).first().isVisible(), "Graph hero missing");
  assert(await page.getByPlaceholder("Search topics or close variants").isVisible(), "Graph search missing");
  assert((await page.getByRole("heading", { name: /Start with a topic/i }).count()) === 0, "Graph page should not show the old idle card");
  assert((await page.getByRole("button", { name: /Rearrange/i }).count()) === 0, "Map should not show rearrange button");
  assert((await page.getByRole("button", { name: /Reset topic/i }).count()) === 0, "Map should not show reset-topic button");
  await page.waitForSelector('[data-role="graph-active"]:not([hidden])');
  assert(await page.getByRole("button", { name: /^Zoom in$/i }).isVisible(), "Graph page should expose zoom-in control");
  assert(await page.getByRole("button", { name: /^Zoom out$/i }).isVisible(), "Graph page should expose zoom-out control");
  assert(await page.getByRole("heading", { name: /Surfaced questions around this topic/i }).isVisible(), "Graph page should prioritize questions");
  assert(await page.getByRole("heading", { name: /Why this question surfaced/i }).isVisible(), "Graph page should show question detail");
  assert(await page.getByText(/Selected topic/i).count() + await page.getByText(/Starter papers/i).count() >= 1, "Graph page should show selected topic context");
  assert(await page.getByText(/Show local graph/i).isVisible(), "Graph page should keep graph context available");
  assert(await page.getByRole("heading", { name: /trade openness/i }).first().isVisible(), "Graph page should preload a topic");
  assert((await page.locator("[data-node-id]").count()) > 0, "Preloaded local graph rendered no nodes");
  const focusedNodeCount = await page.locator("[data-node-id]").count();
  await page.getByRole("button", { name: /Show full map/i }).click();
  await page.waitForTimeout(300);
  const globalNodeCount = await page.locator("[data-node-id]").count();
  assert(globalNodeCount > focusedNodeCount, "Full map should render more nodes than focused mode");
  await page.getByRole("button", { name: /Return to focused view/i }).click();
  await page.waitForTimeout(300);
  await page.goto(
    `${baseUrl}/graph/?q=financial%20development&pair=FG3C000006__FG3C000053&family=mechanism`,
    { waitUntil: "networkidle" },
  );
  await page.waitForSelector('[data-role="graph-active"]:not([hidden])');
  assert(
    await page.getByRole("heading", { name: /Why this mechanism question surfaced/i }).isVisible(),
    "Mechanism graph deep link should switch the question focus heading",
  );

  await page.goto(`${baseUrl}/about/`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");
  assert(await page.getByRole("heading", { name: /^Why Frontier Graph exists\.$/ }).isVisible(), "About hero missing");
  assert(await page.getByText(/^Prashant Garg$/).isVisible(), "About profile missing");
  assert(await page.getByText(/Imperial College London/i).first().isVisible(), "About affiliation missing");
  assert(await page.getByRole("heading", { name: /Why I built it/i }).isVisible(), "About page should explain why the project exists");
  assert(await page.getByRole("heading", { name: /Why it matters now/i }).isVisible(), "About page should explain why the project matters");
  assert(await page.getByRole("heading", { name: /What you can do here/i }).isVisible(), "About page should explain how to use the project");
  assert(await page.getByRole("heading", { name: /Limitations/i }).isVisible(), "About page should include limitations");

  await page.goto(`${baseUrl}/downloads/`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");
  assert(await page.getByRole("heading", { name: /Download the current paper and released files\./i }).isVisible(), "Downloads hero missing");
  assert((await page.getByRole("link", { name: /^Release guide/i }).count()) >= 1, "Downloads page should expose the release guide");
  assert((await page.getByRole("link", { name: /^Data dictionary/i }).count()) >= 1, "Downloads page should expose the data dictionary");
  assert((await page.getByRole("link", { name: /^Current paper PDF/i }).count()) >= 1, "Downloads page should expose the current paper PDF");
  assert((await page.getByRole("link", { name: /^Extended abstract PDF/i }).count()) === 0, "Downloads page should not expose the extended abstract");
  assert((await page.getByRole("link", { name: /^Download bundle$/ }).count()) === 2, "Downloads page should show bundle downloads for tiers 1 and 2");
  assert((await page.getByRole("link", { name: /^Download database$/ }).count()) === 1, "Downloads page should expose the SQLite database download");
  assert(await page.getByText(/About the release/i).isVisible(), "Downloads page should keep the release explanation collapsed");
  assert(await page.getByText(/frontiergraph-economics-public\.db/i).first().isVisible(), "Downloads page should show the public DB bundle");
  assert(await page.getByText(/Tier 1/i).first().isVisible(), "Downloads page should show tiered releases");
  assert(await page.getByText(/The PDF is the current reference version\./i).first().isVisible(), "Downloads page should explain the current manuscript state");

  await page.goto(`${baseUrl}/paper/`, { waitUntil: "networkidle" });
  assert(await page.getByRole("heading", { name: /What Should Economics Ask Next/i }).first().isVisible(), "Paper page missing");
  assert(await page.getByText(/The PDF is the current reference version\./i).first().isVisible(), "Paper page should explain the manuscript status");
  assert(await page.getByText(/This HTML page is provisional\./i).isVisible(), "Paper page should mark the HTML as provisional");
  assert((await page.locator(".paper-hero .button-row a").count()) === 2, "Paper hero should only show paper-specific CTAs");
  assert(await page.locator(".paper-hero .button-row").getByRole("link", { name: /^Download PDF$/ }).isVisible(), "Paper hero PDF CTA missing");
  assert(await page.locator(".paper-hero .button-row").getByRole("link", { name: /^Open downloads$/ }).isVisible(), "Paper hero downloads CTA missing");
  assert((await page.locator(".paper-mermaid").count()) >= 1, "Paper page should render Mermaid diagrams");
  const paperText = await page.locator("main").innerText();
  assert(!/flowchart LR/i.test(paperText), "Paper page should not expose raw Mermaid source");

  await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
  assert(await page.locator('link[rel="canonical"]').getAttribute("href"), "Homepage should include canonical metadata");
  assert(await page.locator('meta[property="og:image"]').getAttribute("content"), "Homepage should include OG image metadata");
  assert(await page.getByRole("link", { name: /^About$/ }).first().isVisible(), "Header should expose About");
  assert(await page.getByText(/Start with one short path\./i).isVisible(), "Homepage should show the map explainer");

  await expectRedirect(page, "/paper/full/", "/paper/");

  await expectRedirect(page, "/how-it-works/", "/about/");
  await expectRedirect(page, "/method/", "/about/");
  await expectRedirect(page, "/faq/", "/about/");
  await expectRedirect(page, "/validation/", "/about/");
  await expectRedirect(page, "/compare/", "/about/");
  await expectRedirect(page, "/advanced/", "/downloads/");
  await expectRedirect(page, "/opportunities/", "/questions/");

  await page.goto(`${baseUrl}/broad/`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");
  assert(await page.getByRole("heading", { name: /Broad preview: finer topic vocabulary\./i }).isVisible(), "Broad home hero missing");
  assert(await page.getByText(/16\.5k-topic regime/i).isVisible(), "Broad home should explain the broader regime");
  assert((await page.getByRole("link", { name: /Broad app preview/i }).count()) === 0, "Broad home should not show retired workspace CTA");

  await page.goto(`${baseUrl}/broad/questions/`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");
  assert(await page.getByRole("heading", { name: /Browse questions from the broad preview\./i }).isVisible(), "Broad questions hero missing");
  assert(await page.getByText(/broader 16\.5k-topic regime directly/i).isVisible(), "Broad questions should explain the regime swap");
  assert(await page.getByRole("link", { name: /See question/i }).first().isVisible(), "Broad questions should expose question links");

  await page.goto(`${baseUrl}/broad/graph/`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-role="search-input"]');
  assert(await page.getByRole("heading", { name: /Pick a topic and inspect why a surfaced question appears nearby\./i }).first().isVisible(), "Broad graph hero missing");
  await page.waitForSelector('[data-role="graph-active"]:not([hidden])');
  assert(await page.getByRole("heading", { name: /Surfaced questions around this topic/i }).isVisible(), "Broad graph should show question chooser");

  await page.goto(`${baseUrl}/broad/audit/`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");
  assert(await page.getByRole("heading", { name: /Side-by-side regime audit\./i }).isVisible(), "Broad audit hero missing");
  assert(await page.getByText(/current public site tracks the main release/i).isVisible(), "Broad audit note missing");

  await captureSet(browser, [
    { name: "home", path: "/" },
    { name: "questions", path: "/questions/" },
    { name: "map", path: "/graph/" },
    { name: "about", path: "/about/" },
    { name: "downloads", path: "/downloads/" },
    { name: "paper", path: "/paper/" },
    { name: "paper_full", path: "/paper/full/" },
    { name: "broad_home", path: "/broad/" },
    { name: "broad_questions", path: "/broad/questions/" },
    { name: "broad_graph", path: "/broad/graph/" },
    { name: "broad_audit", path: "/broad/audit/" },
  ]);

  assert(errors.length === 0, `Browser errors found:\n${errors.join("\n")}`);
  await browser.close();
  console.log("playwright smoke passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
