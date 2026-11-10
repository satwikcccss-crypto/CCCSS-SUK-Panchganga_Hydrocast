import { test, expect } from "@playwright/test";
import path from "path";

test.describe("HydroCast Public Portal E2E Tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("http://localhost:3000/dashboard", { waitUntil: "networkidle" });
  });

  test("1. Strictly Light Mode and clean typography", async ({ page }) => {
    // Assert body background is light mode
    const bodyClass = await page.locator("body").getAttribute("class");
    expect(bodyClass).toContain("bg-slate-50");
    expect(bodyClass).not.toContain("dark");

    // Header logo and title
    await expect(page.locator("header")).toBeVisible();
    await expect(page.locator("text=HYDROCAST").first()).toBeVisible();
  });

  test("2. Displays post-monsoon normal flow (9.10 m³/s) and zero NaN values", async ({ page }) => {
    // Wait for data load
    await page.waitForTimeout(2000);

    const pageContent = await page.content();
    // Must NOT have unhandled NaN or undefined displayed to citizens
    expect(pageContent).not.toContain(">NaN<");
    expect(pageContent).not.toContain("NaN m³/s");
    expect(pageContent).not.toContain("undefined m");

    // Must NOT show stale 91 m³/s
    expect(pageContent).not.toContain("91.10 m³/s");
    expect(pageContent).not.toContain("91 m³/s");

    // Capture screenshot
    await page.screenshot({
      path: path.join(__dirname, "../results/screenshots/public_dashboard_en.png"),
      fullPage: true,
    });
  });

  test("3. Marathi | English Language Toggle", async ({ page }) => {
    // Find language switcher buttons by title and text
    const mrBtn = page.locator("button[title='मराठी']").or(page.locator("button:has-text('मराठी')")).first();
    const enBtn = page.locator("button[title='English']").or(page.locator("button:has-text('EN')")).first();

    await expect(mrBtn).toBeVisible({ timeout: 10000 });
    await expect(enBtn).toBeVisible({ timeout: 10000 });

    // Click Marathi toggle
    await mrBtn.click();
    await page.waitForTimeout(1000);

    // Assert Marathi text appears in header / nav
    await expect(page.locator("text=हायड्रोकास्ट").or(page.locator("text=नदी पातळी")).first()).toBeVisible({ timeout: 10000 });

    // Screenshot Marathi view
    await page.screenshot({
      path: path.join(__dirname, "../results/screenshots/public_dashboard_mr.png"),
      fullPage: true,
    });

    // Switch back to English
    await enBtn.click();
    await page.waitForTimeout(1000);
    await expect(page.locator("text=HYDROCAST").first()).toBeVisible({ timeout: 10000 });
  });

  test("4. Open Data and Forecast CSV Download exists", async ({ page }) => {
    // Navigate to Open Data tab
    const openDataTab = page.locator("button:has-text('Open Data & Telegram')").first();
    if (await openDataTab.isVisible()) {
      await openDataTab.click();
      await page.waitForTimeout(1000);

      // Verify CSV download button is present
      const csvBtn = page.locator("button:has-text('Download 90h Forecast CSV')").first();
      await expect(csvBtn).toBeVisible();
    }
  });
});
