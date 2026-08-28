/**
 * Drives the running site in a real browser and saves screenshots.
 *
 * Doubles as demo-asset generation: the PNGs it writes to frontend/shots/ are
 * ready to drop into the SIH presentation deck.
 *
 * Usage (backend must already be running on :8000):
 *     node scripts/capture.mjs
 *     node scripts/capture.mjs http://127.0.0.1:5173     # against the dev server
 */

import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const BASE = process.argv[2] ?? "http://127.0.0.1:8000";
// fileURLToPath, not .pathname: the latter leaves spaces percent-encoded, which
// on a path like "…/SIH 2026/…" silently creates a literal "SIH%202026" folder.
const OUT = fileURLToPath(new URL("../shots/", import.meta.url));
const VIEWPORT = { width: 1440, height: 1000 };

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: VIEWPORT, deviceScaleFactor: 2 });

const problems = [];
page.on("console", (message) => {
  if (message.type() === "error") problems.push(`console: ${message.text()}`);
});
page.on("pageerror", (error) => problems.push(`pageerror: ${error.message}`));

// The detail drawer is `position: fixed`, so a fullPage screenshot renders it
// stranded at the current scroll offset instead of covering the view. Drawer
// shots are therefore viewport-only.
const shot = async (name, { fullPage = true } = {}) => {
  const path = `${OUT}${name}.png`;
  if (!fullPage) await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path, fullPage });
  console.log(`  saved ${name}.png`);
};

const nav = (name) => page.getByRole("tab", { name, exact: true });

try {
  console.log(`Opening ${BASE}`);
  await page.goto(BASE, { waitUntil: "networkidle", timeout: 60_000 });

  // ---- Overview: what is indexed, against the real BIS totals ----
  // Scoped to the status bar: "standards indexed" also appears as a KPI label.
  await page.locator(".status__item").first().waitFor({ timeout: 30_000 });
  await page.locator(".coverage__row").first().waitFor({ timeout: 30_000 });
  const indexed = await page.locator(".status__item strong").first().innerText();
  const departments = await page.locator(".coverage__row").count();
  console.log(`  ${indexed} standards indexed across ${departments} departments`);
  await shot("01-overview");

  // ---- Recommendation flow (the flagship demo) ----
  // Helmets rather than flats: it is the clearest mandatory-vs-voluntary split.
  console.log("Recommend: two-wheeler helmets");
  await nav("Find my standards").click();
  await page.getByRole("button", { name: "Two-wheeler helmets" }).click();
  await page.getByRole("button", { name: "Find standards" }).click();
  await page.locator(".cards--ranked .card").first().waitFor({ timeout: 120_000 });
  const mandatory = await page.locator(".group--mandatory .card").count();
  const codes = await page.locator(".cards--ranked .is-number").allInnerTexts();
  console.log(`  ${codes.length} recommendations (${mandatory} mandatory): ${codes.join(" | ")}`);
  await shot("02-recommendations");

  // ---- Detail drawer: certification pathway + reference graph ----
  console.log("Drawer: certification pathway");
  await page.locator(".group--mandatory .is-number--link").first().click();
  await page.locator(".drawer__panel .steps li").first().waitFor({ timeout: 30_000 });
  console.log(`  ${await page.locator(".drawer__panel .steps li").count()} certification steps`);
  await shot("03-certification", { fullPage: false });
  await page.locator(".drawer__head .btn").click();

  // ---- Tender analyser (SIH26108's core ask) ----
  console.log("Tender: outdated + missing references");
  await nav("Check a tender").click();
  await page.getByRole("button", { name: "Sample building tender" }).click();
  await page.getByRole("button", { name: "Analyse specification" }).click();
  await page.locator(".gauge").waitFor({ timeout: 120_000 });
  const outdated = await page.locator(".finding--warn .finding__list li").count();
  const missing = await page.locator(".finding--info .is-number").count();
  console.log(`  ${outdated} outdated citation(s), ${missing} missing normative ref(s)`);
  await shot("04-tender");

  // ---- Reference graph ----
  console.log("Graph: IS 456 reference neighbourhood");
  await page.getByRole("button", { name: "IS 456:2000", exact: true }).first().click();
  await page.locator(".graph").waitFor({ timeout: 30_000 });
  await page.locator(".graph").scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  console.log(`  ${await page.locator(".graph__node").count()} nodes in the graph`);
  await shot("05-graph", { fullPage: false });
  await page.locator(".drawer__head .btn").click();

  // ---- Browse the catalogue ----
  console.log("Browse: filter to standards under a QCO");
  await nav("Browse catalogue").click();
  await page.locator(".table tbody tr").first().waitFor({ timeout: 30_000 });
  await page.locator(".filters__check input").check();
  await page.waitForTimeout(500);
  console.log(`  ${await page.locator(".result__count strong").innerText()} under a QCO`);
  await shot("06-browse");

  // ---- Grounded chat ----
  console.log("Ask: drinking water quality");
  await nav("Ask a question").click();
  await page.getByRole("button", { name: "Drinking water quality" }).click();
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await page.locator(".answer").waitFor({ timeout: 120_000 });
  const cited = await page.locator(".cards .is-number").allInnerTexts();
  console.log(`  cited: ${cited.join(" | ")}`);
  await shot("07-answer");

  // ---- Honest refusal ----
  console.log("Ask: off-topic (must decline)");
  await page.getByRole("button", { name: "Off-topic (declines)" }).click();
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await page.locator(".note--empty").waitFor({ timeout: 120_000 });
  console.log("  declined as expected");
  await shot("08-declines");

  // ---- Hindi ----
  console.log("Hindi UI");
  await page.getByRole("button", { name: "हिं" }).click();
  await page.waitForTimeout(400);
  await shot("09-hindi");
  await page.getByRole("button", { name: "EN" }).click();

  // ---- Mobile ----
  console.log("Mobile viewport");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(400);
  await shot("10-mobile");

  console.log(
    problems.length
      ? `\nFAIL — browser reported ${problems.length} problem(s):\n  ${problems.join("\n  ")}`
      : "\nOK — no console errors or page exceptions.",
  );
  process.exitCode = problems.length ? 1 : 0;
} catch (error) {
  console.error(`\nFAIL — ${error.message}`);
  await shot("99-failure");
  process.exitCode = 1;
} finally {
  await browser.close();
}
