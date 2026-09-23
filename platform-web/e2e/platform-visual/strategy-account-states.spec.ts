import { expect, test, type Page } from '@playwright/test';

// Synthetic account facts exercise the real Vue page. No account or venue writes occur.
const now = '2026-09-19T08:00:00Z';
const instance = 'strategy_cross_venue_spread_instance_default';
const accountIds = ['bybit-live-main', 'mt5-live-main'];

function snapshot(accountId: string) {
  const bybit = accountId === accountIds[0];
  return {
    strategyInstanceId: instance,
    accountId,
    accountCode: bybit ? 'BYBIT-LIVE-001' : 'MT5-LIVE-001',
    capability: 'trade_and_read',
    snapshotScope: 'strategy',
    dataQualityState: 'complete',
    syncStatus: 'ready',
    isStale: false,
    asOf: now,
    lastSuccessfulSyncAt: now,
    financialSyncStatus: 'ready',
    balance: { currency: 'USD', equity: bybit ? '1234.56' : '678.90' },
    accountRisk: {
      currency: 'USD',
      assetScope: bybit ? 'unified_trading' : 'trading',
      totalAssets: bybit ? '2345.67' : null,
      freeMargin: '500',
      assetBreakdown: [],
    },
    positions: [
      {
        accountId,
        instrumentId: bybit ? 'instrument_xau_usdt_perp' : 'instrument_xau_usd',
        symbol: bybit ? 'XAUTUSDT' : 'XAUUSD.S',
        category: bybit ? 'linear' : 'mt5',
        instrumentType: bybit ? 'crypto_perp' : 'mt5_contract',
        netQuantity: bybit ? '1' : '-0.01',
        positionValue: '3000',
        positionValueCurrency: bybit ? 'USDT' : 'USD',
        currentPrice: '3000',
      },
    ],
    orders: [],
    fills: [],
    finance: null,
    coinBalances: [],
    economicEvents: [],
    dailyPnl: [
      {
        date: '2026-09-18',
        currency: 'USD',
        pnl: bybit ? '10' : '20',
        equityOpen: '100',
        equityClose: bybit ? '110' : '120',
        returnRate: bybit ? '10' : '20',
        quality: 'estimated',
      },
    ],
    equityHistory: [
      {
        asOf: now,
        equity: bybit ? '1234.56' : '678.90',
        totalAssets: bybit ? '2345.67' : null,
        equityDrawdown: '0',
        totalAssetsDrawdown: '0',
      },
    ],
  };
}

async function fixture(page: Page) {
  const state = { failBindings: false, failAccount: '', noBindings: false, reads: [] as string[] };
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const json = (data: unknown, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) });
    // Any unexpected mutation is a test failure, never forwarded to a service.
    expect(request.method()).toBe('GET');
    state.reads.push(url.pathname + url.search);
    if (url.pathname.endsWith('/auth/me'))
      return json({
        user: {
          userId: 'fixture-reader',
          username: 'fixture',
          realName: '验收只读用户',
          role: 'ceo',
          status: 'active',
          registeredAt: now,
          rowVersion: 1,
        },
        permissions: ['strategy.read', 'profile.read_self', 'research.read'],
        session: { sessionId: 'fixture-session', expiresAt: '2030-01-01T00:00:00Z' },
        csrfToken: 'fixture-only',
      });
    if (url.pathname.endsWith('/strategies/management-overview'))
      return json([
        {
          deskKey: 'crossSpread',
          sortOrder: 10,
          operatingStatus: 'active',
          displayName: '跨所价差',
        },
        {
          deskKey: 'shortLineTraderW',
          sortOrder: 20,
          operatingStatus: 'active',
          displayName: '短线交易员BL',
        },
      ]);
    if (url.pathname.endsWith('/system/monitor-health'))
      return json({
        accountSync: { status: 'healthy' },
        crossExit: { status: 'healthy' },
        watchdog: { status: 'healthy' },
        crossExitExecutionEnabled: true,
      });
    if (url.pathname.endsWith(`/${instance}/accounts`)) {
      if (state.failBindings) return json({ detail: 'fixture bindings unavailable' }, 503);
      return json(
        state.noBindings
          ? []
          : accountIds.map((accountId, index) => ({
              accountId,
              accountCode: index ? 'MT5-LIVE-001' : 'BYBIT-LIVE-001',
              role: index ? 'mt5_leg' : 'venue_a',
              status: 'active',
            })),
      );
    }
    if (url.pathname.endsWith('/account-snapshot')) {
      const id = url.searchParams.get('accountId');
      if (!id)
        return json({
          ...snapshot(''),
          accountId: null,
          accountCode: null,
          balance: null,
          accountRisk: null,
          syncStatus: 'unbound',
          dataQualityState: 'unbound',
          asOf: null,
          isStale: true,
          dailyPnl: [],
          equityHistory: [],
        });
      if (id === state.failAccount) return json({ detail: 'fixture account unavailable' }, 503);
      return json(snapshot(id));
    }
    if (url.pathname.endsWith('/pnl'))
      return json({
        currency: 'USD',
        byCurrency: [],
        positions: [],
        timeline: [],
        issues: [],
        dataQualityState: 'complete',
        strategyDailyPnl: [],
      });
    return json([]);
  });
  return state;
}

test.beforeEach(async ({ page }, testInfo) => {
  const errors: string[] = [];
  const requests: object[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('Failed to load resource'))
      errors.push(message.text());
  });
  page.on('response', (response) => {
    if (new URL(response.url()).pathname.startsWith('/api/'))
      requests.push({
        url: response.url(),
        status: response.status(),
        method: response.request().method(),
      });
  });
  (page as Page & { acceptanceEvidence?: () => Promise<void> }).acceptanceEvidence = async () => {
    await testInfo.attach('api-request-summary', {
      body: JSON.stringify(requests.slice(-100), null, 2),
      contentType: 'application/json',
    });
    expect(errors, 'uncaught and console errors, including captured component errors').toEqual([]);
    await expect(page.getByText(/渲染失败，已自动跳过/)).toHaveCount(0);
  };
});

test.afterEach(async ({ page }) => {
  await (page as Page & { acceptanceEvidence?: () => Promise<void> }).acceptanceEvidence?.();
});

test('isolated seeded API and SQLite drive an authenticated management page', async ({
  page,
  request,
}) => {
  const backend = process.env.PLATFORM_VISUAL_BACKEND_ORIGIN!;
  const runtime = process.env.PLATFORM_VISUAL_RUNTIME_ORIGIN!;
  expect(await (await request.get(`${backend}/health`)).json()).toMatchObject({
    service: 'platform-api',
    environment: 'test',
  });
  expect(await (await request.get(`${runtime}/health`)).json()).toMatchObject({
    service: 'execution-runtime',
    gateway: 'fake',
  });
  await page.route(/^https?:\/\/(?!127\.0\.0\.1(?::\d+)?\/|localhost(?::\d+)?\/)/, (route) =>
    route.abort(),
  );
  await page.goto('/#/login');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_SHARED_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/);
  await page.goto('/#/strategy/management?desk=shortLineTraderW&section=capital');
  await expect(page.getByTestId('strategy-management-original-structure')).toBeVisible();
  await expect(page.locator('.risk-item').filter({ hasText: '数据状态' })).toContainText(
    '暂未绑定账号',
  );
  await page.getByRole('button', { name: '策略损益', exact: true }).click();
  await expect(page.getByRole('heading', { name: '损益总览', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '账户资金', exact: true }).click();
  await expect(page.locator('.capital-net-value-board')).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await expect(page.locator('.ant-drawer-open')).toHaveCount(0);
  await expect(page.locator('.ant-drawer-content-wrapper')).toBeHidden();
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
    .toBeLessThanOrEqual(391);
});

test('account failure is distinct from unbound, refresh restores both legs, and stale data remains labelled', async ({
  page,
}) => {
  const state = await fixture(page);
  state.failAccount = accountIds[1];
  await page.goto('/#/strategy/management?desk=crossSpread&section=capital');
  await expect(page.getByTestId('strategy-management-original-structure')).toBeVisible();
  await expect(
    page.locator('.strategy-sync-alert').filter({ hasText: '账户数据同步中断' }),
  ).toBeVisible();
  await expect(page.locator('.risk-item').filter({ hasText: '数据状态' })).not.toContainText(
    '全部正常',
  );
  await expect(page.locator('.pnl-calendar-summary')).not.toContainText('+10.00');
  expect(
    state.reads.filter((url) => url.includes('/account-snapshot') && url.includes('accountId=')),
  ).toHaveLength(2);
  expect(
    state.reads.filter((url) => url.includes('/account-snapshot') && url.includes('accountId=')),
  ).toEqual(expect.arrayContaining([expect.stringContaining('includeDetails=false')]));
  expect(state.reads.some((url) => url.endsWith(`/${instance}/pnl`))).toBe(false);

  state.failAccount = '';
  await page.getByRole('button', { name: '刷新状态', exact: true }).click();
  await expect(
    page.locator('.strategy-sync-alert').filter({ hasText: '账户数据同步中断' }),
  ).toHaveCount(0);
  await expect(page.locator('.risk-item').filter({ hasText: '数据状态' })).toContainText(
    '全部正常',
  );
  await expect(page.locator('.pnl-calendar-summary')).toContainText('30.00');
  await expect(page.locator('.position-distribution-card')).toContainText('USDT');
  await expect(page.locator('.position-distribution-card')).toContainText('USD');
  await expect(page.locator('.position-distribution-card')).toContainText('oz');
  const curve = page.locator('.capital-net-value-board');
  await curve.locator('select').first().selectOption('mt5Equity');
  await expect(curve.locator('h3')).toHaveText('MT5-LIVE-001 · 交易账户权益');
  await expect(curve.locator('.curve-summary')).toContainText('678.90');
  await page.locator('.pnl-calendar-title').click();
  await expect(page.locator('.pnl-calendar-switch')).toContainText('按月');
  await page.getByRole('button', { name: '上一年', exact: true }).click();
  await expect(page.locator('.pnl-calendar-cursor')).toContainText('2025');

  state.failAccount = accountIds[1];
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await expect(
    page.locator('.strategy-sync-alert').filter({ hasText: '账户数据同步中断' }),
  ).toBeVisible();
  await expect(curve.locator('.curve-summary')).toContainText('678.90');
  await page.setViewportSize({ width: 390, height: 844 });
  // The responsive shell opens its navigation drawer when crossing the breakpoint.
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await expect(page.locator('.ant-drawer-open')).toHaveCount(0);
  await expect(page.locator('.ant-drawer-content-wrapper')).toBeHidden();
  await page.getByRole('button', { name: '刷新状态', exact: true }).scrollIntoViewIfNeeded();
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
    .toBeLessThanOrEqual(391);
  await page.screenshot({
    path: test.info().outputPath('account-stale-mobile.png'),
    animations: 'disabled',
  });
  const overflow = await page
    .locator('.strategy-management-page')
    .evaluate((element) => element.scrollWidth - element.clientWidth);
  expect(overflow, 'management content should wrap on a narrow screen').toBeLessThanOrEqual(2);
  state.failAccount = '';
  await page.getByRole('button', { name: '刷新状态', exact: true }).click();
  await expect(
    page.locator('.strategy-sync-alert').filter({ hasText: '账户数据同步中断' }),
  ).toHaveCount(0);
  await page.getByRole('button', { name: '策略损益', exact: true }).click();
  await expect(page.getByRole('heading', { name: '损益总览', exact: true })).toBeVisible();
  await page.getByLabel('收益曲线时间精度').selectOption({ label: '1H' });
  await page.getByRole('button', { name: '账户资金', exact: true }).click();
  await expect(curve).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath('account-recovered-mobile.png'),
    animations: 'disabled',
  });
});

test('binding transport failure is not an empty binding and switching desks does not duplicate refresh subscriptions', async ({
  page,
}) => {
  const state = await fixture(page);
  state.failBindings = true;
  await page.goto('/#/strategy/management?desk=crossSpread&section=capital');
  await expect(
    page.locator('.strategy-sync-alert').filter({ hasText: '账户数据同步中断' }),
  ).toBeVisible();
  state.failBindings = false;
  state.noBindings = true;
  await page.getByRole('button', { name: '刷新状态', exact: true }).click();
  await expect(page.locator('.risk-item').filter({ hasText: '数据状态' })).toContainText(/未绑定/);
  state.noBindings = false;
  await page.getByRole('button', { name: '短线交易员BL', exact: true }).click();
  await expect(page.locator('.risk-item').filter({ hasText: '数据状态' })).toContainText(
    '暂未绑定账号',
  );
  await page.getByRole('button', { name: '跨所价差', exact: true }).click();
  await expect(page.locator('.risk-item').filter({ hasText: '数据状态' })).toContainText(
    '全部正常',
  );
  const before = state.reads.filter((url) => url.endsWith(`/${instance}/accounts`)).length;
  await page.evaluate(() => {
    document.dispatchEvent(new Event('visibilitychange'));
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await expect
    .poll(() => state.reads.filter((url) => url.endsWith(`/${instance}/accounts`)).length)
    .toBe(before + 1);
});
