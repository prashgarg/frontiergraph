import { chromium } from "playwright";

const baseUrl = process.argv[2] || "http://127.0.0.1:8511";

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

async function assertReadableText(page, selector, label) {
  const color = await page.locator(selector).first().evaluate((el) => getComputedStyle(el).color);
  assert(color !== "rgb(255, 255, 255)", `${label} should not render in white`);
}

async function main() {
  const browser = await chromium.launch({
    channel: "chrome",
    headless: true,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  const errors = [];
  const ignoredConsolePatterns = [
    /Download Button source error - 404/i,
    /Failed to load resource: the server responded with a status of 404 \(\)/i,
  ];
  page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (ignoredConsolePatterns.some((pattern) => pattern.test(text))) return;
    errors.push(`console:${text}`);
  });

  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("h1", { timeout: 30000 });
  await page.getByText(/Search questions/i).first().waitFor({ timeout: 30000 });
  await textDoesNotContain(page, ["Traceback", "sqlite3.OperationalError", "ModuleNotFoundError"]);
  assert(await page.getByRole("heading", { name: /Read one question or topic at a time/i }).isVisible(), "App hero missing");
  assert(await page.getByText(/Start with/i).first().isVisible(), "Primary view switch missing");
  assert(await page.getByText(/Search questions/i).first().isVisible(), "Question search missing");
  assert(await page.getByText(/Choose a question/i).first().isVisible(), "Question picker missing");
  await assertReadableText(page, "label", "App form labels");
  await assertReadableText(page, '[data-testid="stMetric"] label', "Metric labels");
  await assertReadableText(page, '[data-testid="stTextInput"] input', "Search input text");

  await page.goto(`${baseUrl}/?view=concept&concept=FG3C000001`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("h1", { timeout: 30000 });
  await page.getByText(/Search topics/i).first().waitFor({ timeout: 30000 });
  await page.getByText(/economic growth/i).first().waitFor({ timeout: 30000 });
  await textDoesNotContain(page, ["Traceback", "sqlite3.OperationalError"]);
  assert(await page.getByText(/Search topics/i).first().isVisible(), "Concept view input missing");
  assert(await page.getByText(/Choose a topic/i).first().isVisible(), "Concept picker missing");
  assert(await page.getByText(/economic growth/i).first().isVisible(), "Concept deep link did not resolve");
  await page.getByText(/Local map/i).first().waitFor({ timeout: 30000 });
  await page.getByText(/Questions touching this topic/i).first().waitFor({ timeout: 30000 });
  assert(await page.getByText(/Local map/i).first().isVisible(), "Concept local map missing");
  assert(await page.getByText(/Questions touching this topic/i).first().isVisible(), "Concept opportunity table missing");
  assert((await page.getByRole("button", { name: /Open question/i }).count()) >= 1, "Concept view should surface question actions");

  await page.goto(`${baseUrl}/?view=compare&pairs=FG3C000010__FG3C003971,FG3C000003__FG3C000208`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("h1", { timeout: 30000 });
  await page.getByText(/Choose 2 to 4 questions/i).first().waitFor({ timeout: 30000 });
  await textDoesNotContain(page, ["Traceback", "sqlite3.OperationalError"]);
  assert(await page.getByText(/Choose 2 to 4 questions/i).first().isVisible(), "Compare multiselect missing");

  assert(errors.length === 0, `Browser errors found:\n${errors.join("\n")}`);
  await browser.close();
  console.log("streamlit smoke passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
