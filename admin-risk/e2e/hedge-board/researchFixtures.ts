import type { Page, Route } from '@playwright/test';

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

function shenwanRow(
  rank: number,
  swL1Code: string,
  swL1Name: string,
  swL2Code: string,
  swL2Name: string,
  turnoverYuan: number,
) {
  return {
    rank,
    swL1Code,
    swL1Name,
    swL2Code,
    swL2Name,
    returnPct: rank === 1 ? 2.4 : 1.2,
    turnoverYuan,
    marketSharePct: rank === 1 ? 8.1 : 5.4,
    netInflowYuan: rank === 1 ? 8_000_000_000 : 3_200_000_000,
  };
}

function dashboardFixture(thresholdYuan: number) {
  const thresholdStocks =
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
  const sw2All = [
    shenwanRow(1, '801080', '电子', '801081', '半导体', 180_000_000_000),
    shenwanRow(2, '801780', '银行', '851911', '股份制银行Ⅱ', 120_000_000_000),
  ];
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
        sw2Top: sw2All,
        sw2All,
        threshold: {
          thresholdYuan,
          operator: '>',
          industries: thresholdStocks.length
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
          stocks: thresholdStocks,
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

export async function mockResearchRoutes(page: Page): Promise<void> {
  await page.route('**/api/v1/research/a-share/dashboard**', async (route: Route) => {
    const url = new URL(route.request().url());
    const thresholdYuan = Number(url.searchParams.get('thresholdYuan') || 10_000_000_000);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(dashboardFixture(thresholdYuan)),
    });
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
