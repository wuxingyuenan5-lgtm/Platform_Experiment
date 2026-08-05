'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const root = path.resolve(__dirname, '..');

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

function assertUses(source, values, context) {
  for (const value of values) {
    assert.equal(source.includes(value), true, `${context} does not use ${value}`);
  }
}

test('dashboard renders the reference information architecture', () => {
  const source = read('src/views/dashboard/index.vue');
  assertUses(
    source,
    [
      'PageWrapper',
      'dashboard-original-structure',
      '欢迎来到',
      '全球变量',
      '顺应时代大势，洞悉投资先机',
      '全球市场概览',
      '投资组合总览',
      '市场脉搏',
      '组合概览',
      '策略概览',
      '重要日历',
      "@/data/sample/dashboard",
      'sample:dashboard-restoration',
    ],
    'dashboard',
  );
});

test('strategy management imports and renders the reference component system', () => {
  const source = read('src/views/strategy/management/index.vue');
  assertUses(
    source,
    [
      'CompactSegmentTabs',
      'StrategyPnlPanel',
      'StrategyKpiGrid',
      'StrategyCapitalFinanceBoard',
      'StrategyCapitalNetValueBoard',
      'StrategyCapitalRulePanel',
      'StrategyCapitalRiskOverview',
      'StrategyRuntimePanel',
      'StrategyCurveGrid',
      'StrategyRecordsPanel',
      'getCrossSpreadObservability',
      "@/data/sample/strategy",
    ],
    'strategy management',
  );
  assert.match(source, /<StrategyPnlPanel\b/);
  assert.match(source, /<StrategyKpiGrid\b/);
  assert.match(source, /<StrategyRecordsPanel\b/);
});

test('funding carry imports and renders all four reference components', () => {
  const source = read('src/views/strategy/funding-carry/index.vue');
  assertUses(
    source,
    [
      'FundingMarketBoard',
      'FundingChartPanel',
      'FundingDetailPanel',
      'FundingOrderPanel',
      "@/data/sample/funding",
      'funding-original-structure',
    ],
    'funding carry',
  );
  for (const component of [
    'FundingMarketBoard',
    'FundingChartPanel',
    'FundingDetailPanel',
    'FundingOrderPanel',
  ]) {
    assert.match(source, new RegExp(`<${component}\\b`));
  }
});

test('spread research renders restored analysis components and the current execution workspace', () => {
  const source = read('src/views/strategy/spread-carry/index.vue');
  assertUses(
    source,
    [
      'SpreadAnalysisWorkspaceHeader',
      'SpreadAnalysisOverview',
      'SpreadStatisticsSection',
      'CrossVenueExecutionWorkspace',
      "@/data/sample/spread",
      'spread-research-chart',
      'ACK/Fill 区分',
      'result_unknown',
    ],
    'spread carry',
  );
  assert.match(source, /<CrossVenueExecutionWorkspace\b/);
});

test('financial AI, news/wealth and settings retain reference product shells', () => {
  const financialAi = read('src/views/financialAi/index.vue');
  assertUses(
    financialAi,
    [
      'PageWrapper',
      'financial-ai-original-structure',
      '研究辅助与情景推演中枢',
      '专题研究输入与结果区',
      'not-configured:financial-ai-provider',
      '暂无模型结果',
    ],
    'financial AI',
  );

  const news = read('src/views/newsCalendar/index.vue');
  assertUses(
    news,
    [
      'news-calendar-original-structure',
      'TradingViewEconomicCalendarPanel',
      'news-asset-tabs',
      'wealth-toolbar',
      "@/data/sample/news",
      'sample:news-digest',
      'sample:wealth-campaigns',
    ],
    'news and wealth',
  );

  const settings = read('src/views/settings/index.vue');
  assertUses(
    settings,
    [
      'settings-original-structure',
      '当前登录',
      '本地服务配置',
      '个人账号自助管理',
      '数据服务状态',
      'not-configured:settings-write-owner',
      "router.push('/account/index')",
    ],
    'settings',
  );
});

test('sample data is isolated from production APIs and remains non-actionable', () => {
  for (const relativePath of [
    'src/data/sample/dashboard/index.ts',
    'src/data/sample/strategy/index.ts',
    'src/data/sample/funding/index.ts',
    'src/data/sample/spread/index.ts',
    'src/data/sample/news/index.ts',
  ]) {
    const source = read(relativePath);
    assert.match(source, /state:\s*'sample'/, `${relativePath} lacks sample state`);
    assert.match(source, /actionable:\s*false/, `${relativePath} is not explicitly non-actionable`);
    assert.doesNotMatch(source, /Math\.random|fetch\(|axios\.|\/api\//);
  }
});
