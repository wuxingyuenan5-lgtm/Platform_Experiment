import { expect, test, type Page } from '@playwright/test';

import { mockPlatformVisualRoutes } from './platformVisualFixtures';

const FRONTEND_ORIGIN = process.env.PLATFORM_VISUAL_FRONTEND_ORIGIN;
if (!FRONTEND_ORIGIN) throw new Error('Run with playwright.platform-visual.config.ts');

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

test('current product surfaces distinguish sample, unavailable and permission boundaries', async ({
  page,
}) => {
  await preparePage(page);
  await loginEmployee(page);
  const tradingWrites: string[] = [];
  page.on('request', (request) => {
    if (
      request.method() !== 'GET' &&
      /\/api\/v1\/(trading|trade-commands|live-trading)/.test(request.url())
    )
      tradingWrites.push(request.url());
  });

  await page.goto(absoluteUrl('/home/index'));
  await expect(page.getByTestId('dashboard-original-structure')).toBeVisible();
  await expect(page.getByRole('heading', { name: '我的工作台', exact: true })).toBeVisible();
  await expect(page.getByText('非实时样例', { exact: true })).toBeVisible();
  await expect(page.locator('.market-mini-grid strong').first()).toHaveText('--');
  await expect(page.getByText('实时数据', { exact: true })).toHaveCount(0);

  await page.goto(absoluteUrl('/strategy/management?desk=crossSpread&section=capital'));
  await expect(page.getByTestId('strategy-kpi-grid')).toBeVisible();
  await expect(page.locator('[data-write-action="true"]')).toHaveCount(0);
  await page.getByRole('button', { name: '订单信息', exact: true }).click();
  await expect(page.locator('.records-card')).toBeVisible();

  await page.goto(absoluteUrl('/strategy/platform?desk=funding&section=execution'));
  await expect(page.getByTestId('funding-order-panel')).toBeVisible();
  await expect(page.getByRole('button', { name: '市价开仓', exact: true })).toBeDisabled();
  await page.goto(absoluteUrl('/strategy/platform?desk=crossSpread&section=execution'));
  await page.getByRole('button', { name: '开多价差', exact: true }).click();
  await expect(page.locator('strong').filter({ hasText: /^仅 CEO 可下达交易指令$/ })).toBeVisible();
  await expect(page.getByText('确认价差指令', { exact: true })).toHaveCount(0);

  await page.route('**/api/v1/research/a-share/dashboard*', (route) =>
    route.fulfill({
      status: 503,
      json: { detail: '市场底稿暂不可用' },
    }),
  );
  await page.goto(absoluteUrl('/financial-ai/index'));
  await expect(page.getByRole('heading', { name: '当日市场复盘', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '更新数据', exact: true }).click();
  await expect(page.locator('.notice.error')).toBeVisible();
  await expect(page.getByRole('button', { name: '生成 AI 复盘', exact: true })).toBeDisabled();
  await expect(page.locator('.metric-grid')).toHaveCount(0);
  await expect(page.getByText('模型运行成功', { exact: false })).toHaveCount(0);

  await page.goto(absoluteUrl('/news-calendar/news'));
  await expect(page).toHaveURL(/financial-ai\/news-radar/);
  await expect(page.getByRole('heading', { name: '资讯雷达', exact: true })).toBeVisible();
  await page.getByRole('button', { name: /^事件概率/ }).click();
  await expect(page.getByRole('heading', { name: '关键事件概率', exact: true })).toBeVisible();
  await page.goto(absoluteUrl('/news-calendar/wealth'));
  const wealth = page.getByTestId('crypto-wealth-panel');
  await expect(wealth).toBeVisible();
  await expect(wealth).toContainText('暂无已核实的活动数据');
  await expect(wealth.locator('.wealth-row')).toHaveCount(0);
  await expect(wealth.getByRole('button', { name: /申购/ })).toHaveCount(0);

  await page.goto(absoluteUrl('/settings/profile'));
  await expect(page.getByTestId('settings-original-structure')).toBeVisible();
  await expect(page.getByText('当前浏览器 Session', { exact: true })).toBeVisible();
  await expect(
    page
      .getByRole('article')
      .filter({ hasText: '本人资料与头像' })
      .getByRole('button', { name: '进入个人账号', exact: true }),
  ).toBeVisible();
  await page.goto(absoluteUrl('/notification/index'));
  await expect(page.getByRole('heading', { name: '消息通知' })).toBeVisible();
  await expect(page.getByRole('button', { name: '全部已读' })).toHaveCount(0);
  await expect(page.getByText('只读', { exact: true })).toBeVisible();
  await page.goto(absoluteUrl('/hedge-board/gold'));
  await expect(page.locator('.research-module')).toBeVisible();
  await expect(page.getByText('static_design_isolated', { exact: false })).toHaveCount(0);
  expect(tradingWrites).toEqual([]);
});
