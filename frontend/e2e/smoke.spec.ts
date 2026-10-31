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
