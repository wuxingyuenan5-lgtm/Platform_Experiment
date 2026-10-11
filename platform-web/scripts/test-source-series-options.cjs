const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../src/views/hedgeBoard/charts/sourceSeriesOptions.ts'), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const output = { exports: {} };
vm.runInNewContext(`(function(exports){${compiled}\n})`, {})(output.exports);
const { buildSourceSeriesOptions, buildSourceCurveOptions, unitText } = output.exports;

test('mixed units keep independent axes, native dates, gaps and exact tooltip values', () => {
  const input = [
    { seriesId: 'price', label: 'Price', unit: 'USD', observations: [
      { date: '2026-01-01', value: '123.123456789' }, { date: '2026-01-02', value: null } ] },
    { seriesId: 'rate', label: 'Rate', unit: 'percent', observations: [{ date: '2026-01-02', value: 0 }] },
  ];
  const result = buildSourceSeriesOptions(input, ['blue', 'green']);
  assert.equal(result.yAxis.length, 2);
  assert.equal(result.series[0].yAxisIndex, 0);
  assert.equal(result.series[1].yAxisIndex, 1);
  assert.equal(result.series[0].connectNulls, false);
  assert.equal(result.series[0].data[1][1], null);
  assert.equal(result.series[1].data[0][1], 0);
  const tooltip = result.tooltip.formatter([{ seriesIndex: 0, data: result.series[0].data[0] }, { seriesIndex: 1, data: result.series[1].data[0] }]);
  assert.match(tooltip, /2026-01-01\nPrice\n123\.123456789 USD/);
  assert.match(tooltip, /2026-01-02\nRate\n0 %/);
  assert.equal(result.useUTC, true);
  assert.equal(result.dataZoom[0].filterMode, 'none');
});

test('one genuine observation remains a visible point', () => {
  const result = buildSourceSeriesOptions([{ seriesId: 'single', label: 'Snapshot', unit: 'BTC', observations: [{ date: '2026-01-01', value: 5 }] }], ['blue']);
  assert.equal(result.series[0].showSymbol, true);
  assert.equal(unitText('percent'), '%');
});

test('IV timestamps retain source precision and the value axis has no fixed clipping range', () => {
  const result = buildSourceSeriesOptions([{seriesId:'iv',label:'1M',unit:'percent',observations:[
    {date:'2026-10-09T08:00:00+00:00',value:19.1256789},
    {date:'2026-10-10T08:00:00+00:00',value:85.75},
  ]}], ['blue']);
  assert.equal(result.yAxis[0].min, undefined);
  assert.equal(result.yAxis[0].max, undefined);
  assert.match(result.tooltip.formatter({seriesIndex:0,data:result.series[0].data[0]}), /19\.1256789/);
  assert.match(result.tooltip.formatter({seriesIndex:0,data:result.series[0].data[0]}), /2026-10-09T08:00:00\+00:00/);
  assert.equal(result.series[0].data[1][1], 85.75);
});

test('contract curves preserve month spacing and full source precision', () => {
  const result = buildSourceCurveOptions([{ label: 'AU2610', latestValue: '25.1234567' }, { label: 'AU2702', latestValue: '26.3' }], 'blue', '%');
  const data = result.series[0].data;
  assert.equal(data[0].value[0], Date.UTC(2026, 9, 1));
  assert.equal(data[1].value[0], Date.UTC(2027, 1, 1));
  assert.match(result.tooltip.formatter({ data: data[0] }), /25\.1234567 %/);
});
