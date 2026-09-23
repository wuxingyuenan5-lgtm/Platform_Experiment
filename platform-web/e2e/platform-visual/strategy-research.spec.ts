import { expect, test } from '@playwright/test';

test('research uses real isolated API, preserves unknowns and removes carry templates', async ({
  page,
}) => {
  await page.route(/^https?:\/\/(?!127\.0\.0\.1(?::\d+)?\/|localhost(?::\d+)?\/)/, (route) =>
    route.abort(),
  );
  await page.goto('/#/login');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_SHARED_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/);
  const requests: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/research/strategies/'))
      requests.push(request.method() + ' ' + request.url());
  });
  await page.goto('/#/strategy/platform?desk=funding&section=analysis');
  await expect(page.getByRole('heading', { name: '单次收益情景' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '借贷费率', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: '期现价差表', exact: true })).toBeVisible();
  await expect(page.getByText('已发布研究数据', { exact: false })).toHaveCount(0);
  await expect(page.getByText('历史起点', { exact: false })).toHaveCount(0);
  await expect(page.getByText('当前关注标的', { exact: true })).toHaveCount(0);
  await expect(page.getByText('高精度研究标的', { exact: true })).toHaveCount(0);
  await expect(page.getByText('借贷历史', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: '最高资金费率' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '最低资金费率' })).toBeVisible();
  const boardAlignment = await page.locator('.market-board').evaluate((el) => {
    const table = el.querySelector('.market-board__table-area')?.getBoundingClientRect();
    const extrema = el.querySelector('.extrema-grid')?.getBoundingClientRect();
    return table && extrema ? Math.abs(table.top - extrema.top) : 999;
  });
  expect(boardAlignment).toBeLessThanOrEqual(2);
  await expect(page.locator('.heatmap-table__row .symbol-cell')).toHaveText([
    'BTC×',
    'ETH×',
    'SOL×',
    'XAUT×',
    'CRCL×',
    'MSTR×',
  ]);
  await page.getByPlaceholder('搜索币种', { exact: true }).fill('eth');
  await expect(page.locator('.heatmap-table__row .symbol-cell')).toHaveText(['ETH×']);
  await page.getByPlaceholder('搜索币种', { exact: true }).fill('');
  await page.getByLabel(/^排序/).selectOption('name');
  await expect(page.locator('.heatmap-table__row .symbol-cell')).toHaveText([
    'BTC×',
    'CRCL×',
    'ETH×',
    'MSTR×',
    'SOL×',
    'XAUT×',
  ]);
  await expect(page.getByText('标记价格', { exact: true })).toHaveCount(0);
  await page.getByLabel('入场价差', { exact: true }).fill('3');
  await page.getByLabel('退出价差', { exact: true }).fill('1');
  await page.getByLabel('开平仓总手续费').fill('0');
  await page.getByLabel('额外执行成本').fill('0');
  await page.getByLabel('明确假设本次资金费为 0').check();
  const response = page.waitForResponse((r) => r.url().includes('/research/strategies/scenario'));
  await page.getByRole('button', { name: '计算', exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect(page.locator('dl')).toContainText('2');
  await page.getByRole('button', { name: '采集状态', exact: true }).click();
  await expect(page.getByLabel('采集状态')).toContainText('关闭页面后');
  await page.reload();
  await expect(page.getByRole('heading', { name: '单次收益情景' })).toBeVisible();
  expect(requests.filter((x) => x.startsWith('POST')).length).toBe(1);
  await page.getByLabel('入场价差', { exact: true }).fill('3');
  await page.getByLabel('退出价差', { exact: true }).fill('1');
  const saved = page.waitForResponse(
    (r) => r.url().endsWith('/research/strategies/drafts') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '保存研究参数', exact: true }).click();
  expect((await saved).status()).toBe(200);
  await page.getByRole('link', { name: '交接执行草案', exact: true }).click();
  await expect(page.getByText('研究参数：', { exact: false })).toBeVisible();
  const executionWrites: string[] = [];
  page.on('request', (r) => {
    if (r.method() === 'POST' && /trading.*(instructions|market-command|commands)/.test(r.url()))
      executionWrites.push(r.url());
  });
  await page.getByRole('button', { name: '预填执行表单', exact: true }).click();
  await expect(page.getByText('已预填，请核对当前执行条件。')).toBeVisible();
  expect(executionWrites).toHaveLength(0);
  await page.goto('/#/strategy/platform?desk=crossSpread&section=analysis');
  await expect(page.getByText('XAUTUSDT − XAUUSD', { exact: true })).toBeVisible();
  await expect(page.getByText('期限结构', { exact: true })).toHaveCount(0);
  await expect(page.getByText('统计分布', { exact: true })).toBeVisible();
  await expect(page.getByText('季节图表', { exact: true })).toBeVisible();
  await expect(page.getByText('月度热力矩阵', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: '历史价格与已结算资费' })).toHaveCount(0);
  await expect(page.getByText('历史结算明细与来源')).toHaveCount(0);
  await expect(page.getByText('持仓加权资金费率', { exact: true })).toHaveCount(0);
  await page.screenshot({ path: 'test-results/strategy-research-desktop.png', fullPage: false });
  await page.setViewportSize({ width: 390, height: 844 });
  const closeMenu = page.locator('.ant-drawer-close');
  if (await closeMenu.isVisible()) await closeMenu.click();
  await expect
    .poll(async () =>
      page.locator('.research-workspace').evaluate((el) => el.getBoundingClientRect().right),
    )
    .toBeLessThanOrEqual(392);
  await page.getByRole('button', { name: '计算', exact: true }).scrollIntoViewIfNeeded();
  await expect(page.getByRole('button', { name: '计算', exact: true })).toBeInViewport();
  const width = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    client: document.documentElement.clientWidth,
  }));
  expect(width.scroll).toBeLessThanOrEqual(width.client + 2);
  await page.screenshot({ path: 'test-results/strategy-research-mobile.png', fullPage: false });
});

// Presentation fixtures intentionally exercise populated data and a partial failure.
// Real venue coverage is checked separately against the running service.
test('market data remains visible when latest quote fails; original chart and table layout survives', async ({
  page,
}) => {
  await page.goto('/#/login');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_SHARED_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/);
  const at = new Date(Date.now() - 120000).toISOString();
  await page.route('**/research/strategies/pairs/funding-btc/latest', (r) =>
    r.fulfill({ status: 503, body: 'unavailable' }),
  );
  await page.route('**/research/strategies/funding/board?*', (r) =>
    r.fulfill({
      json: {
        status: 'available',
        stale: false,
        receivedAt: at,
        data: {
          board: {
            updatedAt: at,
            symbolOptions: ['BTC', 'DOGE'],
            resolutionOptions: [],
            summaryCards: [],
            highest: [],
            lowest: [],
            usdtExchanges: ['Bybit'],
            inverseExchanges: [],
            rows: [{ symbol: 'BTC', usdtPerps: { Bybit: 0.0123 }, inversePerps: {} }],
          },
          fundingChart: {
            title: 'Bybit 指示资金费率',
            legendFunding: '指示资金费率',
            legendPrice: '',
            points: [
              { date: at, funding: 0.0123 },
              { date: new Date(Date.parse(at) + 60000).toISOString(), funding: -0.01 },
            ],
          },
          borrowObservations: [],
        },
      },
    }),
  );
  await page.route('**/research/strategies/pairs/funding-btc/series?*', (r) =>
    r.fulfill({
      json: {
        status: 'available',
        stale: false,
        data: {
          rows: [
            {
              timeMs: String(Date.parse(at)),
              validDurationMs: 999,
              ohlc: { midSpread: { open: '7.123', high: '7.123', low: '7.123', close: '7.123' } },
            },
          ],
        },
      },
    }),
  );
  await page.route('**/research/strategies/pairs/funding-btc/history?*', (r) =>
    r.fulfill({
      json: {
        status: 'available',
        stale: false,
        data: {
          chartSeries: [
            {
              name: 'BTCUSDT 永续收盘',
              type: 'line',
              axis: 0,
              selected: true,
              data: [
                { value: [Date.parse(at), '81234.123456789012345'] },
                { value: [Date.parse(at) + 60000, '81235.123456789012345'] },
              ],
            },
            {
              name: 'BTCUSDT 现货收盘',
              type: 'line',
              axis: 0,
              selected: false,
              data: [{ value: [Date.parse(at), '81230'] }],
            },
          ],
          sourcePriceCount: 2,
          displayIntervalMs: '60000',
          prices: [0, 60000].map((offset) => ({
            symbol: 'BTCUSDT',
            category: 'linear',
            priceType: 'trade',
            sourceTimeMs: String(Date.parse(at) + offset - 60000),
            closeTimeMs: String(Date.parse(at) + offset),
            intervalMs: '60000',
            close: '81234.123456789012345',
            receivedAt: at,
          })),
          settlements: [],
        },
      },
    }),
  );
  await page.goto('/#/strategy/platform?desk=funding&section=analysis');
  await expect(page.locator('.market-board')).toContainText('0.0123%');
  await expect(page.locator('.detail-panel')).toContainText('7.123');
  await expect(
    page.locator('.chart-panel').getByText('所选窗口暂无该序列的已采集数据'),
  ).toHaveCount(0);
  await expect(page.getByRole('alert')).toContainText('部分数据读取失败');
  await expect(page.locator('.chart-grid .chart-card')).toHaveCount(2);
  await expect(page.locator('.table-grid .table-card')).toHaveCount(2);
  await expect(
    page.getByRole('heading', { name: '标的价格与资费走势', exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel('资费精度')).toContainText('1H');
  await expect(page.locator('.history-panel')).toContainText('BTC');
  await expect(page.locator('.history-chart svg')).toBeVisible();
  await expect(page.locator('.chart-panel svg [fill="#2db87c"]').first()).toBeVisible();
  await expect(page.locator('.chart-panel svg [fill="#cf3f4f"]').first()).toBeVisible();
  const added = page.waitForRequest(
    (r) =>
      r.url().includes('/funding/board?') &&
      new URL(r.url()).searchParams.get('symbols')?.includes('DOGE') === true,
  );
  await page.getByPlaceholder('搜索全部标的').fill('DOGE');
  await page.getByRole('button', { name: '添加', exact: true }).click();
  await added;
  await page
    .locator('.history-panel')
    .getByRole('button', { name: '近 1 日', exact: true })
    .click();
  await expect(page.getByRole('button', { name: '1H', exact: true })).toHaveClass(/active/);
  await page.screenshot({
    path: 'test-results/strategy-research-restored-fixture.png',
    fullPage: true,
  });
});
