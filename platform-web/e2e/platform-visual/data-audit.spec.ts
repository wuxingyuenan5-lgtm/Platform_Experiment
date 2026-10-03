import { expect, test } from '@playwright/test';

test('data audit reads persisted backend evidence, filters and reports read failure', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/#/login');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_SHARED_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/);
  await page.goto('/#/risk/data-audit');
  await expect(page.getByRole('heading', { name: '全平台数据健康' })).toBeVisible();
  await expect(page.locator('.audit-key').first()).toBeVisible();
  await page.getByPlaceholder('搜索数据集、模块或问题').fill('全库表登记');
  await expect(page.getByText('database.inventory', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '查看证据', exact: true }).click();
  await expect(page.locator('.audit-evidence')).toContainText('tableCount');
  await page.screenshot({ path: 'test-results/data-audit-desktop.png', fullPage: true });
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  const mobileMenuClose = page.locator('.ant-drawer-close');
  await expect(mobileMenuClose).toBeVisible();
  await mobileMenuClose.click();
  await expect(mobileMenuClose).not.toBeVisible();
  await expect(page.getByRole('button', { name: '刷新结果' })).toBeVisible();
  await page.route('**/api/v1/risk/data-audit', (route) =>
    route.fulfill({ status: 503, body: '{}' }),
  );
  await page.getByRole('button', { name: '刷新结果' }).click();
  await expect(
    page.getByText('无法读取审计结果，请检查平台 API；不能据此判断数据正常。'),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
