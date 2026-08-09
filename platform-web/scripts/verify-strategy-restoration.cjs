const fs = require('fs');
const path = require('path');

const { chromium } = require(path.join(process.cwd(), 'node_modules', '@playwright', 'test'));

const origin = 'http://127.0.0.1:4373';
const oldOrigin = 'http://127.0.0.1:5273';
const outDir = path.join(process.cwd(), 'test-results', 'strategy-restoration');
fs.mkdirSync(outDir, { recursive: true });

const T = {
  login: '\u767b\u5f55',
  accountPlaceholder: /\u8d26\u53f7|\u8d26\u6237|\u8bf7\u8f93\u5165\u8d26\u53f7/,
  passwordPlaceholder: /\u5bc6\u7801|\u8bf7\u8f93\u5165\u5bc6\u7801/,
  funding: '\u8d44\u8d39',
  cross: '\u8de8\u6240\u4ef7\u5dee',
  domestic: '\u6d77\u5185\u5916\u4ef7\u5dee',
  dip: '\u6284\u5e95',
  shortA: '\u77ed\u7ebf\u4ea4\u6613\u5458A',
  shortB: '\u77ed\u7ebf\u4ea4\u6613\u5458B',
  analysis: '\u884c\u60c5\u5206\u6790',
  execution: '\u4ea4\u6613\u6267\u884c',
  quote: '\u62a5\u4ef7',
  position: '\u6301\u4ed3',
  research: '\u7814\u7a76\u4fe1\u606f',
  pnlOverview: '\u635f\u76ca\u603b\u89c8',
  totalFund: '\u603b\u8d44\u91d1',
  breakdown: '\u635f\u76ca\u7ec6\u5206\u603b\u56fe',
  day: '\u65e5\u62a5',
  week: '\u5468\u62a5',
  month: '\u6708\u62a5',
  custom: '\u81ea\u5b9a\u4e49',
  capital: '\u8d26\u6237\u8d44\u91d1',
  orders: '\u8ba2\u5355\u4fe1\u606f',
  currentPositions: '\u5f53\u524d\u6301\u4ed3',
};

function json(route, payload) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(payload),
  });
}

async function setupGlobalReadOnlyFixtures(page) {
  const riskRows = [
    {
      id: 9001,
      title: 'strategy check risk',
      content: 'fixture',
      status: 'resolved',
      severity: 'low',
    },
  ];
  const notifications = [
    {
      id: 9101,
      title: 'strategy check notification',
      content: 'fixture',
      status: 'read',
      read: true,
    },
  ];
  await page.route(/\/risk\/api\/v1\/risk-records\/(?:\?.*)?$/, (route) => json(route, riskRows));
  await page.route(/\/undefined\/risk\/api\/v1\/risk-records\/(?:\?.*)?$/, (route) =>
    json(route, riskRows),
  );
  await page.route(/\/notifications\/api\/v1\/messages\/(?:\?.*)?$/, (route) =>
    json(route, notifications),
  );
  await page.route(/\/undefined\/notifications\/api\/v1\/messages\/(?:\?.*)?$/, (route) =>
    json(route, notifications),
  );
}

function classifyAllowedNoise(url) {
  try {
    const parsed = new URL(url, origin);
    const pathname = parsed.pathname;
    if (
      parsed.hostname.endsWith('tradingview.com') ||
      parsed.hostname.endsWith('tradingview-widget.com')
    )
      return 'TradingView external resource';
    if (
      parsed.origin === origin &&
      (pathname === '/undefined/risk' ||
        pathname === '/undefined/notifications' ||
        pathname === '/undefined/risk/api/v1/risk-records/' ||
        pathname === '/undefined/notifications/api/v1/messages/' ||
        pathname === '/risk/api/v1/risk-records/' ||
        pathname === '/notifications/api/v1/messages/')
    )
      return pathname;
  } catch {
    return '';
  }
  return '';
}

function assertContains(text, required, label) {
  for (const item of required)
    if (!text.includes(item)) throw new Error(`${label} missing ${item}`);
}

function assertNotContains(text, forbidden, label) {
  for (const item of forbidden)
    if (text.includes(item)) throw new Error(`${label} still contains ${item}`);
}

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for authenticated E2E checks`);
  return value;
}

async function assertActiveSection(page, name, label) {
  const className =
    (await page.locator('.section-switcher').getByRole('button', { name }).getAttribute('class')) ||
    '';
  if (!className.split(/\s+/).includes('is-active'))
    throw new Error(`${label} section is not active: ${name}`);
}

async function login(page) {
  await page.goto(`${origin}/#/login`, { waitUntil: 'domcontentloaded' });
  await page.getByPlaceholder(T.accountPlaceholder).fill(requiredEnv('E2E_CEO_USERNAME'));
  await page.getByPlaceholder(T.passwordPlaceholder).fill(requiredEnv('E2E_CEO_PASSWORD'));
  const response = page.waitForResponse((item) => item.url().endsWith('/api/v1/auth/login'));
  await page.getByRole('button', { name: new RegExp(T.login) }).click();
  if (!(await response).ok()) throw new Error('login failed');
  await page.waitForURL((url) => !url.hash.includes('/login'), { timeout: 20_000 });
}

async function captureOldReference(browser, route, filename, width, height) {
  const oldPage = await browser.newPage({ viewport: { width, height }, locale: 'zh-CN' });
  try {
    const response = await oldPage.goto(`${oldOrigin}${route}`, {
      waitUntil: 'domcontentloaded',
      timeout: 8000,
    });
    if (!response || !response.ok()) return false;
    await oldPage.waitForTimeout(1000);
    await oldPage.screenshot({ path: path.join(outDir, `old-${filename}-${width}x${height}.png`) });
    return true;
  } catch {
    return false;
  } finally {
    await oldPage.close();
  }
}

async function activateDesk(page, name, queryPart) {
  await page.goto(`${origin}/#/strategy/platform?desk=funding`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="funding-original-structure"]');
  if (name !== T.funding) {
    await page.getByRole('button', { name }).click();
    await page.waitForFunction((part) => location.href.includes(part), queryPart, {
      timeout: 10_000,
    });
    await page.waitForTimeout(300);
  }
}

async function checkViewport(width, height) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width, height }, locale: 'zh-CN' });
  const errors = [];
  const ignoredNoises = [];

  await page.addInitScript(() => {
    window.__strategyE2EUnhandled = [];
    window.addEventListener('unhandledrejection', (event) => {
      const reason = event.reason || {};
      const url =
        reason?.config?.url ||
        reason?.request?.responseURL ||
        reason?.response?.config?.url ||
        reason?.response?.request?.responseURL ||
        '';
      const message = reason?.message || String(reason || '');
      window.__strategyE2EUnhandled.push({ url, message });
      try {
        const parsed = new URL(url, window.location.origin);
        if (
          parsed.hostname.endsWith('tradingview.com') ||
          parsed.hostname.endsWith('tradingview-widget.com') ||
          (parsed.origin === window.location.origin &&
            (parsed.pathname === '/undefined/risk' ||
              parsed.pathname === '/undefined/notifications' ||
              parsed.pathname === '/undefined/risk/api/v1/risk-records/' ||
              parsed.pathname === '/undefined/notifications/api/v1/messages/'))
        )
          event.preventDefault();
      } catch (error) {
        ignoredNoises.push(`unparseable browser resource URL: ${error.message}`);
      }
    });
  });

  await setupGlobalReadOnlyFixtures(page);
  await login(page);
  page.on('pageerror', (error) => {
    if (error.message === 'canceled') {
      ignoredNoises.push('global read-only request cancellation: canceled');
      return;
    }
    errors.push(`pageerror:${error.message}`);
  });
  page.on('requestfailed', (request) => {
    const reason = classifyAllowedNoise(request.url());
    if (reason) ignoredNoises.push(`${reason}: ${request.url()}`);
    else errors.push(`requestfailed:${request.failure()?.errorText || 'unknown'}:${request.url()}`);
  });
  page.on('response', (response) => {
    if (response.status() < 400) return;
    const reason = classifyAllowedNoise(response.url());
    if (reason) ignoredNoises.push(`${reason}: ${response.url()}`);
    else {
      const parsed = new URL(response.url(), origin);
      if (parsed.origin === origin || parsed.pathname.startsWith('/api/'))
        errors.push(`response:${response.status()}:${response.url()}`);
    }
  });

  await page.goto(`${origin}/#/strategy/management`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="strategy-management-original-structure"]');
  const desks = [
    { name: T.funding, slug: 'funding', markers: ['\u8d44\u8d39\u6536\u76ca'] },
    { name: T.cross, slug: 'cross-spread', markers: ['XAUT/XAU\u4ef7\u5dee\u635f\u76ca'] },
    { name: T.domestic, slug: 'domestic-overseas', markers: ['\u6c47\u7387\u635f\u76ca'] },
    { name: T.dip, slug: 'dip', markers: ['\u6b62\u635f\u635f\u8017'] },
    { name: T.shortA, slug: 'short-a', markers: ['\u80a1\u6307\u8d21\u732e'] },
    { name: T.shortB, slug: 'short-b', markers: ['\u5747\u503c\u56de\u5f52\u8d21\u732e'] },
  ];
  const signatures = [];
  for (const desk of desks) {
    await page.getByRole('button', { name: desk.name }).click();
    await page.waitForTimeout(250);
    let text = await page
      .locator('[data-testid="strategy-management-original-structure"]')
      .innerText();
    assertContains(
      text,
      [
        desk.name,
        T.pnlOverview,
        T.totalFund,
        T.breakdown,
        T.day,
        T.week,
        T.month,
        T.custom,
        ...desk.markers,
      ],
      desk.name,
    );
    signatures.push(text.slice(0, 900));
    await page.screenshot({
      path: path.join(outDir, `strategy-management-${desk.slug}-${width}x${height}.png`),
    });
    await page.getByRole('button', { name: T.capital }).click();
    await page.waitForTimeout(150);
    text = await page.locator('[data-testid="strategy-management-original-structure"]').innerText();
    assertContains(
      text,
      [
        '\u8d26\u6237\u51c0\u503c',
        '\u8d44\u91d1\u7ed3\u6784\u89c2\u5bdf',
        '\u51c0\u503c\u66f2\u7ebf',
      ],
      `${desk.name} capital`,
    );
    await page.getByRole('button', { name: T.orders }).click();
    await page.waitForTimeout(150);
    text = await page.locator('[data-testid="strategy-management-original-structure"]').innerText();
    assertContains(
      text,
      [
        T.orders,
        T.currentPositions,
        '\u5f00\u59cb\u65e5\u671f',
        '\u7ed3\u675f\u65e5\u671f',
        '\u6bcf\u9875\u6761\u6570',
      ],
      `${desk.name} orders`,
    );
  }
  if (new Set(signatures).size !== desks.length)
    throw new Error('strategy content did not change across all six desks');
  await page.screenshot({ path: path.join(outDir, `strategy-management-${width}x${height}.png`) });
  await captureOldReference(
    browser,
    '/index.html#/strategy/management',
    'strategy-management',
    width,
    height,
  );

  await activateDesk(page, T.funding, 'desk=funding');
  await page.waitForSelector('[data-testid="funding-original-structure"]');
  let text = await page.locator('[data-testid="funding-original-structure"]').innerText();
  assertContains(
    text,
    [
      '\u6700\u9ad8\u8d44\u91d1\u8d39\u7387',
      '\u6700\u4f4e\u8d44\u91d1\u8d39\u7387',
      '\u6301\u4ed3\u52a0\u6743\u8d44\u91d1\u8d39\u7387',
      '\u671f\u73b0\u4ef7\u5dee\u8868',
      '\u501f\u8d37\u8d39\u7387\u8868',
    ],
    'funding analysis',
  );
  await page.screenshot({ path: path.join(outDir, `funding-analysis-${width}x${height}.png`) });
  await captureOldReference(
    browser,
    '/index.html#/strategy/platform?desk=funding',
    'funding-analysis',
    width,
    height,
  );
  await page.locator('.section-switcher').getByRole('button', { name: T.execution }).click();
  await assertActiveSection(page, T.execution, 'funding execution');
  await page.waitForSelector('[data-testid="funding-order-panel"]', { state: 'visible' });
  text = await page.locator('[data-testid="funding-order-panel"]').innerText();
  assertContains(
    text,
    [
      '\u73b0\u8d27\u817f',
      '\u6c38\u7eed\u817f',
      '\u5957\u5229\u6267\u884c\u6307\u4ee4',
      '\u4ea4\u6613\u89c4\u5219',
      '\u5f53\u524d\u6301\u4ed3\u603b\u89c8',
    ],
    'funding execution',
  );
  await page.screenshot({ path: path.join(outDir, `funding-execution-${width}x${height}.png`) });
  await page.locator('.order-panel').scrollIntoViewIfNeeded();
  await page.screenshot({
    path: path.join(outDir, `funding-execution-controls-${width}x${height}.png`),
  });

  await activateDesk(page, T.cross, 'desk=crossSpread');
  await page.locator('.section-switcher').getByRole('button', { name: T.analysis }).click();
  await assertActiveSection(page, T.analysis, 'cross analysis');
  await page.waitForSelector('[data-testid="spread-original-structure"]');
  text = await page.locator('[data-testid="spread-original-structure"]').innerText();
  assertContains(
    text,
    [
      '\u671f\u9650\u7ed3\u6784',
      '\u673a\u4f1a\u5206\u6790',
      '\u7edf\u8ba1\u5206\u6790',
      '\u5b63\u8282\u56fe\u8868',
      '\u6708\u5ea6\u70ed\u529b\u77e9\u9635',
    ],
    'cross spread analysis',
  );
  if ((await page.locator('.spread-detail-grid').count()) !== 0)
    throw new Error('cross spread analysis still renders removed quote/position/research block');
  await page.screenshot({
    path: path.join(outDir, `cross-spread-analysis-${width}x${height}.png`),
  });
  await captureOldReference(
    browser,
    '/index.html#/strategy/platform?desk=crossSpread',
    'cross-spread-analysis',
    width,
    height,
  );

  await activateDesk(page, T.cross, 'desk=crossSpread');
  await page.locator('.section-switcher').getByRole('button', { name: T.execution }).click();
  await assertActiveSection(page, T.execution, 'cross execution');
  await page.waitForSelector('[data-testid="spread-original-structure"]');
  text = await page.locator('[data-testid="spread-original-structure"]').innerText();
  assertContains(
    text,
    ['\u4ea4\u6613\u6267\u884c', '\u6807\u7684', '\u6267\u884c\u6307\u4ee4'],
    'cross execution',
  );
  if (/CrossVenueExecutionWorkspace|ACK|result_unknown|Live Write/.test(text))
    throw new Error('cross execution exposes engineering copy');
  await page.screenshot({
    path: path.join(outDir, `cross-spread-execution-${width}x${height}.png`),
  });
  await page.getByText('\u6267\u884c\u6307\u4ee4').first().scrollIntoViewIfNeeded();
  await page.screenshot({
    path: path.join(outDir, `cross-spread-execution-controls-${width}x${height}.png`),
  });

  await activateDesk(page, T.domestic, 'desk=domesticOverseas');
  await page.locator('.section-switcher').getByRole('button', { name: T.analysis }).click();
  await assertActiveSection(page, T.analysis, 'domestic overseas analysis');
  await page.waitForSelector('[data-testid="spread-original-structure"]');
  text = await page.locator('[data-testid="spread-original-structure"]').innerText();
  assertContains(
    text,
    [
      '\u79bb\u5cb8\u6c47\u7387',
      '\u5728\u5cb8\u6c47\u7387',
      '\u6d77\u5185\u5916\u6ea2\u4ef7\u5206\u6790',
      '\u5e93\u5b58\u8d39\u5386\u53f2\u56fe\u8868',
      '\u5b9e\u65f6\u4ef7\u5dee',
    ],
    'domestic overseas analysis',
  );
  if ((await page.locator('.spread-detail-grid').count()) !== 0)
    throw new Error(
      'domestic overseas analysis still renders removed quote/position/research block',
    );
  await page.screenshot({ path: path.join(outDir, `domestic-overseas-${width}x${height}.png`) });
  await captureOldReference(
    browser,
    '/index.html#/strategy/platform?desk=domesticOverseas',
    'domestic-overseas',
    width,
    height,
  );

  await activateDesk(page, T.domestic, 'desk=domesticOverseas');
  await page.locator('.section-switcher').getByRole('button', { name: T.execution }).click();
  await assertActiveSection(page, T.execution, 'domestic overseas execution');
  await page.waitForSelector('[data-testid="domestic-overseas-execution-workspace"]');
  if ((await page.locator('[data-testid="domestic-overseas-execution-workspace"]').count()) !== 1)
    throw new Error('domestic overseas execution workspace is not mounted');
  text = await page.locator('[data-testid="domestic-overseas-execution-workspace"]').innerText();
  assertContains(
    text,
    [
      '\u8d44\u4ea7\u6c34\u5e73\uff08CNY\uff09',
      '\u4ed3\u4f4d\u5e73\u8861',
      '74.58% VS \u7a7a 25.42%',
      '11,312,370.08',
      '8,801,303.88',
      '23,028,402.01 CNY',
      '\u603b\u8ba1',
      '20,343,790.35 CNY',
      '2,984,316.97 USD',
      '1.1X',
      '\u6caa\u91d1',
      '1.5X',
      '\u53ef\u7528\u8d44\u91d1\u7387',
      '\u4f26\u6566\u91d1',
      '1,324,857.38',
      '0.6X',
      '\u9884\u4ed8\u6bd4\u7387',
      '\u56fd\u5185\u4ea4\u6613\u817f',
      '\u6d77\u5916\u4ea4\u6613\u817f',
      '\u6c47\u7387',
      '\u4ef7\u5dee',
      '\u8d39\u7528\u4f30\u7b97',
      '\u98ce\u9669\u68c0\u67e5',
      '\u59d4\u6258\u4e0e\u6210\u4ea4',
      '\u63d0\u4ea4\u590d\u6838',
    ],
    'domestic overseas execution',
  );
  assertNotContains(
    text,
    ['\u53cc\u7aef\u8d44\u91d1\u5bf9\u7167', '\u56fd\u5185\u8d26\u6237 48%', '21,773,757.12 CNY'],
    'domestic overseas execution account overview',
  );
  if (!text.includes('\u8d26\u6237\u4fe1\u606f'))
    throw new Error('domestic overseas execution account overview was not restored');
  if (/CrossVenueExecutionWorkspace|ACK|result_unknown|Live Write/.test(text))
    throw new Error('domestic overseas execution reused or exposed cross venue execution copy');
  if (
    /\u5df2\u63d0\u4ea4\u4ea4\u6613\u6240|\u7b49\u5f85\u6210\u4ea4|\u6267\u884c\u6210\u529f|\u6210\u4ea4\u6210\u529f|\u6210\u4ea4\u786e\u8ba4/.test(
      text,
    )
  )
    throw new Error('domestic overseas execution exposes false execution success copy');
  await page.screenshot({
    path: path.join(outDir, `domestic-overseas-execution-${width}x${height}.png`),
  });
  await page.locator('.result-panel').scrollIntoViewIfNeeded();
  await page.screenshot({
    path: path.join(outDir, `domestic-overseas-execution-full-${width}x${height}.png`),
  });

  const unhandled = await page.evaluate(() => window.__strategyE2EUnhandled || []);
  for (const entry of unhandled) {
    const reason = classifyAllowedNoise(entry.url || '');
    if (reason) ignoredNoises.push(`${reason}: ${entry.url}`);
    else errors.push(`unhandledrejection:${entry.message}:${entry.url || 'no-url'}`);
  }
  const bodyText = await page.locator('body').innerText();
  if (
    /Provider|Owner|static_design|source|asOf|actionable|Live Write|ACK\/Fill|ACK|result_unknown|\u4e0d\u53ef\u6267\u884c|\u53ea\u8bfb\u89c2\u5bdf|\u6837\u672c\u89c2\u5bdf\u53e3\u5f84|Sample|Non-actionable/.test(
      bodyText,
    )
  )
    throw new Error('strategy page exposes engineering copy');
  if (errors.length) throw new Error(`strategy runtime errors: ${errors.join(' | ')}`);
  fs.writeFileSync(
    path.join(outDir, `ignored-noise-${width}x${height}.json`),
    JSON.stringify([...new Set(ignoredNoises)], null, 2),
    'utf8',
  );
  await browser.close();
  console.log(`strategy restoration checks passed at ${width}x${height}`);
}

(async () => {
  await checkViewport(1366, 768);
  await checkViewport(1920, 1080);
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
