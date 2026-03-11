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
  await textDoesNotContain(page, ["NaN", "undefined", "sqlite3.OperationalError", "are close in the surrounding graph"]);
  assert(await page.getByRole("heading", { name: "Where do we go next?" }).isVisible(), "Homepage hero did not update");
  assert(await page.locator("[data-theme-toggle]").isVisible(), "Theme toggle missing on home");
  assert(
    await page.getByRole("navigation").getByRole("link", { name: /^Advanced$/ }).isVisible(),
    "Advanced nav missing on home",
  );
  assert(
    (await page.locator('[data-role="home-curated-opportunities"] [data-role="curated-opportunity-card"]').count()) === 4,
    "Homepage should show exactly 4 curated opportunity cards",
  );
  assert(await page.getByText(/Next study:/i).first().isVisible(), "Curated cards should expose Next study");
  await page.getByPlaceholder("Search labels or aliases").fill("income / economic growth");
  await page.getByRole("button", { name: /income \/ economic growth/i }).first().click();
  await page.getByRole("link", { name: /see nearby opportunities/i }).waitFor();

  await page.goto(`${baseUrl}/opportunities/?q=${encodeURIComponent("income / economic growth")}`, {
    waitUntil: "networkidle",
  });
  await page.waitForSelector(".lookup-shell");
  await textDoesNotContain(page, [
    "NaN",
    "undefined",
    "sqlite3.OperationalError",
    "are close in the surrounding graph",
    "Start with a bridge review or cross-field pilot.",
  ]);
  assert(
    (await page.locator('[data-role="opportunities-curated-front-set"] [data-role="curated-opportunity-card"]').count()) === 8,
    "Opportunities page should show exactly 8 curated opportunity cards",
  );
  assert(await page.getByText(/broad measure of ecological carrying capacity/i).first().isVisible(), "Glossary subtitle did not render");
  const rankedSection = page.locator('[data-role="overall-ranked-opportunities"]');
  assert(!((await rankedSection.innerText()).includes("→")), "Ranked opportunities should not use arrow syntax");
  await page.getByRole("button", { name: /ready for follow-up/i }).click();
  await page.waitForTimeout(250);
  assert(await page.getByText(/No visible pairs match the current filter combination/i).isVisible(), "Filter empty state did not render");
  await page.getByRole("button", { name: /ready for follow-up/i }).click();
  await page.waitForTimeout(250);
  const firstEvidence = page.locator('[data-role="overall-ranked-opportunities"] [data-role="opportunity-evidence"]').first();
  await firstEvidence.locator("summary").click();
  await page.waitForTimeout(200);
  assert(/Nearby linking ideas:/i.test(await firstEvidence.innerText()), "Evidence drawer did not open with mediator labels");

  const lookupText = await page.locator('[data-role="concept-panel"]').innerText();
  assert(!/\bNA\b/.test(lookupText), "Concept lookup still renders NA");
  assert(/incoming|papers|nearby concepts/i.test(lookupText), "Concept lookup did not render readable metadata");
  const lookupOpportunityText = await page.locator('[data-role="opportunities-panel"]').innerText();
  assert(!lookupOpportunityText.includes("→"), "Concept lookup opportunities should not use arrow syntax");

  await page.goto(`${baseUrl}/graph/`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-role="graph-canvas"]');
  await page.getByRole("button", { name: /show full map/i }).waitFor();
  await page.waitForTimeout(500);
  const focusedNodeCount = await page.locator("[data-node-id]").count();
  assert(focusedNodeCount > 0, "Focused graph mode rendered no nodes");
  await page.getByRole("button", { name: /show full map/i }).click();
  await page.waitForTimeout(400);
  const globalNodeCount = await page.locator("[data-node-id]").count();
  assert(globalNodeCount > focusedNodeCount, "Full map should render more nodes than focused mode");
  await page.getByRole("button", { name: /return to focused view/i }).click();
  await page.waitForTimeout(400);
  const focusedNodeCountAgain = await page.locator("[data-node-id]").count();
  assert(focusedNodeCountAgain === focusedNodeCount, "Returning to focused view should restore the smaller node set");

  const graphSearch = page.locator('[data-role="search-input"]');
  await graphSearch.fill("income / economic growth");
  await page.getByRole("button", { name: /income \/ economic growth/i }).first().click();
  await page.waitForTimeout(400);

  const inspectorText = await page.locator('[data-role="selected-concept"]').innerText();
  assert(!/\bNA\b/.test(inspectorText), "Graph inspector still renders NA");
  assert(!/NaN/.test(inspectorText), "Graph inspector still renders NaN");
  assert(/incoming observed links/i.test(inspectorText), "Graph inspector missing readable link counts");
  assert(
    /Focus summary/i.test(await page.locator('[data-role="selection-list-view"]').innerText()),
    "Graph text view did not render the keyboard-readable focus summary",
  );
  const graphOpportunitiesText = await page.locator('[data-role="selected-opportunities"]').innerText();
  assert(!graphOpportunitiesText.includes("→"), "Graph nearby opportunities should not use arrow syntax");

  const viewport = page.locator('[data-role="graph-viewport"]');
  const initialTransform = await viewport.getAttribute("transform");
  const canvas = page.locator('[data-role="graph-canvas"]');
  const canvasBox = await canvas.boundingBox();
  assert(canvasBox, "Graph canvas has no bounding box");

  await page.getByRole("button", { name: /zoom out/i }).click();
  await page.waitForTimeout(250);
  const zoomTransform = await viewport.getAttribute("transform");
  assert(zoomTransform && zoomTransform !== initialTransform, "Zoom button did not change graph viewport");

  await page.mouse.move(canvasBox.x + 20, canvasBox.y + 20);
  await page.mouse.down();
  await page.mouse.move(canvasBox.x + 160, canvasBox.y + 120, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(250);
  const panTransform = await viewport.getAttribute("transform");
  assert(panTransform && panTransform !== zoomTransform, "Pan did not change graph viewport");

  const firstNode = page.locator("[data-node-id]").first();
  const firstCircle = page.locator("[data-node-id] circle").first();
  const nodeId = await firstNode.getAttribute("data-node-id");
  assert(nodeId, "No graph nodes rendered");
  const beforeCx = await firstCircle.getAttribute("cx");
  const beforeCy = await firstCircle.getAttribute("cy");
  const nodeBox = await firstCircle.boundingBox();
  assert(nodeBox, "Node circle has no bounding box");

  await page.getByRole("button", { name: /adjust layout/i }).click();
  await firstCircle.dispatchEvent("mousedown", {
    button: 0,
    bubbles: true,
    clientX: nodeBox.x + nodeBox.width / 2,
    clientY: nodeBox.y + nodeBox.height / 2,
  });
  await page.mouse.move(nodeBox.x + nodeBox.width / 2 + 60, nodeBox.y + nodeBox.height / 2 + 40, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(300);
  const circle = page.locator(`[data-node-id="${nodeId}"] circle`);
  const afterCx = await circle.getAttribute("cx");
  const afterCy = await circle.getAttribute("cy");
  assert(beforeCx !== afterCx || beforeCy !== afterCy, "Layout drag did not move a node");

  await page.getByRole("button", { name: /reset layout/i }).click();
  await page.waitForTimeout(300);
  const resetCx = await circle.getAttribute("cx");
  const resetCy = await circle.getAttribute("cy");
  assert(resetCx === beforeCx && resetCy === beforeCy, "Reset layout did not restore node position");

  await page.goto(`${baseUrl}/advanced/`, { waitUntil: "networkidle" });
  assert(await page.getByRole("heading", { name: /keep the main path simple/i }).isVisible(), "Advanced page did not render");

  await page.goto(`${baseUrl}/compare/`, { waitUntil: "networkidle" });
  assert(await page.getByRole("heading", { name: /compare ontology views only when your question needs a sensitivity check/i }).isVisible(), "Compare page did not render");

  assert(errors.length === 0, `Browser errors found:\n${errors.join("\n")}`);
  await browser.close();
  console.log("playwright smoke passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
