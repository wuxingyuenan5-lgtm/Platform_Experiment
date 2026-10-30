const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const vue = require('vue');
const createLoader = require('./load-strategy-module.cjs');

function setup(file, props, names, modules = {}) {
  const source = fs.readFileSync(path.resolve(__dirname, '../src/views/hedgeBoard/aShare/components', file), 'utf8');
  const script = source.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1];
  const hooks = {};
  const scope = vue.effectScope();
  const exports = {};
  const code = ts.transpileModule(`${script}\nexports.state = { ${names} };`, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const load = createLoader();
  scope.run(() => vm.runInNewContext(code, {
    exports, defineProps: () => props, defineEmits: () => () => {},
    require: (name) => {
      if (name in modules) return modules[name];
      if (name === 'vue') return {
        ...vue, getCurrentInstance: () => ({ uid: 1 }),
        onMounted: (fn) => { hooks.mount = fn; }, onBeforeUnmount() {},
      };
      if (name === '@vueuse/core') return {
        useWindowSize: () => ({ height: vue.ref(900) }),
        useElementSize: () => ({ width: vue.ref(600) }),
      };
      if (name.includes('researchWorkspace')) return { useResearchViewState: (_, initial) => vue.ref(initial) };
      if (name === './overviewSegments') return load('src/views/hedgeBoard/aShare/components/overviewSegments.ts');
      if (name === './etfTrackingModel') return load('src/views/hedgeBoard/aShare/components/etfTrackingModel.ts');
      return {};
    },
  }));
  return { ...exports.state, hooks, close: () => scope.stop() };
}

test('crosshair reuses plot geometry; window, legend and data still update with gaps intact', async () => {
  const props = vue.reactive({
    title: 'Test', dates: ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04'],
    series: [
      { name: 'flow', type: 'line', color: 'blue', values: [1, null, 3, 4] },
      { name: 'price', type: 'line', axis: 'hidden-price', color: 'red', values: [10, 20, 30, 40] },
    ],
  });
  const s = setup('VibeTimeChart.vue', props, 'geometry, hover, startIndex, toggle');
  try {
    const initial = s.geometry.value;
    assert.equal(initial[0].segments.length, 2);
    assert.ok(initial[0].segments[0].isolated);
    assert.equal(initial[0].segments[1].isolated, null);
    assert.ok(!initial[1].segments[0].points.includes('NaN'));
    for (let i = 0; i < 100; i++) {
      s.hover.value = i % 4;
      assert.equal(s.geometry.value, initial);
    }
    s.startIndex.value = 2;
    assert.notEqual(s.geometry.value, initial);
    assert.equal(s.geometry.value[0].segments.length, 1);
    s.toggle(1);
    assert.equal(s.geometry.value.length, 1);
    const beforeData = s.geometry.value;
    props.series[0].values[3] = 7;
    await vue.nextTick();
    assert.notEqual(s.geometry.value, beforeData);
  } finally { s.close(); }
});

test('ETF window movement dispatches zoom without rebuilding historical series', async () => {
  let sets = 0;
  const actions = [];
  const props = vue.reactive({
    detail: {
      series: [{ date: '2026-01-01', etf_qfq_close: 1 }, { date: '2026-01-02', etf_qfq_close: 2 }],
      group: [], margin: [], groupMargin: [], disclosures: [],
    },
    start: '2026-01-01', end: '2026-01-02', tooltip: true,
  });
  const instance = { dispatchAction: (...args) => actions.push(args), on() {} };
  const s = setup('EtfLinkedCharts.vue', props, 'render', {
    '@/hooks/web/useECharts': { useECharts: () => ({
      getInstance: () => instance, setOptions: async () => { sets++; },
    }) },
  });
  try {
    await s.render();
    assert.equal(sets, 1);
    props.start = '2026-01-02';
    await vue.nextTick();
    assert.equal(sets, 1);
    assert.equal(actions.at(-1)[0].type, 'dataZoom');
    assert.equal(actions.at(-1)[0].startValue, props.start);
    assert.equal(actions.at(-1)[1].silent, true);
    props.detail = { ...props.detail, series: [...props.detail.series] };
    await vue.nextTick();
    assert.equal(sets, 2);
  } finally { s.close(); }
});

test('ETF main and collapsible flow plots retain their own data and financing axes', async () => {
  for (const flowsOnly of [false, true]) {
    let option;
    const props = vue.reactive({
      flowsOnly, start: '2026-01-01', end: '2026-01-02', tooltip: true,
      detail: {
        series: [
          {date:'2026-01-01',etf_qfq_close:1,qfq_delta_units_yi:-2,flow_to_index_pct:-0.5},
          {date:'2026-01-02',etf_qfq_close:2,qfq_delta_units_yi:0,flow_to_index_pct:0},
        ],
        group: [], disclosures: [],
        margin: [{date:'2026-01-01',financing_balance_yi:11,financing_net_buy_yi:-1}],
        groupMargin: [{date:'2026-01-01',index_financing_balance_yi:33,index_financing_net_buy_yi:3}],
      },
    });
    const s = setup('EtfLinkedCharts.vue', props, 'render', {
      '@/hooks/web/useECharts': {useECharts:()=>({getInstance:()=>null,setOptions:async o=>{option=o;}})},
    });
    try {
      await s.render();
      assert.equal(option.grid.length,flowsOnly?2:5);
      assert.equal(option.series.some(s=>s.id==='index_close'||s.name==='本组 ETF 总份额'),false);
      if (flowsOnly) {
        assert.equal(option.series.length,2);
        assert.equal(option.series[0].data[0],-2);
        assert.equal(option.series[0].data[1],0);
        assert.equal(option.series[1].data[0],-0.5);
      } else {
        const balance=option.series.find(s=>s.id==='financing_balance_yi');
        assert.equal(balance.xAxisIndex,3);
        assert.equal(balance.data[0],11);
        assert.equal(balance.data[1],null);
        assert.equal(option.series.find(s=>s.id==='index_financing_balance_yi').data[0],33);
        assert.equal(option.series.find(s=>s.name==='ETF 融资净买入').xAxisIndex,3);
        assert.equal(option.series.find(s=>s.name==='成分股融资净买入').xAxisIndex,4);
        assert.equal(option.series.some(s=>s.id==='qfq_delta_units_yi'),false);
      }
    } finally {s.close();}
  }
});
