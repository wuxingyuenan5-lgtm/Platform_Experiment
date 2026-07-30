import type { Page, Route } from '@playwright/test';

import { mockResearchRoutes } from '../hedge-board/researchFixtures';

const FIXED_TIME = '2026-07-30T08:30:00+08:00';

function fulfill(route: Route, payload: unknown): Promise<void> {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(payload),
  });
}

function sourceMeta(source: string) {
  return {
    source,
    sourceTimestamp: '2026-07-30T00:30:00+00:00',
    fetchedAt: '2026-07-30T00:31:00+00:00',
    status: 'ready',
    isStale: false,
    errorCode: null,
    message: null,
  };
}

export async function mockPlatformVisualRoutes(page: Page): Promise<void> {
  await mockResearchRoutes(page);

  await page.route(/\/api\/v1\/research\/macro\/expectations(?:\?.*)?$/, (route) =>
    fulfill(route, {
      generatedAt: '2026-07-30T00:31:00+00:00',
      events: {
        meta: sourceMeta('E2E事件概率夹具'),
        data: [
          {
            eventId: 'fed-cut-september',
            category: 'monetary_policy',
            title: '美联储9月降息',
            outcome: '是',
            currentProbabilityPct: 64.2,
            change1dPctPoints: 1.4,
            change7dPctPoints: 4.8,
            liquidityLabel: '高',
            expiryAt: '2026-09-17T00:00:00+00:00',
            sourceUrl: 'https://example.invalid/fed-cut',
            history: [
              { observedAt: '2026-07-24T00:00:00+00:00', probabilityPct: 59.4 },
              { observedAt: '2026-07-27T00:00:00+00:00', probabilityPct: 62.1 },
              { observedAt: '2026-07-30T00:00:00+00:00', probabilityPct: 64.2 },
            ],
          },
          {
            eventId: 'us-recession-2027',
            category: 'macro',
            title: '美国在2027年前进入衰退',
            outcome: '是',
            currentProbabilityPct: 27.8,
            change1dPctPoints: -0.6,
            change7dPctPoints: -2.1,
            liquidityLabel: '中',
            expiryAt: '2026-12-31T00:00:00+00:00',
            sourceUrl: 'https://example.invalid/recession',
            history: [
              { observedAt: '2026-07-24T00:00:00+00:00', probabilityPct: 31.0 },
              { observedAt: '2026-07-27T00:00:00+00:00', probabilityPct: 29.2 },
              { observedAt: '2026-07-30T00:00:00+00:00', probabilityPct: 27.8 },
            ],
          },
          {
            eventId: 'geopolitical-risk',
            category: 'geopolitics',
            title: '主要地缘风险在季度内缓和',
            outcome: '是',
            currentProbabilityPct: 41.5,
            change1dPctPoints: 0.2,
            change7dPctPoints: 3.0,
            liquidityLabel: '中',
            expiryAt: '2026-09-30T00:00:00+00:00',
            sourceUrl: 'https://example.invalid/geopolitics',
            history: [
              { observedAt: '2026-07-24T00:00:00+00:00', probabilityPct: 38.5 },
              { observedAt: '2026-07-27T00:00:00+00:00', probabilityPct: 40.0 },
              { observedAt: '2026-07-30T00:00:00+00:00', probabilityPct: 41.5 },
            ],
          },
        ],
      },
    }),
  );

  const accounts = [
    {
      id: 1,
      name: '组合主账户',
      account_type: 'fund',
      account_address: 'DEMO-FUND-001',
      initial_capital: 1_000_000,
      arbitrary_flag: false,
      status: 'active',
      created_at: FIXED_TIME,
      updated_at: FIXED_TIME,
      total_asset: 1_126_800,
      available_fund: 684_200,
      asset_updated_at: FIXED_TIME,
      platform: 'Platform',
      accountName: '组合主账户',
    },
    {
      id: 2,
      name: '策略执行账户',
      account_type: 'strategy',
      account_address: 'DEMO-STRATEGY-001',
      initial_capital: 500_000,
      arbitrary_flag: false,
      status: 'active',
      created_at: FIXED_TIME,
      updated_at: FIXED_TIME,
      total_asset: 548_600,
      available_fund: 391_400,
      asset_updated_at: FIXED_TIME,
      platform: 'Simulation',
      accountName: '策略执行账户',
    },
  ];

  await page.route(/\/api\/v1\/accounts(?:\?.*)?$/, (route) => fulfill(route, accounts));
  await page.route(/\/api\/v1\/data\/total(?:\?.*)?$/, (route) =>
    fulfill(route, { total_asset: 1_675_400, updated_at: FIXED_TIME }),
  );
  await page.route(/\/api\/v1\/data\/net-value(?:\?.*)?$/, (route) =>
    fulfill(route, [
      {
        created_at: '2026-07-30T06:00:00+08:00',
        account_id: 1,
        total_asset: 1_102_000,
        available_fund: 671_000,
        unit_net_worth: 1.102,
        current_drawdown: 0.012,
      },
      {
        created_at: '2026-07-30T07:00:00+08:00',
        account_id: 1,
        total_asset: 1_118_500,
        available_fund: 679_500,
        unit_net_worth: 1.1185,
        current_drawdown: 0.008,
      },
      {
        created_at: FIXED_TIME,
        account_id: 1,
        total_asset: 1_126_800,
        available_fund: 684_200,
        unit_net_worth: 1.1268,
        current_drawdown: 0.006,
      },
    ]),
  );
  await page.route(/\/product\/nav\/productRatio(?:\?.*)?$/, (route) =>
    fulfill(route, [
      { name: '权益类', value: 620_000, valueUSD: 620_000, percent: 0.37 },
      { name: '固收类', value: 415_000, valueUSD: 415_000, percent: 0.25 },
      { name: '商品策略', value: 335_000, valueUSD: 335_000, percent: 0.2 },
      { name: '现金及其他', value: 305_400, valueUSD: 305_400, percent: 0.18 },
    ]),
  );
  await page.route(/\/exchange\/(?:\?.*)?$/, (route) =>
    fulfill(route, { rate: 7.18, symbol: 'USDCNY', updated_at: FIXED_TIME }),
  );
  await page.route(/\/risk\/api\/v1\/risk-records\/(?:\?.*)?$/, (route) =>
    fulfill(route, [
      {
        id: 101,
        title: '策略集中度检查',
        content: '组合集中度处于预警线以内',
        status: 'resolved',
        severity: 'medium',
        created_at: FIXED_TIME,
      },
      {
        id: 102,
        title: '数据源时效检查',
        content: '研究数据夹具状态正常',
        status: 'pending',
        severity: 'low',
        created_at: '2026-07-30T08:10:00+08:00',
      },
    ]),
  );
  await page.route(/\/notifications\/api\/v1\/messages\/(?:\?.*)?$/, (route) =>
    fulfill(route, [
      {
        id: 201,
        title: 'EOD对账完成',
        content: '模拟环境EOD核对已完成',
        status: 'read',
        read: true,
        created_at: FIXED_TIME,
      },
      {
        id: 202,
        title: '研究数据状态',
        content: '视觉基线使用确定性夹具',
        status: 'unread',
        read: false,
        created_at: '2026-07-30T08:20:00+08:00',
      },
    ]),
  );
  await page.route(/\/health(?:\?.*)?$/, (route) =>
    fulfill(route, { status: 'ok', service: 'data-service', update_frequency: '5m' }),
  );
}
