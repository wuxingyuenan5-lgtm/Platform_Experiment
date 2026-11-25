const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, expect } = require('@playwright/test');
const origin = process.env.AI_REPORT_TEST_ORIGIN || 'http://127.0.0.1:4473';
const output = path.resolve('test-results/ai-investment-report');
fs.mkdirSync(output, { recursive: true });

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1050 },
    acceptDownloads: true,
    reducedMotion: 'reduce',
  });
  const errors = [],
    writes = [],
    api = [];
  let unavailable = false;
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => {
    if (/\[Vue warn\]|WidgetErrorBoundary/.test(m.text())) errors.push(m.text());
  });
  await page.route('**/*', (route) => {
    const req = route.request(),
      url = new URL(req.url());
    const json = (body, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
    if (url.pathname.startsWith('/api/')) {
      api.push(url.pathname);
      if (!['GET', 'HEAD', 'OPTIONS'].includes(req.method())) writes.push(url.pathname);
      if (req.method() === 'OPTIONS')
        return route.fulfill({
          status: 204,
          headers: {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Allow-Headers': '*',
          },
        });
      if (url.pathname === '/api/v1/auth/me')
        return json({
          user: {
            userId: 'ai-report-isolated',
            username: 'test',
            realName: '隔离验证',
            role: 'employee',
            status: 'active',
            registeredAt: '2026-11-09T00:00:00Z',
            rowVersion: 1,
          },
          permissions: ['profile.read_self', 'research.read'],
          session: { sessionId: 'isolated', expiresAt: '2030-01-01T00:00:00Z' },
          csrfToken: 'isolated',
        });
      if (url.pathname === '/api/v1/research/equity/ai')
        return unavailable
          ? json({ detail: '隔离测试：历史数据暂不可用' }, 503)
          : json({ companies: [], capexHistory: [], cds: [], sources: [], metricDefinitions: {} });
      if (url.pathname === '/api/v1/research/equity/ai/MSFT')
        return json({ ticker: 'MSFT', quarters: [], annual: [], kpis: [], disclosures: [] });
      return json([]);
    }
    if (url.origin !== origin) return route.abort();
    return route.continue();
  });
  try {
    await page.goto(origin + '/#/hedge-board/us?view=ai');
    const entry = page.getByRole('button', { name: '兴证AI投资专题 · 本次新增', exact: true });
    await expect(entry).toBeVisible({ timeout: 90000 });
    await entry.click();
    await expect(page.getByRole('heading', { name: '从资本开支，追踪景气兑现' })).toBeVisible();
    const nav = page.getByRole('navigation', { name: '新增专题分类' });
    const groups = [
      '资本开支与高频验证',
      '历史周期与盈利',
      '全球权重与交易热度',
      '日历效应与产业轮动',
      '渗透率与估值',
      '产业链与上游材料',
    ];
    const seen = new Set();
    for (let i = 0; i < groups.length; i++) {
      await nav.getByRole('button', { name: new RegExp(groups[i]) }).click();
      const hosts = page.locator('.investment-report .visible-chart');
      const n = await hosts.count();
      for (let j = 0; j < n; j++) {
        await hosts.nth(j).scrollIntoViewIfNeeded();
        await expect(hosts.nth(j).locator('.plot svg, .plot canvas').first()).toBeVisible({
          timeout: 15000,
        });
        const chartId = await hosts.nth(j).locator('[data-chart-id]').getAttribute('data-chart-id');
        seen.add(chartId);
        if (['global-peg', 'segments-peg', 'market-cap', 'drawdowns'].includes(chartId))
          await hosts.nth(j).screenshot({ path: path.join(output, chartId + '.png') });
      }
      await page.locator('.report-head').scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(output, `group-${i + 1}.png`) });
    }
    assert.equal(seen.size, 35);
    await expect(page.locator('.chain-map')).toHaveCount(2);
    await nav.getByRole('button', { name: /资本开支与高频验证/ }).click();
    await page.getByPlaceholder('Capex、GPU、估值…').fill('GPU');
    await expect(page.locator('.topic')).toHaveCount(1);
    await page.getByRole('button', { name: '清除筛选', exact: true }).click();
    const first = page.locator('.report-chart').first();
    await first.scrollIntoViewIfNeeded();
    await first.getByText('查看数据与单位', { exact: true }).click();
    await expect(first.locator('tbody tr')).toHaveCount(162);
    const downloadEvent = page.waitForEvent('download');
    await first.getByRole('button', { name: '导出CSV' }).click();
    const download = await downloadEvent;
    const exported = path.join(output, download.suggestedFilename());
    await download.saveAs(exported);
    assert.ok(fs.readFileSync(exported, 'utf8').includes('Demo · 模拟数据'));
    await first.getByText('查看数据与单位', { exact: true }).click();
    await page
      .getByRole('button', { name: '放大图表：半导体盈利预期 × 北美云厂商Capex', exact: true })
      .click();
    await expect(
      page.getByRole('dialog', { name: '半导体盈利预期 × 北美云厂商Capex', exact: true }),
    ).toBeVisible();
    await page.screenshot({ path: path.join(output, 'expanded.png') });
    await page.keyboard.press('Escape');
    await expect(page.locator('[aria-modal="true"]')).toHaveCount(0);
    await nav.getByRole('button', { name: /全球权重与交易热度/ }).click();
    await page.getByLabel('数据范围').selectOption('snapshot');
    await expect(page.locator('.topic')).toHaveCount(2);
    await page.locator('.visible-chart').first().scrollIntoViewIfNeeded();
    await expect(page.locator('.report-chart .demo')).toHaveCount(0);
    await page.getByRole('button', { name: '清除筛选', exact: true }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.locator('.ant-drawer-mask')).toBeVisible();
    await page.locator('.ant-drawer-mask').click({ position: { x: 380, y: 400 } });
    await expect(page.locator('.ant-drawer-mask')).not.toBeVisible();
    for (const group of ['全球权重与交易热度', '渗透率与估值', '产业链与上游材料']) {
      await nav.getByRole('button', { name: new RegExp(group) }).click();
      await page.locator('.report-head').scrollIntoViewIfNeeded();
      assert.ok(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
        group + ' document overflow',
      );
      assert.ok(
        await page
          .locator('.investment-report')
          .evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
        group + ' report overflow',
      );
    }
    await page.screenshot({ path: path.join(output, 'mobile.png') });
    await page.setViewportSize({ width: 1440, height: 1050 });
    await page.getByRole('button', { name: '产业总览', exact: true }).click();
    await expect(page.getByRole('heading', { name: '产业链财务比较', exact: true })).toBeVisible();
    await expect(page.locator('.investment-report')).toHaveCount(0);
    unavailable = true;
    await page.reload();
    await expect(entry).toBeVisible({ timeout: 60000 });
    await entry.click();
    await expect(page.locator('.investment-report')).toBeVisible();
    await expect(page.getByRole('heading', { name: '从资本开支，追踪景气兑现' })).toBeVisible();
    assert.deepEqual(writes, []);
    assert.deepEqual(errors, []);
    console.log(
      JSON.stringify({
        result: 'passed',
        charts: seen.size,
        groups: 6,
        mobile: '390px',
        verified:
          'actual route with isolated auth/API; all charts, filters, CSV, expansion, old tab, API failure',
        writes: writes.length,
        errors: errors.length,
      }),
    );
  } finally {
    await browser.close();
  }
}
main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
