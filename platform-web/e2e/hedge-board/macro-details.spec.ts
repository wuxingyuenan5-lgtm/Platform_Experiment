import { expect, test } from '@playwright/test';

test('macro details groups six topics, preserves links and aligns paired cards', async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1720, height: 1000 });
  const errors: string[] = [];
  const groups: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  // This verifies navigation and layout with isolated research data, not production freshness.
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url());
    return ['127.0.0.1', 'localhost'].includes(url.hostname) ? route.continue() : route.abort();
  });
  await page.route('**/api/v1/research/**', (route) =>
    route.fulfill({ status: 503, json: { detail: 'Isolated research source unavailable' } }),
  );
  await page.route('**/research/macro/dashboard-v1*', (route) => {
    const requested = (new URL(route.request().url()).searchParams.get('groups') || '').split(',');
    groups.push(...requested);
    return route.fulfill({
      json: {
        groups: Object.fromEntries(
          requested.map((group, index) => [
            group,
            [
              {
                seriesId: group,
                label: index ? '测试指标' : '隔离宏观历史',
                unit: 'percent',
                frequency: 'daily',
                timezone: 'UTC',
                methodologyVersion: 'fixture-v1',
                qualityFlags: [],
                source: 'isolated fixture',
                status: 'ready',
                isStale: false,
                latestValue: '3.5',
                observationDate: '2026-11-06',
                observations: Array.from({ length: 24 }, (_, n) => ({
                  date: `2026-10-${String(n + 1).padStart(2, '0')}`,
                  value: String(3 + n / 100),
                })),
              },
            ],
          ]),
        ),
      },
    });
  });
  await page.goto('/#/hedge-board/macro?view=macro-details&section=macro-growth');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  const sidebar = page.getByRole('navigation', { name: '宏观研究专题' });
  await expect(sidebar.getByRole('link')).toHaveText([
    '市场总览›',
    '宏观主题与叙事›',
    '跨资产筛选›',
    '宏观详情›',
    '周期分析›',
    '观点跟踪›',
    '研究工具›',
  ]);
  const tabs = page.getByRole('navigation', { name: '宏观详情分类' });
  const subtabs = page.getByRole('navigation', { name: '宏观详情子分类' });
  const topics = [
    ['macro-liquidity', '流动性'],
    ['macro-rates', '利率'],
    ['macro-growth', '经济'],
    ['macro-inflation', '通胀'],
    ['macro-risk-appetite', '风险偏好'],
    ['macro-fx', '汇率与海外利差'],
  ];
  await expect(tabs.getByRole('link')).toHaveText([
    ...topics.map(([, label]) => label),
    'polymarket',
  ]);
  await expect(tabs.getByRole('link', { name: '经济', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await page
    .locator('#macro-growth .widget-card:not(.widget-card--wide)')
    .first()
    .scrollIntoViewIfNeeded();
  await expect(page.locator('#macro-growth .source-series-plot').first()).toBeVisible();
  expect(groups.length).toBeGreaterThan(0);
  expect(groups).not.toContain('fedAssets');
  expect(groups).not.toContain('majorFx');

  for (const [id, label] of topics) {
    await tabs.getByRole('link', { name: label, exact: true }).click();
    await expect(sidebar.getByRole('link', { name: '宏观详情', exact: true })).toHaveAttribute(
      'aria-current',
      'page',
    );
    await expect(page.locator('.chart-section')).toHaveCount(1);
    await expect(page.locator(`#${id}`)).toBeVisible();
    expect(await subtabs.getByRole('link').count()).toBeLessThanOrEqual(3);
    const mainRow = (await tabs.boundingBox())!;
    const subRow = (await subtabs.boundingBox())!;
    expect(Math.abs(mainRow.y - subRow.y)).toBeLessThan(2);
    if (id === 'macro-rates') {
      await expect(subtabs.getByRole('link')).toHaveText(['美国', '中国']);
      await expect(page.getByRole('heading', { name: '中国国债收益率', exact: true })).toHaveCount(
        0,
      );
      await subtabs.getByRole('link', { name: '中国', exact: true }).click();
      await expect(
        page.getByRole('heading', { name: '中国国债收益率', exact: true }),
      ).toBeVisible();
      await expect(
        page.getByRole('heading', { name: '美债收益率曲线走势', exact: true }),
      ).toHaveCount(0);
      await expect(page.locator('#macro-rates .widget-card')).toHaveCount(3);
      await page.reload();
      await expect(subtabs.getByRole('link', { name: '中国', exact: true })).toHaveAttribute(
        'aria-current',
        'page',
      );
      await subtabs.getByRole('link', { name: '美国', exact: true }).click();
      await expect(subtabs.getByRole('link', { name: '美国', exact: true })).toHaveAttribute(
        'aria-current',
        'page',
      );
      await expect(
        page.getByRole('heading', { name: '美债收益率曲线走势', exact: true }),
      ).toBeVisible();
    }

    const pair = page.locator(
      `#${id} .widget-grid > .widget-card:not(.widget-card--wide):not(.widget-card--macro-fedwatch):not(.widget-card--macro-polymarket-fed)`,
    );
    await pair.first().scrollIntoViewIfNeeded();
    await expect
      .poll(() => pair.first().locator('.visible-chart').getAttribute('data-loaded'))
      .toBe('true');
    // Match by actual row coordinates, including rows below the current viewport.
    await expect
      .poll(async () =>
        page.locator(`#${id} .widget-grid > .widget-card`).evaluateAll((cards) => {
          const rects = cards.map((card) => card.getBoundingClientRect());
          const pairs = rects.flatMap((left, index) =>
            rects
              .slice(index + 1)
              .filter((right) => Math.abs(left.top - right.top) < 1)
              .map((right) => Math.abs(left.bottom - right.bottom)),
          );
          return pairs.length ? Math.max(...pairs) : -1;
        }),
      )
      .toBeGreaterThanOrEqual(0);
    await expect
      .poll(async () =>
        page.locator(`#${id} .widget-grid > .widget-card`).evaluateAll((cards) => {
          const rects = cards.map((card) => card.getBoundingClientRect());
          return rects.every((left, index) =>
            rects
              .slice(index + 1)
              .every(
                (right) =>
                  Math.abs(left.top - right.top) >= 1 || Math.abs(left.bottom - right.bottom) < 2,
              ),
          );
        }),
      )
      .toBe(true);
    if (id === 'macro-growth') {
      await expect(pair.first().locator('.source-series-plot')).toBeVisible();
      await pair
        .first()
        .getByRole('button', { name: /^放大图表/ })
        .click();
      await expect(pair.first().getByRole('dialog')).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(pair.first().getByRole('dialog')).toHaveCount(0);
      await page.screenshot({ path: testInfo.outputPath('macro-paired-cards.png') });
    }
  }
  await page.reload();
  await expect(tabs.getByRole('link', { name: '汇率与海外利差', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await tabs.getByRole('link', { name: '通胀', exact: true }).click();
  await expect(tabs.getByRole('link', { name: '通胀', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await page.goBack();
  await expect(tabs.getByRole('link', { name: '汇率与海外利差', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await page.goto('/#/hedge-board/macro?view=macro-rates');
  await expect(tabs.getByRole('link', { name: '利率', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await tabs.getByRole('link', { name: 'polymarket', exact: true }).click();
  await expect(page).toHaveURL(/view=macro-details&section=expectations/);
  await expect(page.getByRole('heading', { name: 'polymarket', exact: true })).toBeVisible();
  await expect(subtabs).toHaveCount(0);
  await expect(page.locator('.chart-section')).toHaveCount(0);
  await expect(sidebar.getByRole('link', { name: '宏观详情', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await page.reload();
  await expect(tabs.getByRole('link', { name: 'polymarket', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await page.goto('/#/hedge-board/macro?view=expectations');
  await expect(page.getByRole('heading', { name: 'polymarket', exact: true })).toBeVisible();
  await expect(tabs.getByRole('link', { name: 'polymarket', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await page.goto('/#/hedge-board/macro?view=macro-details&section=invalid');
  await expect(tabs.getByRole('link', { name: '流动性', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .locator('.ant-drawer-open')
    .getByRole('button', { name: 'Close', exact: true })
    .click();
  await tabs.getByRole('link', { name: '经济', exact: true }).click();
  await expect(page.locator('#macro-growth')).toBeVisible();
  await subtabs.getByRole('link', { name: '中国', exact: true }).click();
  await expect(page.getByRole('heading', { name: '中国景气调查', exact: true })).toBeVisible();
  const tabBounds = (await page.locator('.macro-detail-navigation').boundingBox())!;
  expect(tabBounds.x).toBeGreaterThanOrEqual(0);
  expect(tabBounds.x + tabBounds.width).toBeLessThanOrEqual(390);
  const mobileCards = page.locator('#macro-growth .widget-card:not(.widget-card--wide)');
  const first = await mobileCards.nth(0).boundingBox();
  const second = await mobileCards.nth(1).boundingBox();
  expect(first!.width).toBeGreaterThan(200);
  expect(second!.y).toBeGreaterThanOrEqual(first!.y + first!.height);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
  ).toBe(true);
  expect(errors).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath('macro-details-mobile.png') });
});
