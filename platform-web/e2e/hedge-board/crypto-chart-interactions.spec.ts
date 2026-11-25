import { expect, test } from '@playwright/test';

test('merged correlations toggle independently and halving sliders keep a stable range', async ({
  page,
}) => {
  const requests: string[] = [];
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
    if (url.pathname.endsWith('/research/crypto/rolling-correlation')) {
      requests.push(url.search);
      const gold = url.searchParams.get('benchmark') === 'xau';
      return route.fulfill({
        json: {
          rows: Array.from({ length: 500 }, (_, day) => ({
            date: new Date(Date.UTC(2025, 0, 1) + day * 86400000).toISOString().slice(0, 10),
            correlation:
              gold && day % 19 === 0
                ? null
                : String((gold ? 0.3 : -0.3) + 0.2 * Math.sin(day / 20)),
          })),
          note: '各自共同交易区间的收益率相关性；缺失日期不填充。',
          sources: ['https://btc.example', gold ? 'https://gold.example' : 'https://ndx.example'],
        },
      });
    }
    if (url.pathname.endsWith('/research/crypto/dashboard-v1')) {
      return route.fulfill({
        json: {
          schemaVersion: '1.0',
          status: 'succeeded',
          asOf: '2026-11-04',
          groups: {
            halvingCycles: [2012, 2016, 2020, 2024].map((year, index) => ({
              seriesId: `halving_${year}`,
              label: `${year} 周期`,
              status: 'succeeded',
              unit: 'index',
              frequency: 'daily',
              timezone: 'UTC',
              source: 'Fixture',
              isStale: false,
              asOf: '2026-11-04',
              qualityFlags: [`base_date:${year}-01-01`, `halving_block:${210000 * (index + 1)}`],
              observations: Array.from({ length: index === 3 ? 501 : 1301 }, (_, day) => ({
                date: new Date(Date.UTC(year, 0, 1) + day * 86400000).toISOString().slice(0, 10),
                value: String(100 + (day * (index + 1)) / 3),
              })),
            })),
          },
        },
      });
    }
    return route.continue();
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/#/login');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login/);
  await page.goto('/#/hedge-board/crypto?view=crypto-onchain-toolbox');
  const correlation = page.locator('.widget-card').filter({
    has: page.getByRole('heading', { name: 'BTC / 纳指、XAU · 滚动相关性', exact: true }),
  });
  await expect(correlation).toHaveCount(1);
  await correlation.scrollIntoViewIfNeeded();
  const plot = correlation.locator('.plot');
  await expect(plot.locator('svg')).toBeVisible();
  await expect.poll(() => requests.length).toBe(2);
  const bluePaths = plot.locator('path[stroke="#2864ec"]');
  const goldPaths = plot.locator('path[stroke="#c7931a"]');
  await expect.poll(() => bluePaths.count()).toBeGreaterThan(0);
  await expect.poll(() => goldPaths.count()).toBeGreaterThan(0);
  await plot.getByText('BTC / 纳指', { exact: true }).click();
  await expect(bluePaths).toHaveCount(0);
  await expect.poll(() => goldPaths.count()).toBeGreaterThan(0);
  await correlation.getByRole('button', { name: '3个月', exact: true }).click();
  await correlation.getByRole('button', { name: '1年', exact: true }).click();
  await expect(bluePaths).toHaveCount(0);
  await plot.getByText('BTC / 纳指', { exact: true }).click();
  await expect.poll(() => bluePaths.count()).toBeGreaterThan(0);
  await plot.getByText('BTC / XAUUSD', { exact: true }).click();
  await expect(goldPaths).toHaveCount(0);
  await expect.poll(() => bluePaths.count()).toBeGreaterThan(0);
  await correlation.getByRole('spinbutton').fill('30');
  await correlation.getByRole('button', { name: '应用', exact: true }).click();
  await expect(correlation.getByText('共同交易区间 · 当前 N=30')).toBeVisible();
  expect(requests.slice(-2).every((query) => new URLSearchParams(query).get('n') === '30')).toBe(
    true,
  );
  await expect(goldPaths).toHaveCount(0);
  await plot.getByText('BTC / XAUUSD', { exact: true }).click();
  await expect.poll(() => goldPaths.count()).toBeGreaterThan(0);
  await correlation.screenshot({ path: '../.codex/crypto-correlations-verified.png' });

  const halving = page
    .locator('.widget-card')
    .filter({ has: page.getByRole('heading', { name: 'Bitcoin 减半周期表现', exact: true }) });
  await halving.scrollIntoViewIfNeeded();
  const start = halving.getByRole('slider', { name: '减半周期显示起点', exact: true });
  const end = halving.getByRole('slider', { name: '减半周期显示终点', exact: true });
  const cursor = halving.getByRole('slider', { name: '减半后天数', exact: true });
  await expect(end).toHaveValue('1095');
  await expect(start).toHaveAttribute('max', '1095');
  await expect(end).toHaveAttribute('min', '0');
  const startBox = (await start.boundingBox())!;
  const endBox = (await end.boundingBox())!;
  expect(Math.abs(startBox.x - endBox.x)).toBeLessThan(1);
  expect(Math.abs(startBox.width - endBox.width)).toBeLessThan(1);
  // Native pointer drag must update continuously without a changing track scale.
  await page.mouse.move(startBox.x + 7, startBox.y + startBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(startBox.x + startBox.width * 0.3, startBox.y + startBox.height / 2, {
    steps: 15,
  });
  await page.mouse.up();
  const selectedStart = Number(await start.inputValue());
  expect(selectedStart).toBeGreaterThan(250);
  expect(selectedStart).toBeLessThan(400);
  await end.focus();
  await end.press('Home');
  await expect(end).toHaveValue(String(selectedStart + 1));
  await expect(cursor).toHaveAttribute('min', String(selectedStart));
  await expect(cursor).toHaveAttribute('max', String(selectedStart + 1));
  expect(Number(await cursor.inputValue())).toBeGreaterThanOrEqual(selectedStart);
  expect((await start.boundingBox())!.x).toBe(startBox.x);
  expect((await end.boundingBox())!.width).toBe(endBox.width);
  await halving.getByRole('button', { name: '365天', exact: true }).click();
  await expect(start).toHaveValue('0');
  await expect(end).toHaveValue('365');
  await halving.getByRole('button', { name: '全部', exact: true }).click();
  await expect(end).toHaveValue('1300');
  await halving
    .getByRole('button', { name: '放大图表：Bitcoin 减半周期表现', exact: true })
    .click();
  await expect(end).toHaveValue('1300');
  await expect(halving.locator('svg[role="img"]')).toBeVisible();
  await halving
    .locator('dialog')
    .screenshot({ path: '../.codex/crypto-halving-sliders-verified.png' });
});
