const assert = require('node:assert/strict');
const test = require('node:test');
const load = require('./load-strategy-module.cjs')({});
const { themeChartData } = load('src/views/hedgeBoard/aShare/components/themeEtfAnalysis.ts');
test('indexed shares use the first visible valid observation and preserve gaps', () => {
  const funds = [{ name: '主题', series: [
    { date: '2025-01-01', units: '5' },
    { date: '2026-10-01', units: '10' },
    { date: '2026-10-02', units: null },
    { date: '2026-10-03', units: '12' },
  ] }];
  assert.deepEqual(themeChartData(funds, 90, true).rows.map(r => r.theme0), [100, null, 120]);
  assert.deepEqual(themeChartData(funds, 90, false).rows.map(r => r.theme0), [10, null, 12]);
});

test('theme identities remain stable for shared chart zoom and values preserve explicit missing observations', () => {
  const a = {code:'a', name:'A', series:[{date:'2026-10-01',units:'10'},{date:'2026-10-02',units:null}]};
  const b = {code:'b', name:'B', series:[{date:'2026-10-01',units:'5'},{date:'2026-10-02',units:'6'}]};
  const chart = themeChartData([a,b],1095,false);
  assert.deepEqual(chart.rows.map(r => r.themea),[10,null]);
  assert.deepEqual(chart.rows.map(r => r.themeb),[5,6]);
  assert.equal(chart.lines[0].key,themeChartData([b,a],1095,false).lines[1].key);
  assert.equal(chart.lines[0].unit,'亿份');
  assert.deepEqual(themeChartData([b],1095,true).rows.map(r => r.themeb),[100,120]);
});
