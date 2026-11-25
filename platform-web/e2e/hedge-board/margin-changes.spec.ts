import { test, expect } from '@playwright/test';

test('margin changes default legends, merged ratio table and compact columns', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  const days = Array.from({ length: 40 }, (_, i) =>
    new Date(Date.UTC(2026, 8, i + 1)).toISOString().slice(0, 10),
  );
  const series = (seriesId: string, value: string) => ({
    seriesId,
    unit: seriesId === 'cn_margin_buy_share' ? 'percent' : 'cny_100million',
    observations: days.map((date, i) => ({
      date,
      value:
        seriesId === 'cn_margin_buy_share' && i === 39
          ? null
          : seriesId === 'cn_margin_financing_balance'
          ? String(Number(value) + i)
          : value,
    })),
  });
  await page.route('**/research/a-share/financing', (route) =>
    route.fulfill({
      json: {
        margin: [
          series('cn_margin_total_balance', '23000'),
          series('cn_margin_financing_balance', '22700'),
          series('cn_margin_short_balance', '300'),
          series('cn_margin_financing_change', '20'),
          series('cn_margin_financing_buy', '1000'),
          series('cn_margin_buy_share', '7.75'),
        ],
        marginIndex: {
          rows: days.slice(0, -1).map((date, i) => ({ date, close: String(4000 + i * 10) })),
        },
        basis: [],
        iv: { rows: [] },
        goldIv: [],
        futuresSource: { status: 'ready' },
      },
    }),
  );
  await page.goto('/#/hedge-board/a-share?view=capital&section=margin');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page.getByRole('button', { name: '两融', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '两融与杠杆', exact: true })).toHaveCount(0);
  const panel = page.locator('.margin-balance-chart');
  await expect(panel.getByRole('heading', { name: '两融余额变化', exact: true })).toBeVisible();
  const level = panel.locator('.ranges').getByLabel('级别选择', { exact: true });
  await expect(level).toHaveValue('day');
  await expect(panel.locator('.plot svg')).toBeVisible();
  await expect(panel.getByRole('button', { name: '1年', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  for (const name of ['两融总余额', '融券余额'])
    await expect(
      panel.locator('svg text').filter({ hasText: new RegExp('^' + name + '$') }),
    ).toHaveAttribute('fill', '#ccc');
  await expect(
    panel.locator('svg text').filter({ hasText: /^融资融券成交额占比$/ }),
  ).toHaveAttribute('fill', '#ccc');
  await panel
    .locator('svg text')
    .filter({ hasText: /^融资融券成交额占比$/ })
    .click();
  await expect(
    panel.locator('svg text').filter({ hasText: /^融资融券成交额占比$/ }),
  ).not.toHaveAttribute('fill', '#ccc');
  await expect(panel.locator('svg text').filter({ hasText: /^沪深300$/ })).not.toHaveAttribute(
    'fill',
    '#ccc',
  );
  await expect(panel.locator('svg text').filter({ hasText: /^融资买入额$/ })).toHaveCount(0);
  const orangeLine = panel
    .locator('svg path[stroke="#d97706"]:not([stroke-dasharray])')
    .filter({ visible: true })
    .first();
  await expect(orangeLine).toBeVisible();
  const bounds = await orangeLine.boundingBox();
  expect(bounds!.height).toBeGreaterThan(50);
  await panel.getByRole('button', { name: '查看数据', exact: true }).click();
  await expect(panel.locator('thead th')).toHaveText([
    '日期',
    '两融总余额（亿元）',
    '融资余额（亿元）',
    '融券余额（亿元）',
    '融资余额日变化（亿元）',
    '融资融券成交额占比（%）',
    '沪深300（点）',
  ]);
  await expect(panel.locator('tbody tr').first().locator('td').last()).toHaveText('—');
  await expect(panel.locator('tbody tr').nth(1).locator('td').nth(4)).toHaveText('7.75');
  await expect(panel.locator('tbody tr').nth(1).locator('td').last()).toHaveText('4,380');
  const sizing = await panel.evaluate((node) => ({
    table: node.querySelector('table')!.getBoundingClientRect().width,
    panel: node.getBoundingClientRect().width,
  }));
  expect(sizing.table).toBeLessThan(sizing.panel * 0.9);
  await panel.screenshot({ path: test.info().outputPath('margin-table.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  expect(
    await panel.locator('.data-scroll').evaluate((node) => node.scrollWidth > node.clientWidth),
  ).toBe(true);
  await level.selectOption('week');
  await expect(panel.getByRole('columnheader', { name: '融资余额周变化（亿元）' })).toBeVisible();
  const first = panel.locator('tbody tr').first();
  await expect(first.locator('th')).toHaveText('2026-10-10');
  await expect(first.locator('td').nth(3)).toHaveText('6');
  await expect(first.locator('td').last()).toHaveText('—');
  await level.selectOption('month');
  await expect(panel.getByRole('columnheader', { name: '融资余额月变化（亿元）' })).toBeVisible();
  await expect(panel.locator('tbody th')).toHaveText(['2026-10-10', '2026-09-30']);
  await expect(first.locator('td').nth(3)).toHaveText('10');
  await expect(panel.locator('tbody tr').last().locator('td').nth(3)).toHaveText('—');
});
