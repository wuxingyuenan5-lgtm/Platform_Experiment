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
  assert.ok(option.series.every(s => s.emphasis.disabled === true && s.emphasis.focus === 'none'));
  assert.equal(option.tooltip.trigger, 'axis');
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

test('regional stacks overlay shared native daily XAUUSD on its own price axis', () => {
  const price = {seriesId:'xauusd_daily_close',label:'XAUUSD',unit:'USD/oz', observations:[{date:'2026-10-08',value:'4165.6500'},{date:'2026-10-09',value:null}]};
  const regions = [row('north_america',[['2026-10-09','10']]),row('europe',[['2026-10-09','-3']])];
  const options=buildRegionalStackOptions([...regions,price]);
  assert.deepEqual(options.series.map(s=>s.type),['bar','bar','line']);
  assert.deepEqual(options.series.map(s=>s.yAxisIndex),[0,0,1]);
  assert.deepEqual(options.yAxis.map(a=>a.scale),[false,true]);
  assert.deepEqual(options.yAxis.map(a=>a.name),['USD','USD/oz']);
  assert.equal(options.series[2].stack,undefined);
  assert.deepEqual(options.series[2].data,[[Date.parse('2026-10-08'),4165.65],[Date.parse('2026-10-09'),null]]);
  assert.match(options.tooltip.formatter([{seriesIndex:2,data:options.series[2].data[0]}]),/4165\.6500 USD\/oz/);
  assert.equal(buildRegionalStackOptions([price]).series[0].type,'line');
  assert.ok(buildRegionalStackOptions(regions).series.every(s=>s.type==='bar'));
});


test('mixed flow charts keep bars on zero-based flow axis and a separate price line through legend filtering', () => {
  const flow = { seriesId: 'spdr_holdings_change', label: 'Flow', unit: 'tonnes', frequency: 'daily', observations: [{date:'2026-10-09',value:'-2.123456789'}, {date:'2026-10-10',value:null}] };
  const price = { seriesId: 'xauusd_daily_close', label: 'Price', unit: 'USD/oz', observations: [{date:'2026-10-09',value:'4000.50'}] };
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
  const ids=['xauusd_daily_close','us_treasury_30y_10y_spread','dxy','us_treasury_10y','us_10y_breakeven','us_10y_real_yield'];
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


test('visible time windows filter all price/OI/funding axes; monetary flows preserve sign colors', () => {
  const {buildBinanceOptions, buildGoldDriversOptions}=load('src/views/hedgeBoard/charts/sourceSeriesOptions.ts');
  const series=['binance_btc_spot','binance_btc_open_interest','binance_btc_funding'].map((seriesId,i)=>({seriesId,label:seriesId,unit:i===2?'percent':'USD',observations:[{date:'2026-01-01',value:'1'},{date:'2026-10-01',value:'100'}]}));
  const option=buildBinanceOptions(series,['blue','green','red']);
  assert.equal(option.grid.length,3);
  assert.ok(option.xAxis.every(axis=>axis.min===Date.parse('2026-01-01') && axis.max===Date.parse('2026-10-01')));
  assert.deepEqual(option.series.map(s=>s.xAxisIndex),[0,1,2]);
  assert.deepEqual(option.series.map(s=>s.type),['line','line','bar']);
  assert.ok(option.dataZoom.every(z=>z.filterMode==='filter' && z.xAxisIndex.length===3));
  assert.equal(option.series[0].lineStyle.color,'#111111');
  assert.equal(option.series[2].itemStyle.color({value:[0,-1]}),'#f23645');
  const flow=buildSourceSeriesOptions([{...series[0],seriesId:'spdr_holdings_change'}],['blue'],undefined,['spdr_holdings_change']);
  assert.equal(flow.series[0].itemStyle.color({value:[0,1]}),'#f97980');
  assert.equal(flow.series[0].itemStyle.color({value:[0,-1]}),'#53b987');
  const gold=buildGoldDriversOptions([{...series[0],seriesId:'xauusd_daily_close',unit:'USD/oz'}],['blue']);
  assert.equal(gold.yAxis[0].min({min:2000,max:2100}),1940);
  assert.equal(gold.yAxis[0].max({min:2000,max:2100}),2163);
});


test('stablecoin stacks align dates instead of stacking different inception dates by array position', () => {
 const {buildStablecoinOptions}=load('src/views/hedgeBoard/charts/sourceSeriesOptions.ts');
 const option=buildStablecoinOptions([row('a',[['2025-01-01','100'],['2025-01-02','110']]),row('b',[['2025-01-02','5']])],['blue','green']);
 assert.deepEqual(option.series[1].data,[[Date.parse('2025-01-01'),null],[Date.parse('2025-01-02'),5]]);
 assert.ok(option.series.every(s=>s.stack==='market-cap'));
});
