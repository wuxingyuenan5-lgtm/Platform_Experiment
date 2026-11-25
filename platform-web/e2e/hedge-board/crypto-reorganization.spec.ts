import { test, expect } from '@playwright/test';

test('crypto keeps requested navigation, moves widgets and exposes viewpoint links', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.route('**/research/crypto/iv-snapshot', (route) =>
    route.fulfill({
      json: {
        data: {
          index: 76000,
          dvol: 40,
          observedAt: '2026-11-07',
          tenors: ['1M', '3M', '6M', '1Y'].map((tenor) => ({
            tenor,
            iv: 38,
            expiry: '2027-01-01',
          })),
        },
      },
    }),
  );
  await page.route('**/research/crypto/iv-history?*', (route) =>
    route.fulfill({
      json: {
        data: {
          history: [
            { observedAt: '2026-11-05', iv: 35 },
            { observedAt: '2026-11-06', iv: null },
            { observedAt: '2026-11-07', iv: 38 },
          ],
          stats: {
            current: 38,
            rangeLow: 35,
            rangeHigh: 38,
            historyLow: 35,
            historyHigh: 38,
            count: 2,
          },
        },
      },
    }),
  );
  await page.goto('/#/hedge-board/crypto?view=crypto-external-research');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  const iv = page.locator('.widget-card--iv-term'),
    distribution = page.locator('.widget-card--option-distribution');
  await expect(iv.locator('svg')).not.toHaveCount(0);
  const left = await iv.boundingBox(),
    right = await distribution.boundingBox();
  expect(left!.x).toBeLessThan(right!.x);
  expect(Math.abs(left!.y - right!.y)).toBeLessThan(5);
  await expect(iv.getByText('历史有 1 个日期存在缺失')).toBeVisible();
  await expect(distribution.locator('.option-distribution-chart')).toHaveCount(2);
  await expect(page.locator('nav a').filter({ hasText: '加密市场总览' })).toBeVisible();
  await expect(page.locator('nav a').filter({ hasText: '衍生品数据' })).toBeVisible();
  await page.goto('/#/hedge-board/crypto?view=crypto-etf');
  const premium = page.locator('.widget-card--etf-premium');
  await expect(premium).toBeVisible();
  const titles = await page.locator('.widget-card__title-row h5').allTextContents();
  expect(titles).toEqual(['BTC ETF 日流量', 'ETH ETF 日流量', 'BTC ETF 溢价 / 折价']);
  const capitalTabs = page.getByRole('navigation', { name: '资金面分类', exact: true });
  await expect(capitalTabs.getByRole('button')).toHaveText(['ETF', '财库公司', '稳定币']);
  await capitalTabs.getByRole('button', { name: '财库公司', exact: true }).click();
  await expect(page.locator('.widget-card__title-row h5')).toHaveText([
    'BTC 财库公司每周变动',
    '上市公司 BTC 持仓分布',
    'Strategic ETH Reserve',
    'STRC 股价历史',
    'Strategy BTC 持仓',
  ]);
  await capitalTabs.getByRole('button', { name: '稳定币', exact: true }).click();
  await expect(page.locator('.widget-card__title-row h5')).toHaveText([
    '稳定币市值历史',
    '离岸人民币与 OKX 买卖U价',
  ]);
  await capitalTabs.getByRole('button', { name: 'ETF', exact: true }).click();
  await expect(premium).toBeVisible();
  await page.goto('/#/hedge-board/crypto?view=crypto-onchain-toolbox');
  await expect(page.getByRole('heading', { name: '链上与周期', exact: true })).toBeVisible();
  await expect(page.getByText('BTC Seasonal Chart', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Murphy Chen', { exact: true })).toHaveCount(0);
  const keys = await page.locator('.widget-card__title-row h5').allTextContents();
  expect(keys.indexOf('BTC 月度统计分析')).toBe(keys.indexOf('Bitcoin 减半周期表现') + 1);
  const a = await page
    .getByRole('group', { name: 'Realized Price Distribution', exact: true })
    .boundingBox();
  const b = await page
    .getByRole('group', { name: 'Bitcoin Address Distribution', exact: true })
    .boundingBox();
  expect(Math.abs(a!.y - b!.y)).toBeLessThan(5);
  expect(Math.abs(a!.height - b!.height)).toBeLessThan(2);
  const controls = await page.locator('.correlation-panel .controls').boundingBox();
  const ranges = await page.locator('.correlation-panel .ranges').boundingBox();
  expect(
    Math.abs(controls!.y + controls!.height / 2 - ranges!.y - ranges!.height / 2),
  ).toBeLessThan(2);
  await expect(page.getByText('日内收盘时差', { exact: false })).toHaveCount(0);
  await page.goto('/#/hedge-board/macro?view=viewpoints');
  await expect(page.getByRole('heading', { name: '观点跟踪', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '美股观点跟踪', exact: true }).click();
  await page.getByLabel('搜索观点来源').fill('美投君');
  await expect(page.locator('.viewpoints__sources a')).toHaveAttribute(
    'href',
    'https://www.youtube.com/channel/UCBUH38E0ngqvmTqdchWunwQ/videos',
  );
  await page.getByRole('button', { name: '备注', exact: true }).click();
  await page
    .getByRole('textbox', { name: '美投君 · 美投讲美股备注', exact: true })
    .fill('关注财报');
  await page.reload();
  await page.getByRole('button', { name: '美股观点跟踪', exact: true }).click();
  await page.getByLabel('搜索观点来源').fill('美投君');
  await expect(page.getByRole('button', { name: '备注 · 已记录', exact: true })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
