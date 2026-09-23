const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('@playwright/test');

const origin = process.env.STRATEGY_TEST_ORIGIN || 'http://127.0.0.1:4489';
const output = path.resolve('test-results/strategy-query-browser');
fs.mkdirSync(output, { recursive: true });

async function main() {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [],
      writes = [],
      reads = [];
    let contextReads = 0;
    let instructionState = 'executing';
    page.on('pageerror', (error) => errors.push(error.message));
    const now = new Date().toISOString();
    const context = {
      accountId: 'bybit-browser-fixture',
      venue: 'Bybit',
      spotSymbol: 'BTCUSDT',
      perpetualSymbol: 'BTCUSDT',
      symbolOptions: [
        {
          baseAsset: 'BTC',
          quoteCurrency: 'USDT',
          perpetualSymbol: 'BTCUSDT',
          spotSymbol: 'BTCUSDT',
          perpetualInstrumentId: 'btc-perp',
          spotInstrumentId: 'btc-spot',
        },
      ],
      spotQuote: { mid: '80000.123456789012345678' },
      perpetualQuote: { mid: '80001.123456789012345678' },
      fundingRate: '0.0001',
      nextFundingTime: now,
      basis: '1',
      tickSize: { spot: '0.01', perpetual: '0.01' },
      quantityStep: { spot: '0.001', perpetual: '0.001' },
      minimumQuantity: { spot: '0.001', perpetual: '0.001' },
      contractMultiplier: { spot: '1', perpetual: '1' },
      suggestedQuantity: '0.001',
      openSizing: {
        valid: true,
        spotQuantity: '0.001',
        perpetualQuantity: '0.001',
      },
      requestedNotional: '100',
      availableBalance: null,
      activeReservation: {
        currency: 'USDT',
        activeReserved: '0',
        fundingReserved: '0',
        crossReserved: '0',
        fundingAvailable: '1000',
      },
      sharedResourceClaims: [],
      controlledLiveReadiness: { ready: true },
      runtime: { liveWriteEnabled: false },
      dataQualityState: 'complete',
      asOf: now,
    };
    await page.route('**/*', async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.origin !== origin) return route.abort();
      if (!url.pathname.includes('/api/')) return route.continue();
      const json = (body, status = 200) =>
        route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
      if (url.pathname === '/api/v1/auth/me')
        return json({
          user: {
            userId: 'browser-ceo',
            username: 'test',
            realName: '浏览器验证',
            role: 'ceo',
            status: 'active',
            registeredAt: now,
            rowVersion: 1,
          },
          permissions: ['strategy.read', 'strategy.trade', 'profile.read_self', 'research.read'],
          session: { sessionId: 'browser-session', expiresAt: '2030-01-01T00:00:00Z' },
          csrfToken: 'browser-csrf',
        });
      if (url.pathname.endsWith('/funding/execution-context')) {
        contextReads++;
        return json(context);
      }
      if (url.pathname.endsWith('/funding/positions')) return json([]);
      if (url.pathname.includes('/funding/instructions')) {
        if (request.method() === 'POST') {
          writes.push({ body: request.postDataJSON(), csrf: request.headers()['x-csrf-token'] });
          return route.abort('timedout');
        }
        reads.push(url.pathname + url.search);
        return json({
          instruction: { instructionId: 'browser-instruction' },
          executionBatch: null,
          workspaceState: { executionState: instructionState },
        });
      }
      if (url.pathname.endsWith('/strategies/management-overview')) return json([]);
      if (url.pathname.endsWith('/account-snapshot'))
        return json({
          strategyInstanceId: 'test',
          accountId: null,
          dataQualityState: 'unavailable',
          positions: [],
          orders: [],
          fills: [],
          equityHistory: [],
          economicEvents: [],
          coinBalances: [],
        });
      return json([]);
    });
    await page.goto(`${origin}/#/strategy/platform?desk=funding&section=execution`);
    await page.locator('[data-testid="funding-order-panel"]').waitFor({ timeout: 20_000 });
    const submit = page.locator('[data-testid="funding-order-panel"] .submit-btn--green');
    await submit.waitFor();
    await page.waitForFunction(() => !document.querySelector('.submit-btn--green')?.disabled);
    assert.ok(await page.getByText('80000.123456789012345678', { exact: true }).count());
    assert.ok(contextReads <= 2, `Unexpected initial context fanout: ${contextReads}`);
    await page.screenshot({ path: path.join(output, 'funding-ready.png'), fullPage: true });
    await submit.click();
    await page.getByRole('button', { name: '确认提交', exact: true }).click();
    await page.waitForFunction(() => {
      const draft = JSON.parse(localStorage.getItem('vg.platform.funding.pendingDraft') || 'null');
      return draft?.instructionId === 'browser-instruction';
    });
    assert.equal(writes.length, 1);
    assert.equal(writes[0].body.quantity, '0.001');
    assert.equal(writes[0].csrf, 'browser-csrf');
    const identity = writes[0].body.idempotencyKey;
    await page.reload();
    await page.locator('[data-testid="funding-order-panel"]').waitFor();
    await page.waitForFunction(
      () =>
        JSON.parse(localStorage.getItem('vg.platform.funding.pendingDraft') || 'null')
          ?.instructionId === 'browser-instruction',
    );
    assert.equal(writes.length, 1);
    assert.equal(await submit.isDisabled(), true);
    assert.equal(
      await page.evaluate(
        () => JSON.parse(localStorage.getItem('vg.platform.funding.pendingDraft')).idempotencyKey,
      ),
      identity,
    );
    instructionState = 'completed';
    await page.getByRole('button', { name: '刷新行情', exact: true }).click();
    await page.waitForFunction(() => !localStorage.getItem('vg.platform.funding.pendingDraft'));
    assert.equal(writes.length, 1);
    await page.screenshot({ path: path.join(output, 'funding-recovered.png'), fullPage: true });
    assert.deepEqual(errors, []);
    console.log(
      JSON.stringify({
        result: 'passed',
        contextReads,
        writes: writes.length,
        recoveryReads: reads.length,
        errors,
      }),
    );
  } finally {
    await browser.close();
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
