const test = require('node:test');
const assert = require('node:assert/strict');
const load = require('./load-strategy-module.cjs')();
const { buildRegionalStackOptions, buildSourceSeriesOptions } = load('src/views/hedgeBoard/charts/sourceSeriesOptions.ts');

const row = (region, observations, period = 'weekly') => ({
  seriesId: `wgc_etf_${period}_${region}`, label: region, unit: 'USD',
  observations: observations.map(([date, value]) => ({ date, value })),
});

test('regional bars share a stack and dates, exclude aggregate, and preserve missing/negative/zero values', () => {
  const source = [
    row('global', [['2026-10-02', '7']]),
    row('north_america', [['2026-10-02', '10.123456789'], ['2026-10-09', null]]),
    row('europe', [['2026-10-09', '0'], ['2026-10-02', '-3.123456789']]),
    row('asia', [['2026-10-02', null], ['2026-10-09', '2']]),
    row('other', [['2026-10-09', '-1']]),
  ];
  const before = JSON.stringify(source);
  const option = buildRegionalStackOptions(source);
  assert.equal(option.series.length, 4);
  assert.ok(option.series.every(s => s.type === 'bar' && s.stack === 'regional-flow' && s.stackStrategy === 'samesign'));
  assert.deepEqual(option.series.map(s => s.data.map(p => p[0])), Array(4).fill([Date.parse('2026-10-02'), Date.parse('2026-10-09')]));
  assert.deepEqual(option.series.map(s => s.data.map(p => p[1])), [[10.123456789, null], [-3.123456789, 0], [null, 2], [null, -1]]);
  assert.match(option.tooltip.formatter([{ seriesIndex: 0, data: option.series[0].data[0] }]), /10\.123456789 USD/);
  assert.equal(JSON.stringify(source), before);
});

test('colors persist across frequency/order/filter changes; ordinary charts stay lines', () => {
  const weekly = buildRegionalStackOptions([row('europe', []), row('asia', [])]);
  const monthly = buildRegionalStackOptions([row('asia', [], 'monthly'), row('europe', [], 'monthly')]);
  assert.equal(weekly.series[0].itemStyle.color, monthly.series[1].itemStyle.color);
  assert.equal(weekly.series[1].itemStyle.color, monthly.series[0].itemStyle.color);
  assert.equal(buildSourceSeriesOptions([row('asia', [])], ['blue']).series[0].type, 'line');
});


test('mixed flow charts keep bars on zero-based flow axis and a separate price line through legend filtering', () => {
  const flow = { seriesId: 'spdr_holdings_change', label: 'Flow', unit: 'tonnes', frequency: 'daily', observations: [{date:'2026-10-09',value:'-2.123456789'}, {date:'2026-10-10',value:null}] };
  const price = { seriesId: 'gold_futures_close', label: 'Price', unit: 'USD/oz', observations: [{date:'2026-10-09',value:'4000.50'}] };
  const option = buildSourceSeriesOptions([flow, price], ['#165dff','#0f8b6d'], undefined, [flow.seriesId]);
  assert.deepEqual(option.series.map(s=>s.type), ['bar','line']);
  assert.deepEqual(option.series.map(s=>s.yAxisIndex), [0,1]);
  assert.deepEqual(option.yAxis.map(a=>a.scale), [false,true]);
  assert.equal(option.series[0].data[1][1], null);
  assert.match(option.tooltip.formatter([{seriesIndex:0,data:option.series[0].data[0]}]), /-2.123456789/);
  const priceOnly = buildSourceSeriesOptions([price], ['#0f8b6d'], undefined, [flow.seriesId]);
  assert.equal(priceOnly.series[0].type, 'line');
  const flowOnly = buildSourceSeriesOptions([flow], ['#165dff'], undefined, [flow.seriesId]);
  assert.equal(flowOnly.series[0].type, 'bar');
  assert.equal(flowOnly.yAxis[0].scale, false);
});


test('gold driver variables retain two panes and synchronized dates/zoom when series are hidden', () => {
  const {buildGoldDriversOptions} = load('src/views/hedgeBoard/charts/sourceSeriesOptions.ts');
  const ids=['gold_futures_close','us_treasury_30y_10y_spread','dxy','us_treasury_10y','us_10y_breakeven','us_10y_real_yield'];
  const series=ids.map((seriesId,i)=>({seriesId,label:seriesId,unit:i===0?'USD/oz':i===2?'index':'percent',observations:[{date:`2026-10-${10+i}`,value:String(i+1)}]}));
  const options=buildGoldDriversOptions(series,['blue','green','gold','purple','red','gray']);
  assert.equal(options.grid.length,2);
  assert.deepEqual(options.series.map(s=>s.xAxisIndex),[0,0,0,1,1,1]);
  assert.deepEqual(options.series.map(s=>s.yAxisIndex),[0,1,2,3,3,3]);
  assert.equal(options.yAxis[0].type,'log');
  assert.equal(options.yAxis[1].type,'value'); // negative spreads remain visible
  assert.deepEqual(options.dataZoom[0].xAxisIndex,[0,1]);
  assert.equal(options.xAxis[0].min,options.xAxis[1].min);
  assert.equal(options.xAxis[0].max,options.xAxis[1].max);
  const hidden=buildGoldDriversOptions([series[3]],['purple']);
  assert.equal(hidden.series[0].yAxisIndex,3);
  assert.equal(hidden.yAxis[2].show,false);
});
