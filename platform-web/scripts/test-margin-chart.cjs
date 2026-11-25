const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'),
  path = require('node:path'),
  ts = require('typescript'),
  vue = require('vue');
const { parse, compileScript } = require('@vue/compiler-sfc');
const valuationStats = require('./load-strategy-module.cjs')()('src/views/hedgeBoard/components/indexValuationStats.ts');
test('financing chart keeps legacy two-axis mapping and separates the added percentage axis', async () => {
  const file = path.resolve(
    __dirname,
    '../src/views/hedgeBoard/aShare/components/FinancingChart.vue',
  );
  const script = compileScript(parse(fs.readFileSync(file, 'utf8')).descriptor, {
    id: 'margin-chart-test',
  }).content;
  const code = ts.transpileModule(script, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  let option;
  const mod = { exports: {} };
  const mock = {
    vue,
    '../../components/ChartExpand.vue': {},
    '../../components/indexValuationStats': valuationStats,
    '@/hooks/web/useECharts': {
      useECharts: () => ({
        getInstance: () => ({ getOption: () => option || {} }),
        setOptions: (next) => {
          option = next;
        },
      }),
    },
  };
  new Function('require', 'module', 'exports', code)(
    (name) => mock[name] || require(name),
    mod,
    mod.exports,
  );
  const props = vue.reactive({
    title: '两融余额变化',
    rows: [
      { date: '2026-11-05', total: '100', balance: '95', short: '5', change: '2', share: '7.75' },
    ],
    lines: [
      { key: 'total', name: '两融总余额', unit: '亿元', color: 'black', defaultSelected: false },
      { key: 'balance', name: '融资余额', unit: '亿元', color: 'blue' },
      { key: 'short', name: '融券余额', unit: '亿元', color: 'gold', defaultSelected: false },
      {
        key: 'change',
        name: '融资余额日变化',
        unit: '亿元',
        color: 'green',
        right: true,
        bar: true,
      },
      { key: 'share', name: '融资融券成交额占比', unit: '%', color: 'purple', axis: 2 },
    ],
    initialRange: 0,
  });
  const scope = vue.effectScope();
  try {
    const state = scope.run(() => mod.exports.default.setup(props, { expose() {} }));
    state.element.value = {};
    await vue.nextTick();
    await vue.nextTick();
    assert.deepEqual(
      option.series.map((s) => s.yAxisIndex),
      [0, 0, 0, 1, 2],
    );
    assert.deepEqual(
      option.yAxis.map((a) => a.name),
      ['亿元', '亿元', '%'],
    );
    assert.equal(option.yAxis[2].offset, 65);
    assert.equal(option.legend.selected['两融总余额'], false);
    assert.equal(option.legend.selected['融券余额'], false);
    assert.equal(option.legend.selected['融资余额'], true);
    assert.equal(option.legend.selected['融资融券成交额占比'], true);
    assert.deepEqual(option.series.at(-1).data, [7.75]);
    props.lines = [
      ...props.lines,
      {
        key: 'index',
        name: '沪深300',
        color: '#d97706',
        unit: '点',
        axis: 3,
        hideAxis: true,
        lineType: 'dashed',
      },
    ];
    props.rows = [
      { date: '2026-11-04', index: '4000' },
      { date: '2026-11-05', index: '4100' },
    ];
    await vue.nextTick();
    await vue.nextTick();
    assert.equal(option.yAxis[3].show, false);
    assert.equal(option.yAxis[3].scale, true);
    assert.equal(option.yAxis[3].min, 'dataMin');
    assert.equal(option.yAxis[3].max, 'dataMax');
    assert.equal(option.grid.right, 140);
    assert.deepEqual(option.series.at(-1).data, [4000, 4100]);
    assert.equal(option.series.at(-1).yAxisIndex, 3);
    assert.equal(option.series.at(-1).lineStyle.type, 'dashed');
    props.lines = props.lines.slice(0, 4);
    await vue.nextTick();
    await vue.nextTick();
    assert.equal(option.yAxis.length, 2);
    assert.deepEqual(
      option.series.map((s) => s.yAxisIndex),
      [0, 0, 0, 1],
    );
  } finally {
    scope.stop();
  }
});
