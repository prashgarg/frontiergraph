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
  assert(await page.getByRole("heading", { name: /Find the next paper worth your time\./i }).isVisible(), "Homepage hero missing");
  const nav = page.getByRole("navigation");
  assert(await nav.getByRole("link", { name: /^Home$/ }).isVisible(), "Home nav missing");
  assert(await nav.getByRole("link", { name: /^Questions$/ }).isVisible(), "Questions nav missing");
  assert(await nav.getByRole("link", { name: /^Map$/ }).isVisible(), "Map nav missing");
  assert(await nav.getByRole("link", { name: /^Paper$/ }).isVisible(), "Paper nav missing");
  assert(await nav.getByRole("link", { name: /^Downloads$/ }).isVisible(), "Downloads nav missing");
  assert((await nav.getByRole("link", { name: /How it works/i }).count()) === 0, "How it works should not remain in nav");
  assert((await nav.getByRole("link", { name: /^Method$/ }).count()) === 0, "Method should not remain in nav");
  assert(await page.getByRole("link", { name: /^Browse questions$/ }).first().isVisible(), "Homepage CTA missing");
  assert(await page.getByRole("link", { name: /^Explore in app$/ }).first().isVisible(), "Homepage app CTA missing");
  assert(await page.getByRole("link", { name: /^Read paper$/ }).first().isVisible(), "Homepage paper CTA missing");
  assert(await page.getByRole("link", { name: /^Download data$/ }).first().isVisible(), "Homepage data CTA missing");
  assert(await page.locator('[data-role="homepage-carousel"]').isVisible(), "Homepage should show the featured example");
  assert((await page.locator('[data-role="homepage-carousel-slide"]').count()) === 4, "Homepage should show 4 featured examples");
  assert(await page.getByText(/Featured question/i).first().isVisible(), "Homepage should label the example");
  assert(await page.getByText(/How does public debt shape CO2 emissions/i).isVisible(), "Homepage lead example missing");
  assert(await page.locator('[data-role="homepage-scale-strip"]').isVisible(), "Homepage release strip missing");

  await page.goto(`${baseUrl}/questions/`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");
  await textDoesNotContain(page, ["NaN", "undefined", "sqlite3.OperationalError"]);
  assert(await page.getByRole("heading", { name: /Browse questions that could become your next paper/i }).isVisible(), "Questions hero missing");
  assert(
    (await page.locator('[data-role="questions-curated-front-set"] [data-role="curated-opportunity-card"]').count()) === 6,
    "Questions page should show exactly 6 curated cards",
  );
  assert((await page.locator('[data-role^="field-shelf-"]').count()) === 5, "Questions page should show 5 field shelves");
  assert((await page.locator('[data-role^="question-collection-"]').count()) === 5, "Questions page should show 5 question collections");
  assert(await page.getByRole("heading", { name: /Browse by field/i }).isVisible(), "Questions field heading missing");
  assert(await page.getByRole("heading", { name: /Browse by use case/i }).isVisible(), "Questions use-case heading missing");
  const rankedSection = page.locator('[data-role="overall-ranked-questions"]');
  assert(await rankedSection.getByRole("button", { name: /No direct papers yet/i }).isVisible(), "Questions filters missing");
  assert(await rankedSection.getByRole("button", { name: /Some direct evidence/i }).isVisible(), "Questions filters missing exact-evidence chip");
  assert(await rankedSection.getByPlaceholder("Search by topic").isVisible(), "Questions search missing");
  assert((await page.getByRole("link", { name: /How it works/i }).count()) === 0, "Questions page should not point to How it works");

  await page.goto(`${baseUrl}/graph/`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-role="graph-canvas"]');
  await textDoesNotContain(page, ["NaN", "undefined", "sqlite3.OperationalError"]);
  assert(await page.getByRole("heading", { name: /Use the map when you already have a topic in mind/i }).isVisible(), "Map hero missing");
  assert(await page.getByRole("link", { name: /^Browse questions$/ }).first().isVisible(), "Map should link back to questions");
  assert(await page.getByRole("link", { name: /^Explore in app$/ }).first().isVisible(), "Map should link to app");
  assert(await page.getByRole("heading", { name: /Selected topic/i }).isVisible(), "Map selected-topic panel missing");
  const focusedNodeCount = await page.locator("[data-node-id]").count();
  assert(focusedNodeCount > 0, "Focused map rendered no nodes");
  await page.getByRole("button", { name: /Show full map/i }).click();
  await page.waitForTimeout(300);
  const globalNodeCount = await page.locator("[data-node-id]").count();
  assert(globalNodeCount > focusedNodeCount, "Full map should render more nodes than focused mode");
  await page.getByRole("button", { name: /Return to focused view/i }).click();
  await page.waitForTimeout(300);

  await page.goto(`${baseUrl}/about/`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");
  assert(await page.getByRole("heading", { name: /FrontierGraph helps narrow the reading problem/i }).isVisible(), "About hero missing");
  assert(await page.getByRole("heading", { name: /^What this is$/ }).isVisible(), "About cards missing");
  assert(await page.getByRole("heading", { name: /^How to use it$/ }).isVisible(), "About cards missing");
  assert(await page.getByRole("heading", { name: /^What it does not do$/ }).isVisible(), "About cards missing");

  await page.goto(`${baseUrl}/downloads/`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");
  assert(await page.getByRole("heading", { name: /Take the paper, the tables, or the full public bundle/i }).isVisible(), "Downloads hero missing");
  assert(await page.getByRole("link", { name: /Paper overview/i }).first().isVisible(), "Downloads page should expose the paper overview");
  assert(await page.getByRole("link", { name: /Working paper PDF/i }).first().isVisible(), "Downloads page should expose the working paper");
  assert(await page.getByRole("link", { name: /Extended abstract PDF/i }).isVisible(), "Downloads page should expose the extended abstract");
  assert(await page.getByText(/frontiergraph-economics-public\.db/i).isVisible(), "Downloads page should show the public DB bundle");
  assert(await page.getByText(/Tier 1/i).first().isVisible(), "Downloads page should show tiered releases");

  await page.goto(`${baseUrl}/paper/`, { waitUntil: "networkidle" });
  assert(await page.getByRole("heading", { name: /What FrontierGraph Finds/i }).first().isVisible(), "Paper overview missing");
  assert(await page.getByRole("link", { name: /^Explore in app$/ }).first().isVisible(), "Paper overview app CTA missing");

  await page.goto(`${baseUrl}/paper/full/`, { waitUntil: "networkidle" });
  assert(await page.getByRole("heading", { name: /What Should Economics Work On Next/i }).first().isVisible(), "Full paper missing");
  assert(await page.getByRole("link", { name: /^Browse questions$/ }).first().isVisible(), "Full paper should link back to questions");

  await expectRedirect(page, "/how-it-works/", "/about/");
  await expectRedirect(page, "/method/", "/about/");
  await expectRedirect(page, "/faq/", "/about/");
  await expectRedirect(page, "/validation/", "/about/");
  await expectRedirect(page, "/compare/", "/about/");
  await expectRedirect(page, "/advanced/", "/downloads/");
  await expectRedirect(page, "/opportunities/", "/questions/");

  await captureSet(browser, [
    { name: "home", path: "/" },
    { name: "questions", path: "/questions/" },
    { name: "map", path: "/graph/" },
    { name: "about", path: "/about/" },
    { name: "downloads", path: "/downloads/" },
    { name: "paper", path: "/paper/" },
    { name: "paper_full", path: "/paper/full/" },
  ]);

  assert(errors.length === 0, `Browser errors found:\n${errors.join("\n")}`);
  await browser.close();
  console.log("playwright smoke passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
