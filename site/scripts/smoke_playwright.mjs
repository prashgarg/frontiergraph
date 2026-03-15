import { chromium } from "playwright";

const baseUrl = process.argv[2] || "http://127.0.0.1:4173";

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
  await textDoesNotContain(page, ["NaN", "undefined", "sqlite3.OperationalError"]);
  assert(await page.getByRole("heading", { name: "Find the next paper to work on." }).isVisible(), "Homepage hero did not update");
  assert(await page.locator("[data-theme-toggle]").isVisible(), "Theme toggle missing on home");
  const nav = page.getByRole("navigation");
  assert(await nav.getByRole("link", { name: /^Home$/ }).isVisible(), "Home nav missing");
  assert(await nav.getByRole("link", { name: /^Research Questions$/ }).isVisible(), "Research Questions nav missing");
  assert(await nav.getByRole("link", { name: /^How it works$/ }).isVisible(), "How it works nav missing");
  assert(await nav.getByRole("link", { name: /^Method$/ }).isVisible(), "Method nav missing");
  assert(await nav.getByRole("link", { name: /^Literature map$/ }).isVisible(), "Literature map nav missing");
  assert(await nav.getByRole("link", { name: /^Paper$/ }).isVisible(), "Paper nav missing");
  assert(await nav.getByRole("link", { name: /^Downloads$/ }).isVisible(), "Downloads nav missing");
  const heroText = await page.locator("main .hero").first().innerText();
  for (const token of ["Baseline exploratory", "path support", "motif"]) {
    assert(!heroText.includes(token), `Homepage hero should not include ${token}`);
  }
  assert(/Social platforms suggest people to follow from shared connections/i.test(heroText), "Homepage should include the analogy");
  assert(await page.locator('[data-role="homepage-carousel"]').isVisible(), "Homepage should show the proof carousel");
  assert((await page.locator('[data-role="homepage-carousel-slide"]').count()) === 4, "Homepage should show exactly 4 carousel examples");
  assert(!heroText.includes("Where do we go next?"), "Homepage should not show the old speculative framing");
  assert(await page.getByText(/How does public debt shape CO2 emissions/i).isVisible(), "Homepage should show the lead carousel example");
  assert(await page.getByText(/Speculative question/i).first().isVisible(), "Homepage carousel should mark examples as speculative");
  await page.getByRole("link", { name: /Read on the web/i }).first().click();
  await page.waitForURL(/\/paper\/$/);
  await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });

  await page.goto(`${baseUrl}/questions/`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");
  await textDoesNotContain(page, ["NaN", "undefined", "sqlite3.OperationalError"]);
  assert(await page.getByRole("heading", { name: /Browse questions that could become your next paper/i }).isVisible(), "Research Questions hero missing");
  assert(
    (await page.locator('[data-role="questions-curated-front-set"] [data-role="curated-opportunity-card"]').count()) === 6,
    "Research Questions page should show exactly 6 curated cards",
  );
  assert((await page.locator('[data-role^="field-shelf-"]').count()) === 5, "Questions page should show 5 field shelves");
  assert((await page.locator('[data-role^="question-collection-"]').count()) === 5, "Questions page should show 5 question collections");
  const curatedText = await page.locator('[data-role="questions-curated-front-set"]').innerText();
  assert(!/innovation and environmental quality/i.test(curatedText), "Removed curated question still visible in curated front set");
  assert(!/visible questions in the public list/i.test(await page.locator("main").innerText()), "Questions page should not show the visible-count pill");
  assert(await page.getByRole("heading", { name: /Browse by field/i }).isVisible(), "Questions page missing field shelves");
  assert(await page.getByRole("heading", { name: /Browse by use case/i }).isVisible(), "Questions page missing use-case collections");
  const rankedSection = page.locator('[data-role="overall-ranked-questions"]');
  assert(await rankedSection.getByRole("button", { name: /No papers on this exact question yet/i }).isVisible(), "Questions filters missing");
  assert(await rankedSection.getByRole("button", { name: /Already some exact-paper evidence/i }).isVisible(), "Exact-paper evidence filter missing");
  assert(await rankedSection.getByPlaceholder("Search by topic or outcome").isVisible(), "Questions search missing");
  const rankedText = await rankedSection.innerText();
  assert(!rankedText.includes("→"), "Ranked questions should not use arrow syntax");
  assert(!/gap bonus|path support|motif/i.test(rankedText), "Ranked questions should not expose raw graph jargon");
  assert(!/This question sits between/i.test(rankedText), "Ranked questions should not show the old context sentence");
  assert(await page.getByText(/ecological carrying capacity/i).first().isVisible(), "Plain-language public label should render on the questions page");
  assert(!/load capacity factor \(LCF\)/i.test(curatedText), "Raw ontology label should not lead on curated public cards");
  const firstEvidence = rankedSection.locator('[data-role="opportunity-evidence"]').first();
  await firstEvidence.locator("summary").click();
  await page.waitForTimeout(150);
  const evidenceText = await firstEvidence.innerText();
  assert(/Why this question/i.test(evidenceText), "Evidence drawer title missing");
  assert(/Related ideas:/i.test(evidenceText), "Evidence drawer missing related ideas");
  assert(/Papers to start with:/i.test(evidenceText), "Evidence drawer missing starter papers");
  assert(/Papers on this exact question:/i.test(evidenceText), "Evidence drawer missing exact-question status");
  assert(/Common contexts:/i.test(evidenceText), "Evidence drawer missing common contexts");

  await rankedSection.getByRole("button", { name: /Mostly indirect evidence/i }).click();
  await page.waitForTimeout(150);
  await rankedSection.getByPlaceholder("Search by topic or outcome").fill("nonexistent topic");
  await page.waitForTimeout(150);
  assert(await page.getByText(/No visible research questions match/i).isVisible(), "Questions empty state missing");
  await rankedSection.getByPlaceholder("Search by topic or outcome").fill("");
  await rankedSection.getByRole("button", { name: /Mostly indirect evidence/i }).click();
  await page.waitForTimeout(150);

  await page.goto(`${baseUrl}/opportunities/`, { waitUntil: "domcontentloaded" });
  await page.waitForURL(/\/questions\/$/);

  await page.goto(`${baseUrl}/how-it-works/`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");
  await textDoesNotContain(page, ["NaN", "undefined", "sqlite3.OperationalError"]);
  assert(await page.getByRole("heading", { name: /How FrontierGraph helps you decide whether a question is worth pursuing/i }).isVisible(), "How It Works page missing");
  assert(await page.getByText(/Causal Claims in Economics/i).first().isVisible(), "Paper citation missing");
  assert(await page.getByRole("link", { name: /causal\.claims/i }).first().isVisible(), "causal.claims link missing");
  const howText = await page.locator("main").innerText();
  assert(/Not a causal estimate/i.test(howText), "How It Works should include what this is not");
  assert(/stable concept surface/i.test(howText), "How It Works should explain the stable concept surface");
  assert(/release filtering/i.test(howText), "How it works should mention release filtering");
  assert(/native concept vocabulary/i.test(howText), "How It Works should mention the native concept vocabulary");

  await page.goto(`${baseUrl}/faq/`, { waitUntil: "domcontentloaded" });
  await page.waitForURL(/\/how-it-works\/$/);
  await page.goto(`${baseUrl}/validation/`, { waitUntil: "domcontentloaded" });
  await page.waitForURL(/\/how-it-works\/$/);

  await page.goto(`${baseUrl}/graph/`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-role="graph-canvas"]');
  await textDoesNotContain(page, ["NaN", "undefined", "sqlite3.OperationalError"]);
  assert(await page.getByRole("heading", { name: /Use the literature map when you want to read one topic in more detail/i }).isVisible(), "Literature Map page hero missing");
  const graphHeroText = await page.locator("main").innerText();
  assert(/Most visitors should start with Research Questions/i.test(graphHeroText), "Literature Map page should point users back to Research Questions");
  assert(await page.getByRole("heading", { name: /Selected topic/i }).isVisible(), "Selected topic panel missing");

  const focusedNodeCount = await page.locator("[data-node-id]").count();
  assert(focusedNodeCount > 0, "Focused literature map rendered no nodes");
  await page.getByRole("button", { name: /Show full map/i }).click();
  await page.waitForTimeout(300);
  const globalNodeCount = await page.locator("[data-node-id]").count();
  assert(globalNodeCount > focusedNodeCount, "Full map should render more nodes than focused mode");
  await page.getByRole("button", { name: /Return to focused view/i }).click();
  await page.waitForTimeout(300);

  await page.getByPlaceholder("Search labels or aliases").fill("income / economic growth");
  await page.getByRole("button", { name: /income \/ economic growth/i }).first().click();
  await page.waitForTimeout(300);
  const inspectorText = await page.locator('[data-role="selected-concept"]').innerText();
  assert(!/\bNA\b/.test(inspectorText), "Selected topic panel still renders NA");
  assert(!/NaN/.test(inspectorText), "Selected topic panel still renders NaN");
  assert(/Common contexts:/i.test(inspectorText), "Selected topic panel missing readable settings");
  const summaryText = await page.locator('[data-role="selection-list-view"]').innerText();
  assert(/Topic summary/i.test(summaryText), "Text summary panel missing");
  const nearbyQuestionsText = await page.locator('[data-role="selected-opportunities"]').innerText();
  assert(!nearbyQuestionsText.includes("→"), "Nearby research questions should not use arrow syntax");

  await page.goto(`${baseUrl}/advanced/`, { waitUntil: "networkidle" });
  assert(await page.getByRole("heading", { name: /Go deeper only when your question needs more context/i }).isVisible(), "Advanced page missing");

  await page.goto(`${baseUrl}/method/`, { waitUntil: "networkidle" });
  assert(await page.getByRole("link", { name: /How it works/i }).first().isVisible(), "Method should link back to How it works");
  assert(await page.getByRole("link", { name: /Read paper on the web/i }).first().isVisible(), "Method should link to the paper");

  await page.goto(`${baseUrl}/compare/`, { waitUntil: "domcontentloaded" });
  await page.waitForURL(/\/method\/$/);

  await page.goto(`${baseUrl}/downloads/`, { waitUntil: "networkidle" });
  assert(await page.getByRole("link", { name: /Paper overview/i }).first().isVisible(), "Downloads page should expose the paper overview");
  assert(await page.getByRole("link", { name: /Working paper PDF/i }).first().isVisible(), "Downloads page should expose the working paper");
  assert(await page.getByRole("link", { name: /Extended abstract PDF/i }).isVisible(), "Downloads page should expose the extended abstract");
  assert(await page.getByText(/frontiergraph-economics-public\.db/i).isVisible(), "Downloads page should show the public DB bundle");
  assert(await page.getByText(/Tier 1/i).first().isVisible(), "Downloads page should show tiered releases");

  await page.goto(`${baseUrl}/paper/`, { waitUntil: "networkidle" });
  assert(await page.getByRole("heading", { name: /What FrontierGraph Finds/i }).first().isVisible(), "Paper overview missing");
  await page.goto(`${baseUrl}/paper/full/`, { waitUntil: "networkidle" });
  assert(await page.getByRole("heading", { name: /What Should Economics Work On Next/i }).first().isVisible(), "Full paper missing");

  assert(errors.length === 0, `Browser errors found:\n${errors.join("\n")}`);
  await browser.close();
  console.log("playwright smoke passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
