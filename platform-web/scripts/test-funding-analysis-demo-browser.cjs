const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, expect } = require('@playwright/test');

const origin = process.env.FUNDING_DEMO_ORIGIN || 'http://127.0.0.1:4477';
const appOrigin = process.env.FUNDING_DEMO_APP_ORIGIN || 'http://127.0.0.1:4476';
const output = path.resolve('test-results/funding-analysis-demo');
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const errors = [],
    requests = [];
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1050 },
      acceptDownloads: true,
    });
    page.on('pageerror', (error) => errors.push(error.message));
    await page.route('**/*', (route) => {
      const url = new URL(route.request().url());
      if (url.origin !== origin || url.pathname.startsWith('/api')) {
        requests.push(url.href);
        return route.abort();
      }
      return route.continue();
    });
    await page.goto(`${origin}/funding-analysis-demo.html`);
    await expect(page.getByTestId('funding-analysis-demo')).toBeVisible();
    await expect(page.locator('.opportunity-table tbody tr')).toHaveCount(8);
    await expect(page.getByTestId('scenario-net')).toHaveText('+119.56');
    await page.screenshot({ path: path.join(output, 'desktop.png'), fullPage: true });
    await page.getByRole('button', { name: '30d', exact: true }).click();
    await page.getByRole('button', { name: '查看数据', exact: true }).click();
    await expect(page.locator('.plot-table tbody tr')).toHaveCount(90);
    await page.getByRole('button', { name: '查看图表', exact: true }).click();
    await page.getByLabel('资费延续比例').evaluate((el) => {
      el.value = '0';
      el.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await expect(page.getByTestId('scenario-net')).toHaveText('-174.44');
    await expect(page.locator('.scenario-explanation')).toContainText('正资费条件不满足');
    await page.getByRole('button', { name: '恢复基准情景', exact: true }).click();
    await expect(page.getByTestId('scenario-net')).toHaveText('+119.56');
    await page.getByRole('button', { name: '基差与拥挤', exact: true }).click();
    await expect(page.locator('.analysis-main svg')).toHaveCount(2);
    await expect(page.locator('.equation')).toContainText('− 现货－指数 +1.00');
    await page.locator('.pair-research').scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, 'basis.png'), fullPage: false });
    await page.getByRole('button', { name: '产品与事件', exact: true }).click();
    await page.getByRole('button', { name: /急涨现金压力 ↗/ }).click();
    await expect(page.locator('.scenario-explanation')).toContainText('假设储备不足');
    await page.getByRole('button', { name: '容量与现金', exact: true }).click();
    await expect(page.locator('.ledger-total dd')).toHaveClass(/negative/);
    await page.screenshot({ path: path.join(output, 'cash-stress.png'), fullPage: false });
    await page.getByRole('button', { name: '恢复基准情景', exact: true }).click();
    await page.getByLabel('持有期', { exact: true }).selectOption('1');
    await expect(page.getByTestId('scenario-net')).toHaveText('-132.44');
    await page.getByLabel('持有期', { exact: true }).selectOption('7');
    await page.getByLabel('单腿名义金额', { exact: true }).selectOption('500000');
    await page.locator('[data-pair="sol-bg"] .pair-button').click();
    await expect(page.locator('.capacity-verdict')).toContainText('深度不足');
    await page.getByLabel('单腿名义金额', { exact: true }).selectOption('100000');
    await page.getByRole('button', { name: '股票', exact: true }).click();
    await expect(page.locator('.opportunity-table tbody tr')).toHaveCount(1);
    await expect(page.getByTestId('scenario-net')).toHaveText('待核验');
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: '导出当前情景 ↓', exact: true }).click();
    const download = await downloadPromise;
    const csv = fs.readFileSync(await download.path(), 'utf8');
    assert.ok(csv.includes('"净收益_USDT","待核验"'));
    assert.ok(csv.includes('全部为合成模拟情景'));
    await page.getByRole('button', { name: '全部', exact: true }).click();
    await page.getByLabel('搜索配对').fill('not-found');
    await expect(page.getByText('没有符合条件的配对', { exact: true })).toBeVisible();
    await expect(page.locator('.pair-research')).toHaveCount(0);
    await page.getByRole('button', { name: '清除筛选', exact: true }).click();
    await page.getByLabel('交易所', { exact: true }).selectOption('Bybit');
    await expect(page.locator('.opportunity-table tbody tr')).toHaveCount(3);
    await page.getByLabel('仅可研究', { exact: true }).check();
    await expect(page.locator('.opportunity-table tbody tr')).toHaveCount(1);
    await page.getByLabel('仅可研究', { exact: true }).uncheck();
    await page.getByLabel('交易所', { exact: true }).selectOption('全部交易所');
    await page.getByLabel('机会排序').selectOption('funding');
    await expect(page.locator('.opportunity-table tbody tr').first()).toHaveAttribute(
      'data-pair',
      'sol-bg',
    );
    await page.locator('[data-pair="btc-bn"] .pair-button').click();
    await page.getByRole('button', { name: '资费与收益', exact: true }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => window.scrollTo(0, 0));
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    assert.ok(overflow <= 1, `Mobile overflow: ${overflow}`);
    await page.screenshot({ path: path.join(output, 'mobile.png'), fullPage: true });
    await page.getByRole('button', { name: '研究口径 ↗', exact: true }).click();
    await expect(page.getByLabel('研究口径', { exact: true })).toContainText(
      '持仓收益与下单留在各自工作区',
    );
    assert.deepEqual(requests, [], 'Standalone demo must not call APIs or external services');

    // Verify the actual application entry with isolated browser auth responses.
    // These responses never grant access to the real backend.
    const integrated = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
    const apiPaths = [],
      writes = [];
    integrated.on('pageerror', (error) => errors.push(error.message));
    await integrated.route('**/*', (route) => {
      const req = route.request(),
        url = new URL(req.url());
      if (url.origin !== appOrigin) return route.abort();
      if (!url.pathname.startsWith('/api/')) return route.continue();
      apiPaths.push(url.pathname);
      if (!['GET', 'HEAD'].includes(req.method())) writes.push(url.pathname);
      const json = (body) =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
      if (url.pathname === '/api/v1/auth/me')
        return json({
          user: {
            userId: 'funding-demo-test',
            username: 'test',
            realName: '隔离测试',
            role: 'ceo',
            status: 'active',
            registeredAt: '2026-11-06T00:00:00Z',
            rowVersion: 1,
          },
          permissions: ['strategy.read', 'strategy.trade', 'profile.read_self', 'research.read'],
          session: { sessionId: 'test', expiresAt: '2030-01-01T00:00:00Z' },
          csrfToken: 'test',
        });
      return json([]);
    });
    await integrated.goto(`${appOrigin}/#/strategy/platform?desk=funding&section=analysisDemo`);
    await expect(integrated.getByTestId('funding-analysis-demo')).toBeVisible({ timeout: 60000 });
    await expect(
      integrated.getByRole('button', { name: '行情分析（新）', exact: true }),
    ).toBeVisible();
    assert.ok(
      !apiPaths.some((p) => /funding\/(execution|positions|instructions)/.test(p)),
      apiPaths.join('\n'),
    );
    await integrated.screenshot({ path: path.join(output, 'platform-entry.png'), fullPage: false });
    await integrated.reload();
    await expect(integrated.getByTestId('funding-analysis-demo')).toBeVisible();
    await integrated.getByRole('button', { name: '行情分析', exact: true }).click();
    await expect(integrated.getByTestId('funding-analysis-demo')).toHaveCount(0);
    await expect(
      integrated.getByRole('heading', { name: '单次收益情景', exact: true }),
    ).toBeVisible();
    await integrated.getByRole('button', { name: '行情分析（新）', exact: true }).click();
    await expect(integrated.getByTestId('funding-analysis-demo')).toBeVisible();
    await integrated.getByRole('button', { name: '海内外价差', exact: true }).click();
    await expect(integrated.getByTestId('funding-analysis-demo')).toHaveCount(0);
    await expect(
      integrated.getByRole('button', { name: '行情分析（新）', exact: true }),
    ).toHaveCount(0);
    assert.deepEqual(writes, []);
    assert.deepEqual(errors, []);
    console.log(
      JSON.stringify(
        {
          result: 'passed',
          standalone: 'filters, charts, scenarios, CSV, 390px',
          integration: 'real route, reload, old/new navigation; isolated auth/API',
          externalRequests: requests.length,
          writes: writes.length,
          pageErrors: errors.length,
          screenshots: output,
        },
        null,
        2,
      ),
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
