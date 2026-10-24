const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const { researchModules } = load('src/views/hedgeBoard/nativeData/dashboardClean.ts');
const { buildSourceSeriesOptions, unitText } = load('src/views/hedgeBoard/charts/sourceSeriesOptions.ts');

test('China policy adjustment events use effective-date steps and native units remain distinct', () => {
  const result = buildSourceSeriesOptions([{ seriesId: 'rrr', label: 'RRR', unit: 'percent', frequency: 'event', observations: [{ date: '2024-01-01', value: 10 }, { date: '2025-01-01', value: 9 }] }], ['blue']);
  assert.equal(result.series[0].step, 'end');
  assert.equal(unitText('usd_100million'), '亿美元');
  assert.equal(unitText('cny_100million'), '亿元');
  assert.equal(unitText('hours'), '小时');
});

test('China expansion covers liquidity, policy, domestic cycle, labor, external demand and price composition', () => {
  const sections = researchModules.find(module => module.id === 'macro').sections;
  for (const [sectionId, keys] of Object.entries({
    'macro-liquidity': ['money-stock', 'rrr', 'reserves'],
    'macro-rates': ['policy-rates', 'rates', 'treasury'],
    'macro-growth': ['investment', 'property', 'trade', 'fiscal', 'profits', 'labor', 'youth-labor'],
    'macro-inflation': ['price-details', 'ppi-details'],
    'macro-risk-appetite': ['confidence', 'fx'],
  })) {
    const widgets = sections.find(section => section.id === sectionId).widgets;
    for (const key of keys) assert.ok(widgets.some(w => w.localKey === `macro-cn-${key}` && w.region === '中国'), `${sectionId}/${key}`);
  }
});

test('China macro groups follow US groups on each requested topic, without empty or duplicate charts', () => {
  const macro = researchModules.find(module => module.id === 'macro');
  for (const id of ['macro-rates', 'macro-growth', 'macro-inflation', 'macro-risk-appetite']) {
    const { widgets } = macro.sections.find(section => section.id === id);
    const firstChina = widgets.findIndex(widget => widget.region === '中国');
    assert.ok(firstChina > 0, id);
    assert.ok(widgets.slice(0, firstChina).every(widget => widget.region === '美国'));
    assert.ok(widgets.slice(firstChina).every(widget => widget.region === '中国' && widget.localKey.startsWith('macro-cn-')));
    assert.equal(new Set(widgets.map(widget => widget.localKey || widget.title)).size, widgets.length);
  }
});

test('Fed assets and liabilities are separate charts; cumulative movement follows each IV chart', () => {
  const macro = researchModules.find(module => module.id === 'macro');
  const liquidity = macro.sections.find(section => section.id === 'macro-liquidity');
  assert.ok(liquidity.widgets.some(widget => widget.localKey === 'macro-fed-balance-structure'));
  assert.ok(liquidity.widgets.some(widget => widget.localKey === 'macro-fed-assets'));
  for (const domain of ['gold', 'crypto']) {
    const market = researchModules.find(module => module.id === domain).sections.find(section => section.id === `${domain}-market`);
    assert.equal(market.widgets[0].kind, 'advanced-chart');
    assert.equal(market.widgets[1].localKey, domain === 'gold' ? 'gold-gvz' : 'crypto-dvol');
    assert.equal(market.widgets[2].localKey, `${domain}-intraday-cumulative-volatility`);
    assert.ok(market.widgets.findIndex(widget => widget.localKey === `${domain}-market-detail-table`) > 1);
  }
});
