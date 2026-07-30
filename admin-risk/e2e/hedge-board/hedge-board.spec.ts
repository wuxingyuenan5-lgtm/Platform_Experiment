import { expect, test, type Browser, type Page } from '@playwright/test';

import { mockResearchRoutes } from './researchFixtures';

const FRONTEND_ORIGIN = 'http://127.0.0.1:4373';

function requiredEnvironment(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required for the hedge-board browser E2E suite`);
  return value;
}

function absoluteUrl(path: string): string {
  return `${FRONTEND_ORIGIN}/#${path}`;
}

async function loginWithUi(page: Page, username: string, password: string): Promise<void> {
  await page.goto(absoluteUrl('/login'));
  await expect(page.getByText('欢迎登录', { exact: true })).toBeVisible();
  await page.getByPlaceholder('请输入账号').fill(username);
  await page.getByPlaceholder('请输入密码').fill(password);
  const loginResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/auth/login') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '登录', exact: true }).click();
  expect((await loginResponse).ok()).toBeTruthy();
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/, { timeout: 20_000 });
}

async function openAuthenticatedPage(browser: Browser, username: string, password: string) {
  const context = await browser.newContext({ locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await context.newPage();
  await mockResearchRoutes(page);
  await loginWithUi(page, username, password);
  return { context, page };
}

async function removeExistingTestStock(page: Page) {
  const section = page.locator('#a-share-watchlist');
  const removeButton = section.getByRole('button', { name: '删除浦发银行', exact: true });
  if ((await removeButton.count()) === 0) return;
  const response = page.waitForResponse(
    (item) =>
      item.url().endsWith('/api/v1/me/research-watchlist') && item.request().method() === 'PUT',
  );
  await removeButton.click();
  expect((await response).ok()).toBeTruthy();
  await expect(section.getByRole('button', { name: '浦发银行 600000', exact: true })).toHaveCount(0);
}

test('covers A-share research workflow and account-level watchlist persistence', async ({ browser }) => {
  const username = requiredEnvironment('E2E_CEO_USERNAME');
  const password = requiredEnvironment('E2E_CEO_PASSWORD');

  const first = await openAuthenticatedPage(browser, username, password);
  await first.page.goto(absoluteUrl('/hedge-board/a-share'));

  await expect(first.page.getByRole('heading', { name: '大盘表现' })).toBeVisible();
  await expect(first.page.getByRole('heading', { name: '大盘广度' })).toBeVisible();
  await expect(first.page.getByRole('heading', { name: '市场明细' })).toBeVisible();
  await expect(first.page.getByRole('heading', { name: '申万板块' })).toBeVisible();
  await expect(first.page.getByRole('heading', { name: '短线情绪' })).toBeVisible();
  await expect(first.page.getByRole('heading', { name: '自选股' })).toBeVisible();
  await expect(first.page.getByText('账号已同步', { exact: true })).toBeVisible();

  await first.page.getByRole('button', { name: /全部申万二级行业/ }).click();
  await first.page.getByLabel('搜索二级行业').fill('半导体');
  await expect(first.page.getByText('显示 1 / 2 个行业')).toBeVisible();
  await first.page.getByRole('button', { name: '降序 ↓' }).click();
  await expect(first.page.getByText(/当前排序：.*升序/)).toBeVisible();

  await first.page.getByLabel('50亿元').check();
  const thresholdResponse = first.page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/research/a-share/dashboard') &&
      response.url().includes('thresholdYuan=5000000000'),
  );
  await first.page.getByRole('button', { name: '应用' }).click();
  expect((await thresholdResponse).ok()).toBeTruthy();
  await expect(first.page.getByText('共 1 只', { exact: true })).toBeVisible();

  await removeExistingTestStock(first.page);
  const watchlistSection = first.page.locator('#a-share-watchlist');
  await watchlistSection.getByRole('button', { name: '添加自选' }).click();
  await watchlistSection.getByLabel('股票代码', { exact: true }).fill('SH600000');
  await watchlistSection.getByLabel('股票名称', { exact: true }).fill('浦发银行');
  await watchlistSection.getByLabel('分组', { exact: true }).fill('银行观察');
  const saveResponse = first.page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/me/research-watchlist') &&
      response.request().method() === 'PUT',
  );
  await watchlistSection.getByRole('button', { name: '保存' }).click();
  expect((await saveResponse).ok()).toBeTruthy();
  await expect(watchlistSection.getByText('浦发银行', { exact: true })).toBeVisible();
  await expect(watchlistSection.getByText('账号已同步', { exact: true })).toBeVisible();

  const snapshotResponse = first.page.waitForResponse(
    (response) => response.url().includes('/api/v1/research/a-share/stocks/600000/snapshot'),
  );
  await watchlistSection.getByRole('button', { name: '浦发银行 600000', exact: true }).click();
  expect((await snapshotResponse).ok()).toBeTruthy();
  await expect(first.page.getByText('完整度 100%')).toBeVisible();
  await expect(first.page.getByRole('button', { name: /行情与估值/ })).toBeVisible();
  await first.context.close();

  const second = await openAuthenticatedPage(browser, username, password);
  await second.page.goto(absoluteUrl('/hedge-board/a-share'));
  const restoredWatchlist = second.page.locator('#a-share-watchlist');
  await expect(restoredWatchlist.getByText('账号已同步', { exact: true })).toBeVisible();
  await expect(restoredWatchlist.getByText('浦发银行', { exact: true })).toBeVisible();
  await expect(restoredWatchlist.getByDisplayValue('银行观察')).toBeVisible();
  await second.context.close();
});
