import { expect, test } from '@playwright/test';

const FRONTEND_ORIGIN = 'http://127.0.0.1:4373';
const VIEWPORTS = [
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'laptop-1024', width: 1024, height: 768 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'mobile-390', width: 390, height: 844 },
] as const;

for (const viewport of VIEWPORTS) {
  test(`login form remains inside ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.route(/^https?:\/\/(?!127\.0\.0\.1(?::\d+)?|localhost(?::\d+)?)/, (route) =>
      route.abort(),
    );
    await page.goto(`${FRONTEND_ORIGIN}/#/login`, { waitUntil: 'domcontentloaded' });

    const form = page.locator('.login-form');
    await expect(page.getByText('欢迎登录', { exact: true })).toBeVisible();
    await expect(form).toBeVisible();

    const bounds = await form.boundingBox();
    expect(bounds).not.toBeNull();
    if (!bounds) return;

    expect(bounds.x).toBeGreaterThanOrEqual(-1);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(viewport.width + 1);
    expect(bounds.y).toBeGreaterThanOrEqual(-1);
    expect(bounds.y).toBeLessThan(viewport.height);
  });
}
