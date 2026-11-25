import { expect, test } from '@playwright/test';

test('all-A forecast follows ETF cumulative chart and survives refresh and cached tabs', async ({
  page,
}) => {
  let status = 'ready';
  await page.route('**/api/v1/research/a-share/turnover-forecast', (route) =>
    route.fulfill({
      json: {
        date: '2026-11-05',
        status,
        source: '隔离测试行情',
        latest: {
          slot: '10:00',
          asOf: '2026-11-05T10:00:00+08:00',
          amountYi: '4000',
          estimate5Yi: '8000',
          estimate20Yi: '9000',
          samples5: 5,
          samples20: 20,
        },
        rows: [
          {
            slot: '10:00',
            asOf: '2026-11-05T10:00:00+08:00',
            amountYi: '4000',
            estimate5Yi: '8000',
            estimate20Yi: '9000',
            samples5: 5,
            samples20: 20,
          },
        ],
      },
    }),
  );
  await page.goto('/#/hedge-board/a-share?view=etf');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await page.getByRole('button', { name: '盘中监测', exact: true }).click();
  const panel = page.getByRole('region', { name: '全A当日成交额预测' });
  await expect(panel.locator('.metrics')).toContainText('8,000');
  await panel.locator('.forecast-plot').scrollIntoViewIfNeeded();
  await expect(panel.locator('.forecast-plot svg')).toHaveCount(1);
  expect(
    await page
      .locator('#chartCum')
      .evaluate((el) => el.closest('.chart-wrap')?.nextElementSibling?.id),
  ).toBe('allATurnoverForecast');
  // The backend read path is exercised independently of the browser's synthetic prediction.
  const response = await page.request.get('/api/v1/research/a-share/turnover-forecast');
  expect(response.ok()).toBeTruthy();
  const actual = await response.json();
  expect(Array.isArray(actual.rows)).toBeTruthy();
  await page.getByRole('button', { name: '刷新当前页', exact: true }).click();
  await expect(panel.locator('.metrics')).toContainText('9,000');
  await panel.locator('.forecast-plot').scrollIntoViewIfNeeded();
  await expect(panel.locator('.forecast-plot svg')).toHaveCount(1);
  await page.getByRole('button', { name: 'ETF总览', exact: true }).click();
  await page.getByRole('button', { name: '盘中监测', exact: true }).click();
  await panel.locator('.forecast-plot').scrollIntoViewIfNeeded();
  await expect(panel.locator('.forecast-plot svg')).toHaveCount(1);
  status = 'stale';
  await page.getByRole('button', { name: '刷新当前页', exact: true }).click();
  await expect(panel).toContainText('当前预测暂停展示');
  await expect(panel.locator('.metrics strong').nth(1)).toHaveText('—亿元');
  await page.unroute('**/api/v1/research/a-share/turnover-forecast');
  await page.getByRole('button', { name: '刷新当前页', exact: true }).click();
  await expect(panel.locator('.source')).toContainText(actual.source);
  if (actual.latest) {
    await expect(panel.locator('.metrics strong').first()).toContainText(
      Number(actual.latest.amountYi).toLocaleString('zh-CN', { maximumFractionDigits: 0 }),
    );
  }
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await panel.evaluate((el) => el.scrollWidth <= el.clientWidth + 1)).toBeTruthy();
  await page.setViewportSize({ width: 1280, height: 1100 });
  await panel.scrollIntoViewIfNeeded();
  await page.screenshot({ path: '../.codex/all-a-forecast-real-preview.png' });
});
