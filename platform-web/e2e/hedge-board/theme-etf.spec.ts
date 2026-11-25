import { expect, test } from '@playwright/test';

test('theme aggregation is reachable and fund drilldown preserves broad analysis', async ({
  page,
}) => {
  await page.goto('/#/hedge-board/a-share?view=etf');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await page.getByRole('button', { name: '主题ETF', exact: true }).click();
  const panel = page.getByRole('region', { name: '主题ETF份额观察' });
  await expect(panel.getByText('主题内ETF', { exact: true })).toBeVisible();
  const response = await page.request.get(
    'http://127.0.0.1:8437/api/v1/research/a-share/theme-etfs',
  );
  expect(response.ok()).toBeTruthy();
  const result = await response.json();
  expect(result.themes.length).toBe(14);
  await panel.getByLabel('主题份额分类').selectOption('红利／央国企');
  await expect(panel.locator('.funds button')).toHaveCount(3);
  await panel.getByRole('combobox').nth(1).selectOption('indexed');
  await expect(panel.locator('.plot svg')).toHaveCount(1);
  await expect(panel.locator('.plot')).toContainText('首日=100');
  await panel.locator('.funds button').first().click();
  await expect(panel.locator('.member-analysis')).toBeVisible();
  await expect(panel.getByText('正在读取单只 ETF…')).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'ETF分类分析' })).toBeVisible();
  await panel.screenshot({ path: '../.codex/theme-etf-desktop.png' });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await panel.evaluate((el) => el.scrollWidth <= el.clientWidth + 1)).toBeTruthy();
});
