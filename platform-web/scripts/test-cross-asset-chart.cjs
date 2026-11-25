const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const vue = require('vue');
const { parse, compileScript } = require('@vue/compiler-sfc');

require.extensions['.ts'] = (mod, filename) =>
  mod._compile(
    ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText,
    filename,
  );
const root = path.resolve(__dirname, '../src/views/hedgeBoard/macro/crossAsset');
function setup() {
  const file = path.join(root, 'TrendChart.vue');
  const script = compileScript(parse(fs.readFileSync(file, 'utf8')).descriptor, {
    id: 'trend-chart-test',
  }).content;
  const code = ts.transpileModule(script, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  let options;
  const module = { exports: {} };
  new Function('require', 'module', 'exports', code)(
    (name) => {
      if (name === 'vue') return vue;
      if (name === '@vueuse/core') return { useWindowSize: () => ({ width: vue.ref(1280) }) };
      if (name === 'echarts/components') return {};
      if (name === '@/utils/lib/echarts') return { default: { use() {} } };
      if (name === '@/hooks/web/useECharts')
        return {
          useECharts: () => ({
            setOptions(value) {
              options = value;
            },
            getInstance: () => ({ getOption: () => ({ dataZoom: [{ start: 25, end: 55 }] }) }),
          }),
        };
      if (name.startsWith('./')) return require(path.join(root, name + '.ts'));
      throw Error(name);
    },
    module,
    module.exports,
  );
  const bars = Array.from({ length: 250 }, (_, i) => ({
    t: 1700000000 + i * 86400,
    o: 100 + i,
    h: 102 + i,
    l: 99 + i,
    c: 101 + i,
    v: 100,
  }));
  const props = vue.reactive({
    source: { symbol: 'SPY', frame: '1D', bars, lastBarComplete: true },
    frame: '1D',
    groups: ['zlma'],
    auxiliary: ['macd', 'rsi', 'volume', 'amount'],
    kalman: [],
    kalmanPaint: 'none',
    range: 120,
    levels: true,
    signalAt: undefined,
  });
  const scope = vue.effectScope();
  const state = scope.run(() => module.exports.default.setup(props, { expose() {} }));
  return { props, state, bars, scope, options: () => options };
}
const settle = async () => {
  await vue.nextTick();
  await vue.nextTick();
  await vue.nextTick();
};

test('charts preserve the manual window across indicator changes and locate historical signals', async () => {
  const s = setup();
  try {
    await settle();
    assert.equal(s.options().series.find((x) => x.type === 'candlestick').data.length, 250);
    s.state.host.value = { querySelector: () => true };
    s.props.groups.push('sma');
    await settle();
    assert.deepEqual([s.options().dataZoom[0].start, s.options().dataZoom[0].end], [25, 55]);
    s.props.signalAt = s.bars[40].t;
    await settle();
    assert.ok(s.options().dataZoom[0].end < 60, 'history target is inside a historical window');
    s.props.range = 0;
    s.props.signalAt = undefined;
    await settle();
    assert.deepEqual([s.options().dataZoom[0].start, s.options().dataZoom[0].end], [0, 100]);
    const grids = s.options().grid;
    assert.equal(s.options().yAxis[3].splitNumber, 2);
    assert.equal(s.options().yAxis[3].axisLabel.formatter(50_000_000), '5000万');
    for (let i = 1; i < grids.length; i++)
      assert.ok(grids[i].top >= grids[i - 1].top + grids[i - 1].height);
    assert.ok(grids.at(-1).top + grids.at(-1).height < s.state.chartHeight.value - 40);
  } finally {
    s.scope.stop();
  }
});

test('native unconfirmed candles are excluded while rolling preview is explicit, and short monthly indicators stay unavailable', async () => {
  const s = setup();
  try {
    s.props.source.lastBarComplete = false;
    await settle();
    assert.equal(s.options().series.find((x) => x.type === 'candlestick').data.length, 249);
    s.props.source.rolling = { asOf: '2024-01-01' };
    await settle();
    assert.equal(s.options().series.find((x) => x.type === 'candlestick').data.length, 250);
    assert.equal(s.options().series[0].data.at(-1).itemStyle.color, '#c18b28');
    s.props.source.bars = s.bars.slice(0, 50);
    s.props.frame = 'M';
    await settle();
    assert.equal(
      s.options().series.some((x) => x.name === 'RSI(14)' || x.name === 'MACD柱'),
      false,
    );
    assert.equal(s.options().graphic.length, 2);
    assert.equal(s.options().tooltip.renderMode, 'richText');
    assert.equal(s.options().series[0].markPoint.label.show, false);
    assert.equal(s.options().series[0].markPoint.symbolSize, 8);
  } finally {
    s.scope.stop();
  }
});

test('full-history signal windows cover the whole series and band/color/event switches preserve reference semantics', async () => {
  const s = setup();
  try {
    s.props.range = 0;
    s.props.signalAt = s.bars[20].t;
    s.props.groups.push('pma');
    s.props.kalman.push('price');
    await settle();
    assert.deepEqual([s.options().dataZoom[0].start, s.options().dataZoom[0].end], [0, 100]);
    assert.equal(s.options().series.filter((x) => x.name === 'Kalman Price Filter').length, 3);
    assert.equal(s.options().series.filter((x) => x.name.startsWith('__PMA')).length, 6);
    const base = s.options().series.find((x) => x.name === '__PMA144PMA169-base');
    const fill = s.options().series.find((x) => x.name === '__PMA144PMA169-fill');
    assert.ok(base.data.at(-1) > 100 && fill.data.at(-1) >= 0);
    assert.equal(s.options().legend.data.includes('Kalman Price Filter'), true);
    assert.equal(
      s.options().legend.data.some((x) => x.startsWith('__')),
      false,
    );
    s.props.levels = false;
    await settle();
    assert.equal(s.options().series[0].markArea, undefined);
    assert.equal(
      s.options().series[0].markPoint.data.every((p) => p.value === 'ZLMA交叉'),
      true,
    );
    s.props.groups = ['pma'];
    s.props.levels = true;
    await settle();
    assert.equal(s.options().series[0].markArea, undefined);
    assert.equal(s.options().series[0].markPoint, undefined);
    assert.deepEqual(s.options().axisPointer.link, [{ xAxisIndex: 'all' }]);
    const text = s.options().tooltip.formatter([
      {
        axisValue: new Date(s.bars[100].t * 1000).toISOString().slice(0, 10),
        seriesName: '成交量',
      },
    ]);
    assert.ok(text.includes('PMA144') && text.includes('RSI') && text.includes('MACD'));
  } finally {
    s.scope.stop();
  }
});

test('historical evidence uses only information available at the signal observation, including warmup', () => {
  const file = path.join(root, 'TrendEvidence.vue');
  const script = compileScript(parse(fs.readFileSync(file, 'utf8')).descriptor, {
    id: 'signal-evidence',
  }).content;
  const code = ts.transpileModule(script, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const mod = { exports: {} };
  new Function('require', 'module', 'exports', code)(
    (name) => (name === 'vue' ? vue : require(path.join(root, name + '.ts'))),
    mod,
    mod.exports,
  );
  const bars = Array.from({ length: 1800 }, (_, i) => ({
    t: 1600000000 + i * 86400,
    o: 100 + i * 0.1,
    h: 102 + i * 0.1,
    l: 99 + i * 0.1,
    c: 101 + i * 0.1,
    v: 100,
  }));
  const state = mod.exports.default.setup(
    { source: { bars, lastBarComplete: true }, groups: ['pma', 'sma'], signalAt: bars[80].t },
    { expose() {} },
  );
  const engine = require(path.join(root, 'engine.ts')),
    rules = require(path.join(root, 'rules.ts'));
  assert.equal(state.index.value, 80);
  assert.deepEqual(
    state.assessment.value,
    rules.classify(engine.compute(bars.slice(0, 81), true)).current,
  );
  assert.equal(state.assessment.value.systems.pma.ready, false);
  assert.equal(state.historyState('PMA676'), '历史不足');
});
