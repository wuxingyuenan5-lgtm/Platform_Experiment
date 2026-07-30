import { expect, test, type APIResponse, type Page, type Route } from '@playwright/test';

const FRONTEND_ORIGIN = 'http://127.0.0.1:4373';
const WATCHLIST_URL = '/api/v1/me/research/a-share/watchlist';

interface AuthenticationResponse {
  csrfToken: string;
}

interface AccountWatchlistResponse {
  version: number;
}

function requiredEnvironment(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required for the hedge-board browser E2E suite`);
  return value;
}

function absoluteUrl(path: string): string {
  if (!path.startsWith('/api/')) return `${FRONTEND_ORIGIN}/#${path}`;
  return new URL(path, FRONTEND_ORIGIN).toString();
}

async function jsonResponse<T>(response: APIResponse): Promise<T> {
  const body = await response.text();
  expect(response.ok(), `${response.status()} ${response.statusText()}\n${body}`).toBeTruthy();
  return body ? (JSON.parse(body) as T) : (undefined as T);
}

async function loginWithUi(page: Page, username: string, password: string): Promise<void> {
  await page.goto(absoluteUrl('/login'));
  await expect(page.getByText('欢迎登录', { exact: true })).toBeVisible();
  await page.getByPlaceholder('请输入账号').fill(username);
  await page.getByPlaceholder('请输入密码').fill(password);
  const loginResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/auth/login') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '登录', exact: true }).click();
  expect((await loginResponse).ok()).toBeTruthy();
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/, { timeout: 20_000 });
}

function sourceMeta(source: string) {
  return {
    source,
    sourceTimestamp: '2026-07-30T01:00:00+00:00',
    fetchedAt: '2026-07-30T01:00:01+00:00',
    status: 'ready',
    isStale: false,
    errorCode: null,
    message: null,
  };
}

function indexRow(code: string, name: string, return1dPct: number) {
  return {
    code,
    name,
    sourceSymbol: code,
    close: code === '000001' ? 3650.12 : 2410.2,
    turnoverYuan: code === '000001' ? 680_000_000_000 : 210_000_000_000,
    volatility20Pct: code === '000001' ? 14.2 : 22.5,
    return1dPct,
    returnYtdPct: 8.4,
    returnQtdPct: 2.1,
    return1wPct: 1.4,
    return1mPct: 3.2,
    return1yPct: 12.8,
    distance52wHighPct: -1.6,
    signal1h: return1dPct >= 0 ? '▲' : '▼',
    signalDaily: '▲',
    signal3d: '▲',
    signalWeekly: '▲',
    spark: [3500, 3525, 3560, 3600, 3650],
  };
}

const industryRows = [
  {
    rank: 1,
    swL1Code: '801080',
    swL1Name: '电子',
    swL2Code: '801081',
    swL2Name: '半导体',
    returnPct: 2.15,
    turnoverYuan: 188_000_000_000,
    marketSharePct: 12.4,
    netInflowYuan: 8_600_000_000,
  },
  {
    rank: 2,
    swL1Code: '801770',
    swL1Name: '通信',
    swL2Code: '801102',
    swL2Name: '通信设备',
    returnPct: 1.08,
    turnoverYuan: 96_000_000_000,
    marketSharePct: 6.3,
    netInflowYuan: 2_100_000_000,
  },
  {
    rank: 3,
    swL1Code: '801750',
    swL1Name: '计算机',
    swL2Code: '801752',
    swL2Name: '软件开发',
    returnPct: -0.42,
    turnoverYuan: 62_000_000_000,
    marketSharePct: 4.1,
    netInflowYuan: -800_000_000,
  },
];

const turnoverStocks = [
  {
    securityCode: '600519',
    securityName: '贵州茅台',
    swL1Code: '801120',
    swL1Name: '食品饮料',
    swL2Code: '801123',
    swL2Name: '白酒',
    turnoverYuan: 12_600_000_000,
    returnPct: 1.2,
  },
  {
    securityCode: '300750',
    securityName: '宁德时代',
    swL1Code: '801730',
    swL1Name: '电力设备',
    swL2Code: '801733',
    swL2Name: '电池',
    turnoverYuan: 10_800_000_000,
    returnPct: 0.8,
  },
];

function dashboardFixture(thresholdYuan: number) {
  const thresholdStocks = turnoverStocks.filter((item) => item.turnoverYuan > thresholdYuan);
  return {
    generatedAt: '2026-07-30T01:00:01+00:00',
    marketDetail: {
      meta: sourceMeta('公开指数行情'),
      data: [indexRow('000001', '上证指数', 0.62), indexRow('932000', '中证2000', -0.18)],
    },
    breadth: {
      meta: sourceMeta('公开市场活跃度'),
      data: {
        up: 3100,
        down: 1900,
        flat: 110,
        limitUp: 68,
        realLimitUp: 55,
        limitDown: 7,
        realLimitDown: 4,
        activityPct: 63.2,
        breadthState: '偏强',
        speculationState: '普通',
        tradeDate: '2026-07-30',
      },
    },
    shenwan: {
      meta: sourceMeta('申万分类 / 公开行情聚合'),
      data: {
        sw2Top: industryRows,
        sw2All: industryRows,
        threshold: {
          thresholdYuan,
          operator: '>',
          industries: thresholdStocks.map((item) => ({
            swL1Code: item.swL1Code,
            swL1Name: item.swL1Name,
            swL2Code: item.swL2Code,
            swL2Name: item.swL2Name,
            stockCount: 1,
          })),
          stocks: thresholdStocks,
          unmatchedSecurityCodes: [],
        },
        unmatchedSecurityCodes: [],
      },
    },
    emotion: {
      meta: sourceMeta('公开涨停池'),
      data: {
        limitUpCount: 68,
        brokenBoardCount: 16,
        limitDownCount: 7,
        highestBoardCount: 5,
        consecutiveBoardCount: 22,
        sealRatePct: 80.95,
        breakRatePct: 19.05,
        promotionRatePct: 31.4,
        ladder: [
          { boardCount: '2板', stockCount: 12 },
          { boardCount: '3板', stockCount: 6 },
          { boardCount: '4板', stockCount: 3 },
          { boardCount: '5板+', stockCount: 1 },
        ],
        leaders: [
          {
            securityCode: '000001',
            securityName: '示例龙头',
            boardCount: 5,
            turnoverYuan: 5_000_000_000,
          },
        ],
        tradeDate: '2026-07-30',
      },
    },
  };
}

function stockFixture(code: string) {
  const module = (data: unknown) => ({ meta: sourceMeta('公开数据源'), data });
  return {
    securityCode: code,
    securityName: '贵州茅台',
    generatedAt: '2026-07-30T01:00:02+00:00',
    completenessPct: 100,
    modules: {
      quoteValuation: module({ price: 1488.8, peTtm: 24.6, pb: 7.2 }),
      consensus: module({ forwardPe: 22.1, peg: 1.5, analystCount: 36 }),
      financials: module({ period: '2026Q2', roe: 18.2 }),
      valuationPercentile: module({ period: '近5年', pe: 35, pb: 42 }),
      reports: module([{ title: '公司跟踪报告' }]),
      announcements: module([{ title: '2026年半年度报告' }]),
      news: module([{ title: '公司经营动态' }]),
      margin: module({ financingBalance: 100 }),
      holders: module({ latest: 120000 }),
      fundFlow: module({ mainNet20d: 8.6 }),
      dividends: module([{ year: 2025, amount: 10 }]),
      blockTrades: module([]),
      dragonTiger: module({ records: [] }),
      lockup: module({ upcoming: [] }),
      investorQa: module([{ question: '经营展望', answer: '稳健经营' }]),
      shenwan: module({ swL1Name: '食品饮料', swL2Name: '白酒' }),
    },
  };
}

async function fulfillResearchRoute(route: Route): Promise<void> {
  const url = new URL(route.request().url());
  if (url.pathname.endsWith('/research/a-share/dashboard')) {
    const threshold = Number(url.searchParams.get('thresholdYuan') || 10_000_000_000);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(dashboardFixture(threshold)),
    });
    return;
  }
  const stockMatch = url.pathname.match(/\/research\/a-share\/stocks\/(\d{6})\/snapshot$/);
  if (stockMatch) {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(stockFixture(stockMatch[1])),
    });
    return;
  }
  await route.continue();
}

async function clearAccountWatchlist(page: Page, csrfToken: string): Promise<number> {
  const current = await jsonResponse<AccountWatchlistResponse>(
    await page.request.get(absoluteUrl(WATCHLIST_URL)),
  );
  const cleared = await jsonResponse<AccountWatchlistResponse>(
    await page.request.put(absoluteUrl(WATCHLIST_URL), {
      headers: {
        Origin: FRONTEND_ORIGIN,
        'X-CSRF-Token': csrfToken,
      },
      data: { expectedVersion: current.version, items: [] },
    }),
  );
  return cleared.version;
}

test('completes hedge-board account persistence and research interactions without Live Write', async ({
  page,
}) => {
  const username = requiredEnvironment('E2E_CEO_USERNAME');
  const password = requiredEnvironment('E2E_CEO_PASSWORD');

  await page.route('**/api/v1/research/**', fulfillResearchRoute);
  await loginWithUi(page, username, password);

  const authentication = await jsonResponse<AuthenticationResponse>(
    await page.request.get(absoluteUrl('/api/v1/auth/me')),
  );
  expect(await clearAccountWatchlist(page, authentication.csrfToken)).toBeGreaterThan(0);

  await page.goto(absoluteUrl('/hedge-board/a-share'));
  await expect(page).toHaveURL(/#\/hedge-board\/a-share$/);
  await expect(page.getByRole('heading', { name: '大盘表现' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '申万板块' })).toBeVisible();
  await expect(page.getByText('已同步到账号', { exact: true })).toBeVisible();
  await expect(page.getByText('暂无自选股，空列表会被正常保留并同步到当前账号。')).toBeVisible();

  await page.getByRole('button', { name: '添加第一只自选股' }).click();
  await page.getByPlaceholder('600519 / SH600519').fill('SH600519');
  await page.getByPlaceholder('例如 贵州茅台').fill('贵州茅台');
  await page.getByPlaceholder('例如 核心观察').fill('核心观察');
  const accountSave = page.waitForResponse(
    (response) =>
      response.url().endsWith(WATCHLIST_URL) && response.request().method() === 'PUT',
  );
  await page.getByRole('button', { name: '保存', exact: true }).click();
  expect((await accountSave).ok()).toBeTruthy();
  await expect(page.getByText('已同步到账号', { exact: true })).toBeVisible();
  await expect(page.locator('.stock-button').filter({ hasText: '贵州茅台' })).toBeVisible();

  await page.evaluate(() => window.localStorage.removeItem('vg_a_share_watchlist_v1'));
  await page.reload();
  await expect(page.getByText('已同步到账号', { exact: true })).toBeVisible();
  await expect(page.locator('.stock-button').filter({ hasText: '贵州茅台' })).toBeVisible();

  await page.getByRole('button', { name: /全部申万二级行业/ }).click();
  await expect(page.getByText('显示 3 / 3 个行业')).toBeVisible();
  await page.getByLabel('申万一级').selectOption('电子');
  await expect(page.getByText('显示 1 / 3 个行业')).toBeVisible();
  await page.getByRole('button', { name: '降序 ↓' }).click();
  await expect(page.getByText('当前排序：成交额 · 升序')).toBeVisible();
  await page.getByRole('button', { name: '重置筛选' }).click();
  await expect(page.getByText('显示 3 / 3 个行业')).toBeVisible();

  await page.getByLabel('50亿元').check();
  const thresholdRefresh = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/research/a-share/dashboard') &&
      response.url().includes('thresholdYuan=5000000000'),
  );
  await page.getByRole('button', { name: '应用', exact: true }).click();
  expect((await thresholdRefresh).ok()).toBeTruthy();
  await expect(page.getByText('当前口径：成交额 > 50.00亿')).toBeVisible();

  await page.getByPlaceholder('输入6位A股代码').fill('600519');
  const snapshotResponse = page.waitForResponse((response) =>
    response.url().endsWith('/api/v1/research/a-share/stocks/600519/snapshot'),
  );
  await page.getByRole('button', { name: '查询', exact: true }).click();
  expect((await snapshotResponse).ok()).toBeTruthy();
  await expect(page.getByText('完整度 100%')).toBeVisible();
  await expect(page.locator('.snapshot-module__body')).toHaveCount(0);
  await page.getByRole('button', { name: '全部展开' }).click();
  await expect(page.locator('.snapshot-module__body')).toHaveCount(16);
});
