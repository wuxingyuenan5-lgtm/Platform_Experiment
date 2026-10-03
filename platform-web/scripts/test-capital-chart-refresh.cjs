const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const ts = require('typescript');
const vue = require('vue');
const { parse, compileScript } = require('vue/compiler-sfc');

// Node 24 exposes navigator although this test uses ECharts' server renderer.
delete global.navigator;
const echarts = require('echarts');

test('capital chart preserves zoom on refresh and resets it on deliberate selection', async () => {
  const filename = path.resolve(
    __dirname,
    '../src/views/strategy/management/components/StrategyCapitalNetValueBoard.vue',
  );
  const { descriptor } = parse(fs.readFileSync(filename, 'utf8'), { filename });
  const source = compileScript(descriptor, { id: 'capital-chart-test' }).content;
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 900, height: 400 });
  const scope = vue.effectScope();
  const module = { exports: {} };
  const mocks = {
    vue: { ...vue, onMounted() {} },
    '@/hooks/web/useECharts': {
      useECharts: () => ({
        getInstance: () => chart,
        resize() {},
        setOptions: async (options, clear = true) => {
          if (clear) chart.clear();
          chart.setOption({ ...options, animation: false });
        },
      }),
    },
  };
  new Function('require', 'module', 'exports', code)(
    (name) => mocks[name] || require(name),
    module,
    module.exports,
  );
  const props = vue.reactive({
    curve: {
      defaultMetric: 'nav',
      defaultPeriod: 'all',
      title: 'Net value',
      summaries: [],
      metricOptions: [{ key: 'nav', label: 'NAV' }],
      periodOptions: [{ key: 'all', label: 'All' }],
      xLabels: Array.from({ length: 100 }, (_, i) => String(i)),
      netValueData: Array.from({ length: 100 }, (_, i) => 1 + i / 100),
      drawdownData: Array(100).fill(0),
    },
  });
  try {
    const component = scope.run(() => module.exports.default.setup(props, { expose() {} }));
    await component.renderChart();
    chart.dispatchAction({ type: 'dataZoom', start: 10, end: 30 });
    props.curve.netValueData = props.curve.netValueData.map((value) => value + 0.01);
    await vue.nextTick();
    assert.equal(chart.getOption().dataZoom[0].start, 10);
    assert.equal(chart.getOption().dataZoom[0].end, 30);
    assert.equal(chart.getOption().series[0].data[0], 1.01);
    component.modeKey.value = 'fixed';
    await vue.nextTick();
    assert.equal(chart.getOption().dataZoom[0].start, 60);
    assert.equal(chart.getOption().dataZoom[0].end, 100);
  } finally {
    scope.stop();
    chart.dispose();
  }
});
