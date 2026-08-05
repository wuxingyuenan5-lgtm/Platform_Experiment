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

async function expectDataState(
  page: Page,
  route: string,
  state: 'sample' | 'unavailable',
  source: string,
): Promise<void> {
  await page.goto(absoluteUrl(route));
  const surface = page
    .locator(`[data-product-state="${state}"][data-actionable="false"]`)
    .first();
  await expect(surface).toBeVisible({ timeout: 20_000 });
  await expect(surface.getByText(source, { exact: false }).first()).toBeVisible();
}

test('restored formal product surfaces disclose state, source and non-actionability', async ({
  page,
}) => {
  await preparePage(page);
  await loginEmployee(page);

  await expectDataState(page, '/home/index', 'sample', 'sample:dashboard-restoration');
  await expect(page.getByTestId('dashboard-original-structure')).toBeVisible();
  for (const title of [
    '全球市场概览',
    '投资组合总览',
    '市场脉搏',
    '组合概览',
    '策略概览',
    '重要日历',
  ]) {
    await expect(page.getByText(title, { exact: true }).first()).toBeVisible();
  }
  await expect(page.getByText('实时数据', { exact: true })).toHaveCount(0);

  await expectDataState(
    page,
    '/strategy/management',
    'sample',
    'sample:strategy-management-restoration',
  );
  await expect(page.getByTestId('strategy-management-original-structure')).toBeVisible();
  await expect(page.getByTestId('strategy-pnl-panel')).toBeVisible();
  await page.getByRole('button', { name: '账户资金', exact: true }).click();
  await expect(page.getByTestId('strategy-kpi-grid')).toBeVisible();
  await expect(page.getByTestId('strategy-capital-finance-board')).toBeVisible();
  await page.getByRole('button', { name: '订单信息', exact: true }).click();
  await expect(page.getByTestId('strategy-records-panel')).toBeVisible();
  await expect(page.getByRole('button', { name: '启停策略' })).toBeDisabled();
  await expect(page.getByRole('button', { name: '部署策略' })).toBeDisabled();

  await expectDataState(
    page,
    '/strategy/platform?desk=funding',
    'sample',
    'sample:funding-carry-research',
  );
  await expect(page.getByTestId('funding-market-board')).toBeVisible();
  await expect(page.getByTestId('funding-chart-panel')).toBeVisible();
  await expect(page.getByTestId('funding-detail-panel')).toBeVisible();
  await page.getByRole('button', { name: '交易执行', exact: true }).click();
  await expect(page.getByTestId('funding-order-panel')).toBeVisible();
  await expect(page.getByRole('button', { name: '提交组合订单' })).toBeDisabled();

  await expectDataState(
    page,
    '/strategy/platform?desk=crossSpread',
    'sample',
    'sample:spread-research',
  );
  await expect(page.getByTestId('spread-analysis-workspace-header')).toBeVisible();
  await expect(page.getByTestId('spread-analysis-overview')).toBeVisible();
  await expect(page.getByTestId('spread-research-chart')).toBeVisible();
  await expect(page.getByTestId('spread-statistics-section')).toBeVisible();
  await page.getByRole('button', { name: '交易执行', exact: true }).click();
  await expect(page.getByText('正式 CrossVenueExecutionWorkspace', { exact: true })).toBeVisible();
  await expect(page.getByText('ACK/Fill 区分', { exact: false })).toBeVisible();

  await expectDataState(
    page,
    '/financial-ai/index',
    'unavailable',
    'not-configured:financial-ai-provider',
  );
  await expect(page.getByTestId('financial-ai-original-structure')).toBeVisible();
  await expect(page.getByText('暂无模型结果', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '运行分析' })).toBeDisabled();
  await expect(page.getByText('模型运行成功', { exact: false })).toHaveCount(0);

  await expectDataState(page, '/news-calendar/news', 'sample', 'sample:news-digest');
  await expect(page.getByRole('heading', { name: '新闻日历与理财' })).toBeVisible();
  await expect(page.getByTestId('news-digest-original-structure')).toBeVisible();
  await expect(page.getByText('非实时', { exact: true }).first()).toBeVisible();

  await expectDataState(page, '/news-calendar/wealth', 'sample', 'sample:wealth-campaigns');
  await expect(page.getByTestId('wealth-original-structure')).toBeVisible();
  await expect(page.getByRole('button', { name: '不可申购' }).first()).toBeDisabled();

  await page.goto(absoluteUrl('/settings/index'));
  await expect(page.getByTestId('settings-original-structure')).toBeVisible();
  await expect(
    page.getByText('not-configured:settings-write-owner', { exact: false }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: '保存（Owner未配置）' })).toBeDisabled();

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
