import { test, expect } from "@playwright/test";

test("root redirects to the dashboard", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("dashboard renders the HydroCast shell", async ({ page }) => {
  const response = await page.goto("/dashboard");
  expect(response?.status()).toBe(200);

  await expect(page).toHaveTitle(/HydroCast/i);
  await expect(page.getByText("HYDROCAST", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/Panchganga Basin/).first()).toBeVisible();
});

test("visitor counter renders the persisted API counts", async ({ page }) => {
  await page.route("**/api/v1/visits/record", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        daily: 7,
        total: 1234,
        persisted: true,
        source: "supabase",
      }),
    });
  });

  await page.goto("/dashboard");

  // The compact header widget exposes the value as a title attribute.
  await expect(page.locator('[title="Total visits: 1,234"]')).toBeVisible();
});
