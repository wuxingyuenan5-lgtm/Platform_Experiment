import { expect, test, type Browser, type Page, type Route } from '@playwright/test';

const FRONTEND_ORIGIN = 'http://127.0.0.1:4373';

function requiredEnvironment(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required for the hedge-board browser E2E suite`);
  return value;
}

function absoluteUrl(path: string): string {
  if (!path.startsWith('/api/')) return `${FRONTEND_ORIGIN}/#${path}`;
  return new URL(path, FRONTEND_ORIGIN).toString();
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
    sourceTimestamp: '2026-07-30T02:30:00+00:00',
    fetchedAt: '2026-07-30T02:31:00+00:00',
    status: 'ready',
    isStale: false,
    errorCode: null,
    message: null,
  };
}

function dashboardFixture(thresholdYuan: number) {
  const stocks =
    thresholdYuan < 15_000_000_000
      ? [
          {
            securityCode: '600000',
            securityName: '浦发银行',
            swL1Code: '801780',
            swL1Name: '银行',
            swL2Code: '851911',
            swL2Name: '股份制银行Ⅱ',
            turnoverYuan: 12_000_000_000,
            returnPct: 1.2,
          },
        ]
      : [];
  return {
    generatedAt: '2026-07-30T02:31:00+00:00',
    marketDetail: {
      meta: sourceMeta('E2E行情夹具'),
      data: [
        {
          code: '000001',
          name: '上证指数',
          sourceSymbol: 'sh000001',
          close: 3420.12,
          turnoverYuan: 620_000_000_000,
          volatility20Pct: 16.8,
          return1dPct: 0.8,
          returnYtdPct: 8.2,
          returnQtdPct: 3.1,
          return1wPct: 1.4,
          return1mPct: 4.2,
          return1yPct: 12.4,
          distance52wHighPct: -2.1,
          signal1h: '偏强',
          signalDaily: '多头',
          signal3d: '多头',
          signalWeekly: '中性',
          spark: [3370, 3388, 3402, 3420],
        },
        {
          code: '932000',
          name: '中证 2000',
          sourceSymbol: '932000',
          close: 2150.5,
          turnoverYuan: 380_000_000_000,
          volatility20Pct: 24.1,
          return1dPct: 1.3,
          spark: [2080, 2105, 2120, 2150.5],
        },
      ],
    },
    breadth: {
      meta: sourceMeta('E2E市场广度夹具'),
      data: {
        up: 3210,
        down: 1780,
        flat: 120,
        limitUp: 68,
        realLimitUp: 60,
        limitDown: 9,
        realLimitDown: 6,
        activityPct: 72.5,
        breadthState: '偏强',
        speculationState: '活跃',
        tradeDate: '2026-07-30',
      },
    },
    shenwan: {
      meta: sourceMeta('申万行业分类 + E2E聚合夹具'),
      data: {
        sw2Top: [
          {
            rank: 1,
            swL1Code: '801080',
            swL1Name: '电子',
            swL2Code: '801081',
            swL2Name: '半导体',
            returnPct: 2.4,
            turnoverYuan: 180_000_000_000,
            marketSharePct: 8.1,
            netInflowYuan: 8_000_000_000,
          },
          {
            rank: 2,
            swL1Code: '801780',
            swL1Name: '银行',
            swL2Code: '851911',
            swL2Name: '股份制银行Ⅱ',
            returnPct: 1.2,
            turnoverYuan: 120_000_000_000,
            marketSharePct: 5.4,
            netInflowYuan: 3_200_000_000,
          },
        ],
        sw2All: [
          {
            rank: 1,
            swL1Code: '801080',
            swL1Name: '电子',
            swL2Code: '801081',
            swL2Name: '半导体',
            returnPct: 2.4,
            turnoverYuan: 180_000_000_000,
            marketSharePct: 8.1,
            netInflowYuan: 8_000_000_000,
          },
          {
            rank: 2,
            swL1Code: '801780',
            swL1Name: '银行',
            swL2Code: '851911',
            swL2Name: '股份制银行Ⅱ',
            returnPct: 1.2,
            turnoverYuan: 120_000_000_000,
            marketSharePct: 5.4,
            netInflowYuan: 3_200_000_000,
          },
        ],
        threshold: {
          thresholdYuan,
          operator: '>',
          industries: stocks.length
            ? [
                {
                  swL1Code: '801780',
                  swL1Name: '银行',
                  swL2Code: '851911',
                  swL2Name: '股份制银行Ⅱ',
                  stockCount: 1,
                },
              ]
            : [],
          stocks,
          unmatchedSecurityCodes: [],
        },
        unmatchedSecurityCodes: [],
      },
    },
    emotion: {
      meta: sourceMeta('E2E短线情绪夹具'),
      data: {
        limitUpCount: 68,
        brokenBoardCount: 14,
        limitDownCount: 9,
        highestBoardCount: 5,
        consecutiveBoardCount: 21,
        sealRatePct: 82.9,
        breakRatePct: 17.1,
        promotionRatePct: 31.4,
        ladder: [
          { boardCount: '2板', stockCount: 12 },
          { boardCount: '3板', stockCount: 5 },
          { boardCount: '4板', stockCount: 3 },
          { boardCount: '5板及以上', stockCount: 1 },
        ],
        leaders: [
          {
            securityCode: '600000',
            securityName: '浦发银行',
            boardCount: 2,
            turnoverYuan: 12_000_000_000,
          },
        ],
        tradeDate: '2026-07-30',
      },
    },
  };
}

function snapshotFixture(code: string) {
  return {
    securityCode: code,
    securityName: code === '600000' ? '浦发银行' : '测试股票',
    generatedAt: '2026-07-30T02:32:00+00:00',
    completenessPct: 100,
    modules: {
      quoteValuation: {
        meta: sourceMeta('E2E个股行情夹具'),
        data: { price: 12.34, peTtm: 6.8, pb: 0.72 },
      },
      financials: {
        meta: sourceMeta('E2E财务夹具'),
        data: { period: '2026Q2', roe: '8.2%' },
      },
      shenwan: {
        meta: sourceMeta('申万行业分类'),
        data: { swL1Name: '银行', swL2Name: '股份制银行Ⅱ' },
      },
    },
  };
}

async function mockResearchRoutes(page: Page): Promise<void> {
  await page.route('**/api/v1/research/a-share/dashboard**', async (route: Route) => {
    const url = new URL(route.request().url());
    const thresholdYuan = Number(url.searchParams.get('thresholdYuan') || 10_000_000_000);
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(dashboardFixture(thresholdYuan)) });
  });
  await page.route('**/api/v1/research/a-share/stocks/*/snapshot', async (route: Route) => {
    const match = route.request().url().match(/\/stocks\/(\d{6})\/snapshot/);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(snapshotFixture(match?.[1] || '600000')),
    });
  });
}

async function openAuthenticatedPage(browser: Browser, username: string, password: string) {
  const context = await browser.newContext({ locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await context.newPage();
  await mockResearchRoutes(page);
  await loginWithUi(page, username, password);
  return { context, page };
}

test('covers A-share research workflow and account-level watchlist persistence', async ({ browser }) => {
  const username = requiredEnvironment('E2E_CEO_USERNAME');
  const password = requiredEnvironment('E2E_CEO_PASSWORD');

  const first = await openAuthenticatedPage(browser, username, password);
  await first.page.goto(absoluteUrl('/hedge-board/a-share'));

  await expect(first.page.getByRole('heading', { name: '大盘表现' })).toBeVisible();
  await expect(first.page.getByRole('heading', { name: '大盘广度' })).toBeVisible();
  await expect(first.page.getByRole('heading', { name: '市场明细' })).toBeVisible();
  await expect(first.page.getByRole('heading', { name: '申万板块' })).toBeVisible();
  await expect(first.page.getByRole('heading', { name: '短线情绪' })).toBeVisible();
  await expect(first.page.getByRole('heading', { name: '自选股' })).toBeVisible();
  await expect(first.page.getByText('账号已同步', { exact: true })).toBeVisible();

  await first.page.getByRole('button', { name: '全部申万二级行业' }).click();
  await first.page.getByLabel('搜索二级行业').fill('半导体');
  await expect(first.page.getByText('显示 1 / 2 个行业')).toBeVisible();
  await first.page.getByRole('button', { name: '升序 ↑' }).click();
  await expect(first.page.getByText(/当前排序：.*降序/)).toBeVisible();

  await first.page.getByLabel('50亿元').check();
  const thresholdResponse = first.page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/research/a-share/dashboard') &&
      response.url().includes('thresholdYuan=5000000000'),
  );
  await first.page.getByRole('button', { name: '应用' }).click();
  expect((await thresholdResponse).ok()).toBeTruthy();
  await expect(first.page.getByText('共 1 只')).toBeVisible();

  const watchlistSection = first.page.locator('#a-share-watchlist');
  await watchlistSection.getByRole('button', { name: '添加自选' }).click();
  await watchlistSection.getByLabel('股票代码').fill('SH600000');
  await watchlistSection.getByLabel('股票名称').fill('浦发银行');
  await watchlistSection.getByLabel('分组').fill('银行观察');
  const saveResponse = first.page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/me/research-watchlist') &&
      response.request().method() === 'PUT',
  );
  await watchlistSection.getByRole('button', { name: '保存' }).click();
  expect((await saveResponse).ok()).toBeTruthy();
  await expect(watchlistSection.getByText('浦发银行', { exact: true })).toBeVisible();
  await expect(watchlistSection.getByText('账号已同步', { exact: true })).toBeVisible();

  const snapshotResponse = first.page.waitForResponse(
    (response) => response.url().includes('/api/v1/research/a-share/stocks/600000/snapshot'),
  );
  await watchlistSection.getByRole('button', { name: /浦发银行/ }).click();
  expect((await snapshotResponse).ok()).toBeTruthy();
  await expect(first.page.getByText('完整度 100%')).toBeVisible();
  await expect(first.page.getByRole('button', { name: /行情与估值/ })).toBeVisible();
  await first.context.close();

  const second = await openAuthenticatedPage(browser, username, password);
  await second.page.goto(absoluteUrl('/hedge-board/a-share'));
  const restoredWatchlist = second.page.locator('#a-share-watchlist');
  await expect(restoredWatchlist.getByText('账号已同步', { exact: true })).toBeVisible();
  await expect(restoredWatchlist.getByText('浦发银行', { exact: true })).toBeVisible();
  await expect(restoredWatchlist.getByText('银行观察', { exact: true })).toBeVisible();
  await second.context.close();
});
