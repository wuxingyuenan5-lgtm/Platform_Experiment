import { expect, test, type Page } from '@playwright/test';

import { mockPlatformVisualRoutes } from './platformVisualFixtures';

const FRONTEND_ORIGIN = 'http://127.0.0.1:4373';

function requiredEnvironment(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required for the product data closure suite`);
  return value;
}

function absoluteUrl(route: string): string {
  return `${FRONTEND_ORIGIN}/#${route}`;
}

async function preparePage(page: Page): Promise<void> {
  await page.route(/^https?:\/\/(?!127\.0\.0\.1(?::\d+)?|localhost(?::\d+)?)/, (route) =>
    route.abort(),
  );
  await mockPlatformVisualRoutes(page);
}

async function loginEmployee(page: Page): Promise<void> {
  await page.goto(absoluteUrl('/login'));
  await page.getByPlaceholder('请输入账号').fill('e2e_employee_1');
  await page.getByPlaceholder('请输入密码').fill(requiredEnvironment('E2E_SHARED_PASSWORD'));
  const response = page.waitForResponse(
    (item) => item.url().endsWith('/api/v1/auth/login') && item.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '登录', exact: true }).click();
  expect((await response).ok()).toBeTruthy();
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/, { timeout: 20_000 });
}

async function expectUnavailableSource(
  page: Page,
  route: string,
  title: string,
  source: string,
): Promise<void> {
  await page.goto(absoluteUrl(route));
  await expect(page.getByText(title, { exact: true })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(source, { exact: false })).toBeVisible();
}

test('formal product surfaces disclose data gaps instead of demo values', async ({ page }) => {
  await preparePage(page);
  await loginEmployee(page);

  await expectUnavailableSource(
    page,
    '/home/index',
    '全球市场概览尚未配置',
    'not-configured: dashboard-market-aggregate',
  );

  await expectUnavailableSource(
    page,
    '/financial-ai/index',
    '金融AI分析数据源尚未配置',
    'not-configured: financial-ai-provider',
  );
  await expect(page.getByText('铜价情景概率', { exact: false })).toHaveCount(0);

  await expectUnavailableSource(
    page,
    '/strategy/management',
    '策略管理目录尚未配置',
    'not-configured: strategy-catalog-owner',
  );
  await expect(page.getByText('account_mt5_demo', { exact: false })).toHaveCount(0);

  await expectUnavailableSource(
    page,
    '/news-calendar/news',
    '新闻聚合Provider尚未配置',
    'not-configured: news-aggregation-provider',
  );

  await expectUnavailableSource(
    page,
    '/news-calendar/wealth',
    '理财活动数据源尚未配置',
    'not-configured: wealth-campaign-provider',
  );
  await expect(page.getByText('15.00%', { exact: true })).toHaveCount(0);

  await page.goto(absoluteUrl('/notification/index'));
  await expect(page.getByRole('heading', { name: '消息通知' })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole('button', { name: '全部已读' })).toHaveCount(0);
  await expect(page.getByText('只读', { exact: true })).toBeVisible();

  await page.goto(absoluteUrl('/hedge-board/gold'));
  await expect(page.getByText('静态设计稿', { exact: false }).first()).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByText('static_design_isolated', { exact: false })).toBeVisible();
});
