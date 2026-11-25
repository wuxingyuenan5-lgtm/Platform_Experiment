const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const vue = require('vue');
const createLoader = require('./load-strategy-module.cjs');

test('fixed net axis preserves actual extremes, marks overflow and leaves turnover independent', async () => {
  let option;
  const props = vue.reactive({
    title: '双创购买比例',
    initialRange: 0,
    bounds: [-100, 100],
    markOverflow: true,
    rows: [
      { date: '2023-12-15', net: '-7395.3252', turnover: '29.5962' },
      { date: '2023-12-18', net: '100', turnover: '31' },
      { date: '2026-02-25', net: '3109.8085', turnover: '13.2798' },
      { date: '2026-02-26', net: null, turnover: null },
    ],
    lines: [
      { key: 'net', name: '双创申购比例', unit: '%', color: 'blue', defaultSelected: false },
      { key: 'turnover', name: '双创成交额比例', unit: '%', color: 'orange', right: true },
    ],
  });
  const state = setup('FinancingChart.vue', props, 'element', {
    '@/hooks/web/useECharts': {
      useECharts: () => ({
        getInstance: () => option ? { getOption: () => ({ legend: [option.legend] }) } : null,
        setOptions: (value) => {
          option = value;
        },
      }),
    },
  });
  try {
    state.element.value = {};
    await vue.nextTick();
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(option.yAxis[0].min, -100);
    assert.equal(option.legend.selected['双创申购比例'], false);
    assert.equal(option.legend.selected['双创成交额比例'], true);
    assert.equal(option.yAxis[0].max, 100);
    assert.equal(option.yAxis[1].min, undefined);
    assert.equal(option.yAxis[1].max, undefined);
    assert.deepEqual([...option.series[0].data], [-7395.3252, 100, 3109.8085, null]);
    const marks = option.series[0].markPoint.data;
    assert.equal(marks.length, 2);
    assert.deepEqual([...marks[0].coord], ['2023-12-15', -100]);
    assert.deepEqual([...marks[1].coord], ['2026-02-25', 100]);
    assert.equal(marks[0].value, -7395.3252);
    assert.equal(marks[1].value, 3109.8085);
    assert.equal(option.series[1].markPoint, undefined);
    assert.match(option.series[0].markPoint.tooltip.formatter({ data: marks[0] }), /-7,395.3252/);
    assert.match(
      option.tooltip.formatter([{ dataIndex: 2, seriesIndex: 0, marker: '' }]),
      /3,109.8085/,
    );
    option.legend.selected['双创申购比例'] = true;
    props.markOverflow = false;
    await vue.nextTick();
    await vue.nextTick();
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(option.series[0].markPoint, undefined);
    assert.equal(option.legend.selected['双创申购比例'], true);
  } finally {
    state.close();
  }
});

function setup(file, props, names, modules = {}) {
  const source = fs.readFileSync(
    path.resolve(__dirname, '../src/views/hedgeBoard/aShare/components', file),
    'utf8',
  );
  const script = source.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1];
  const hooks = {};
  const scope = vue.effectScope();
  const exports = {};
  const code = ts.transpileModule(`${script}\nexports.state = { ${names} };`, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const load = createLoader();
  scope.run(() =>
    vm.runInNewContext(code, {
      exports,
      defineProps: () => props,
      defineEmits: () => () => {},
      require: (name) => {
        if (name in modules) return modules[name];
        if (name === '@/hooks/web/chartMotion') return {
          useChartReveal: () => Object.assign(async () => {}, { cancel() {} }),
        };
        if (name === 'vue')
          return {
            ...vue,
            getCurrentInstance: () => ({ uid: 1 }),
            onMounted: (fn) => {
              hooks.mount = fn;
            },
            onBeforeUnmount() {},
          };
        if (name === '@vueuse/core')
          return {
            useWindowSize: () => ({ height: vue.ref(900) }),
            useElementSize: () => ({ width: vue.ref(600) }),
          };
        if (name.includes('researchWorkspace'))
          return { useResearchViewState: (_, initial) => vue.ref(initial) };
        if (name === '../../components/indexValuationStats')
          return load('src/views/hedgeBoard/components/indexValuationStats.ts');
        if (name === './overviewSegments')
          return load('src/views/hedgeBoard/aShare/components/overviewSegments.ts');
        if (name === './etfTrackingModel')
          return load('src/views/hedgeBoard/aShare/components/etfTrackingModel.ts');
        return {};
      },
    }),
  );
  return { ...exports.state, hooks, close: () => scope.stop() };
}

test('A-share research charts share calendar-year history and keep all available data when requested', () => {
  const dates = ['2014-02-27', '2014-02-28', '2021-02-27', '2021-02-28', '2024-02-29'];
  const modules = { vue: {
    ...vue,
    inject: (key, fallback) => key === 'aShareThemeResearchCalendarRanges' ? true : fallback,
    getCurrentInstance: () => ({ uid: 1 }),
    onBeforeUnmount() {},
  } };
  const line = { name: 'Test', type: 'line', color: 'blue' };
  const finance = setup('FinancingChart.vue', {
    title: 'Test', rows: dates.map((date) => ({ date, value: 1 })), lines: [],
  }, 'filtered, range, selectRange', {
    ...modules, '@/hooks/web/useECharts': { useECharts: () => ({}) },
  });
  const vibe = setup('VibeTimeChart.vue', {
    title: 'Test', dates, series: [{ ...line, values: dates.map(() => 1) }], initialWindow: 2,
  }, 'shownDates, preset, setPreset', modules);
  try {
    assert.equal(finance.range.value, 10);
    assert.equal(vibe.preset.value, 10);
    assert.deepEqual(finance.filtered.value.map((r) => r.date), dates.slice(1));
    assert.deepEqual([...vibe.shownDates.value], dates.slice(1));
    finance.selectRange(3); vibe.setPreset(3);
    assert.deepEqual(finance.filtered.value.map((r) => r.date), dates.slice(3));
    assert.deepEqual([...vibe.shownDates.value], dates.slice(3));
    finance.selectRange(0); vibe.setPreset(0);
    assert.deepEqual(finance.filtered.value.map((r) => r.date), dates);
    assert.deepEqual([...vibe.shownDates.value], dates);
  } finally {
    finance.close();
    vibe.close();
  }
});

test('crosshair reuses plot geometry; window, legend and data still update with gaps intact', async () => {
  const props = vue.reactive({
    title: 'Test',
    dates: ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04'],
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
  } finally {
    s.close();
  }
});

test('ETF window movement dispatches zoom without rebuilding historical series', async () => {
  let sets = 0;
  const actions = [];
  const props = vue.reactive({
    detail: {
      series: [
        { date: '2026-01-01', etf_qfq_close: 1 },
        { date: '2026-01-02', etf_qfq_close: 2 },
      ],
      group: [],
      margin: [],
      groupMargin: [],
      disclosures: [],
    },
    start: '2026-01-01',
    end: '2026-01-02',
    tooltip: true,
  });
  const instance = { dispatchAction: (...args) => actions.push(args), on() {} };
  const s = setup('EtfLinkedCharts.vue', props, 'render', {
    '@/hooks/web/useECharts': {
      useECharts: () => ({
        getInstance: () => instance,
        setOptions: async () => {
          sets++;
        },
      }),
    },
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
  } finally {
    s.close();
  }
});

test('ETF unified plots put shares on the price right axis and link all four plots to the common slider', async () => {
  let option;
  const props = vue.reactive({
    start: '2026-01-01',
    end: '2026-01-02',
    tooltip: true,
    detail: {
      series: [
        {
          date: '2026-01-01',
          etf_qfq_close: 1,
          qfq_total_units_yi: 22,
          etf_qfq_turnover_est_yi: 4,
        },
        {
          date: '2026-01-02',
          etf_qfq_close: 2,
          qfq_total_units_yi: 23,
          etf_qfq_turnover_est_yi: 5,
        },
      ],
      group: [],
      disclosures: [{ report_date: '2026-01-01', total_shares_yi_qfq: 22, combined_ratio_pct: 10 }],
      margin: [{ date: '2026-01-01', financing_balance_yi: 11, financing_net_buy_yi: -1 }],
      groupMargin: [
        { date: '2026-01-01', index_financing_balance_yi: 33, index_financing_net_buy_yi: 3 },
      ],
    },
  });
  const state = setup('EtfLinkedCharts.vue', props, 'render', {
    '@/hooks/web/useECharts': {
      useECharts: () => ({
        getInstance: () => null,
        setOptions: async (value) => (option = value),
      }),
    },
  });
  try {
    await state.render();
    assert.equal(option.grid.length, 4);
    const price = option.series.find((s) => s.id === 'etf_qfq_close');
    const shares = option.series.find((s) => s.id === 'qfq_total_units_yi');
    assert.equal(price.xAxisIndex, 0);
    assert.equal(shares.xAxisIndex, 0);
    assert.notEqual(price.yAxisIndex, shares.yAxisIndex);
    assert.equal(option.yAxis[shares.yAxisIndex].position, 'right');
    assert.deepEqual(shares.data, [22, 23]);
    assert.equal(option.series.find((s) => s.id === 'disclosures').yAxisIndex, shares.yAxisIndex);
    assert.equal(option.series.find((s) => s.id === 'financing_balance_yi').xAxisIndex, 1);
    assert.deepEqual(option.series.find((s) => s.id === 'financing_balance_yi').data, [11, null]);
    assert.equal(option.series.find((s) => s.name === '成分股融资净买入').xAxisIndex, 2);
    assert.equal(option.series.find((s) => s.id === 'etf_qfq_turnover_est_yi').xAxisIndex, 3);
    assert.equal(
      option.series.some((s) => s.id === 'qfq_delta_units_yi'),
      false,
    );
    assert.deepEqual(
      [...option.dataZoom.find((z) => z.type === 'slider').xAxisIndex],
      [0, 1, 2, 3],
    );
    props.mode = 'price';
    await state.render();
    assert.equal(option.grid.length, 2);
    assert.equal(option.series.find((s) => s.id === 'etf_qfq_turnover_est_yi').xAxisIndex, 1);
    props.mode = 'flows';
    props.detail.series[1].flow_yi = -2;
    await state.render();
    assert.deepEqual(option.series.find((s) => s.id === 'flow_yi').data, [null, -2]);
    props.mode = 'financing';
    await state.render();
    assert.equal(option.grid.length, 3);
    assert.equal(option.series.find((s) => s.name === '成分股融资净买入').xAxisIndex, 2);
  } finally {
    state.close();
  }
});
