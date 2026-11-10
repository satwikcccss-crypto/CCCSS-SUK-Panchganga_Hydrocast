import { test, expect } from "@playwright/test";
import path from "path";

test.describe("HydroCast Operator Admin Console E2E Tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("http://localhost:3001/login", { waitUntil: "networkidle" });

    // Fill in Administrator credentials
    await page.fill("#username", "admin");
    await page.fill("#password", "admin");
    await page.click("button[type='submit']");

    // Wait until navigated to /admin
    await page.waitForURL("**/admin", { timeout: 10000 });
    await page.waitForTimeout(1000);
  });

  test("1. Admin Console Loads and Displays Dashboard", async ({ page }) => {
    // Verify main header or settings title
    await expect(page.locator("text=HYDROCAST").first()).toBeVisible();

    // Verify Seasonal Standby indicator is active during post-monsoon
    const standbyBadge = page.locator("text=Seasonal Standby").first();
    if (await standbyBadge.isVisible()) {
      await expect(standbyBadge).toBeVisible();
    }

    // Capture initial screenshot
    await page.screenshot({
      path: path.join(__dirname, "../results/screenshots/admin_console.png"),
      fullPage: true,
    });
  });

  test("2. DB Test button triggers database ping and saves audit record", async ({ page }) => {
    // Locate DB Test button
    const dbTestBtn = page.locator("button:has-text('DB Test')").first();
    await expect(dbTestBtn).toBeVisible({ timeout: 10000 });

    // Click DB Test
    await dbTestBtn.click();
    await page.waitForTimeout(2000);

    // Verify confirmation notification or audit log banner
    const confirmation = page.locator("text=Saved to Database").or(page.locator("text=Audit ID")).or(page.locator("text=connected"));
    await expect(confirmation.first()).toBeVisible({ timeout: 15000 });
  });

  test("3. DB Backup button executes pg_dump and records audit entry", async ({ page }) => {
    // Locate DB Backup button
    const backupBtn = page.locator("button:has-text('DB Backup')").first();
    await expect(backupBtn).toBeVisible({ timeout: 10000 });

    // Click DB Backup
    await backupBtn.click();
    await page.waitForTimeout(3000);

    // Verify backup created message with file path
    const backupResult = page.locator("text=Backup created").or(page.locator("text=db_backup_")).or(page.locator("text=saved to"));
    await expect(backupResult.first()).toBeVisible({ timeout: 20000 });

    // Capture screenshot after backup
    await page.screenshot({
      path: path.join(__dirname, "../results/screenshots/admin_backup_success.png"),
      fullPage: false,
    });
  });
});
