const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const ts = require('typescript');
const vue = require('vue');
const { parse, compileScript } = require('vue/compiler-sfc');

function mountPanel(points, options = {}) {
  const filename = path.resolve(
    __dirname,
    '../src/views/hedgeBoard/components/CumulativeVolatilityPanel.vue',
  );
  const { descriptor } = parse(fs.readFileSync(filename, 'utf8'), { filename });
  const source = compileScript(descriptor, { id: 'volatility-window-test' }).content;
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const calls = [];
  const cleanups = [];
  const mocks = {
    vue: {
      ...vue,
      onMounted() {},
      onBeforeUnmount(fn) {
        cleanups.push(fn);
      },
    },
    '@/api/hedgeResearch': {
      async getCumulativeVolatility(asset, days, interval, window) {
        calls.push({ asset, days, interval, window });
        if (!window && options.failFull) { options.failFull=false; throw new Error('test full transport failure'); }
        if (!window && options.deferFull) await new Promise(resolve => { options.resolveFull = resolve; });
        if (window && options.failWindow) { options.failWindow = false; throw new Error('test transport failure'); }
        const selected = points.filter(
          (p) => !window || (p.timestamp >= window.start && p.timestamp <= window.end),
        );
        const bases = {};
        return {
          data: {
            interval,
            points: selected.map((p) => {
              bases[p.session] ??= Number(p.value);
              return { ...p, value: String(Number(p.value) - bases[p.session]) };
            }),
          },
        };
      },
    },
    '../charts/chartRange': { renderChartRangeSelector() {} },
  };
  const module = { exports: {} };
  new Function('require', 'module', 'exports', code)(
    (name) => mocks[name] || require(name),
    module,
    module.exports,
  );
  const scope = vue.effectScope();
  const panel = scope.run(() =>
    module.exports.default.setup({ asset: options.asset ?? 'btc', title: 'BTC' }, { expose() {} }),
  );
  return {
    panel,
    calls,
    close() {
      cleanups.forEach((fn) => fn());
      scope.stop();
    },
  };
}

const points = Array.from({ length: 60 }, (_, day) =>
  ['asia', 'europe', 'americas'].flatMap((session, index) =>
    Array.from({ length: 2 }, (_, sample) => {
      const date = new Date(Date.UTC(2026, 7, 1 + day, index * 8, sample * 15));
      return {
        timestamp: date.toISOString().replace('.000Z', 'Z'),
        session,
        sessionDate: date.toISOString().slice(0, 10),
        value: String(day * 2 + sample + index * 100),
        price: '100',
      };
    }),
  ),
).flat();
const settle = async () => {
  await vue.nextTick();
  await new Promise((resolve) => setTimeout(resolve, 230));
};

test('presets, slider and custom window request backend rebasing and retain full timeline', async () => {
  const { panel, calls, close } = mountPanel(points);
  try {
    await panel.load();
    await settle();
    assert.equal(panel.allDates.value.length, points.length);
    for (const days of [7, 30]) {
      panel.selectPresetRange(days);
      await settle();
      assert.ok(calls.at(-1).window.start > points[0].timestamp);
      for (const session of ['asia', 'europe', 'americas']) {
        assert.equal(panel.points.value.find((p) => p.session === session).value, '0');
      }
      assert.equal(panel.allDates.value.length, points.length);
    }
    panel.onRangeStartChange(90);
    panel.onRangeEndChange(200);
    await settle();
    assert.deepEqual(calls.at(-1).window, {
      start: points[90].timestamp,
      end: points[200].timestamp,
    });
    assert.equal(panel.customRangeApplied.value, true);
    panel.customStartDate.value = '2026-08-15';
    panel.customEndDate.value = '2026-08-20';
    panel.applyCustomRange();
    await settle();
    assert.equal(calls.at(-1).window.start.slice(0, 10), '2026-08-15');
    assert.equal(calls.at(-1).window.end.slice(0, 10), '2026-08-20');
  } finally {
    close();
  }
});

test('hover reads aligned session slots and remains bounded for a year of samples', async () => {
  const yearPoints = Array.from({ length: 365 * 96 }, (_, i) => {
    const date = new Date(Date.UTC(2025, 9, 1, 0, i * 15));
    const hour = date.getUTCHours();
    const session = hour < 7 || hour >= 23 ? 'asia' : hour < 15 ? 'europe' : 'americas';
    return { timestamp: date.toISOString().replace('.000Z', 'Z'), session,
      sessionDate: new Date(date.getTime() + (date.getUTCHours() >= 23 ? 86400000 : 0)).toISOString().slice(0, 10), value: String(i), price: '100' };
  });
  const { panel, close } = mountPanel(yearPoints);
  try {
    await panel.load();
    await settle();
    const event = {
      clientX: 76,
      currentTarget: { getBoundingClientRect: () => ({ left: 0, width: 1200 }) },
    };
    panel.onMove(event);
    assert.equal(panel.hoverIndex.value, 0);
    assert.equal(panel.valueAt({key:'asia'}, 0), '—'); // archive starts after this day's Asian session began
    assert.equal(panel.valueAt({key:'asia'}, 4), '+0.00%');
    for (const key of ['europe','americas']) assert.equal(panel.valueAt({key}, 0), '+0.00%');
    assert.equal(panel.hoverPrice.value, 100);
    panel.togglePrice();
    assert.equal(panel.priceVisible.value, false);
    const started = performance.now();
    for (let i = 0; i < 1000; i++) panel.onMove({ ...event, clientX: 76 + i });
    assert.ok(performance.now() - started < 250, 'hover must not rescan points for every sample');
  } finally {
    close();
  }
});


for (const asset of ['gold','btc']) test(`${asset}: range changes during precision load cannot cancel the full response; errors recover without reload`, async () => {
  const options = {asset};
  const {panel,calls,close} = mountPanel(points,options);
  try {
    await panel.load(); await settle();
    options.deferFull=true;
    panel.precision.value='1h';
    await vue.nextTick();
    panel.selectPresetRange(7);
    await vue.nextTick();
    options.deferFull=false; options.resolveFull();
    await settle();
    assert.equal(panel.status.value,'ready');
    assert.equal(panel.loadingFull.value,false);
    assert.equal(calls.at(-1).interval,'1h');
    assert.ok(panel.plottedSeries.value.some(s=>s.path));
    options.failWindow=true;
    panel.selectPresetRange(30); await settle();
    assert.equal(panel.status.value,'error');
    panel.selectPresetRange(7); await settle();
    assert.equal(panel.status.value,'ready');
  } finally {close();}
});

test('calendar gaps and missing sample slots stay empty instead of being compressed or connected', async () => {
  const points = [
    {timestamp:'2025-10-16T07:14:00Z',session:'europe',sessionDate:'2025-10-16',value:'0',price:'100'},
    {timestamp:'2026-08-25T07:14:00Z',session:'europe',sessionDate:'2026-08-25',value:'1',price:'101'},
    {timestamp:'2026-08-25T07:44:00Z',session:'europe',sessionDate:'2026-08-25',value:'2',price:'102'},
    {timestamp:'2026-08-26T07:14:00Z',session:'europe',sessionDate:'2026-08-26',value:'3',price:'103'},
  ];
  const {panel,close} = mountPanel(points);
  try {
    await panel.load(); await settle();
    const step=panel.xForDate('2026-08-26')-panel.xForDate('2026-08-25');
    assert.ok(panel.xForDate('2026-08-25')-panel.xForDate('2025-10-16') > step*300);
    assert.ok(panel.missingDayCount.value > 300);
    const path=panel.plottedSeries.value.find(s=>s.key==='europe').path;
    assert.equal((path.match(/M/g)||[]).length,4); // both interday and intraday gaps break
    assert.ok(panel.dateTicks.value.every((t,i,a)=>!i||t.date>a[i-1].date));
    assert.ok(panel.formatDate('2025-10-16').startsWith('2025'));
  } finally {close();}
});


test('a failed precision load can be retried from an existing range button without refreshing the page', async () => {
  const options={}; const {panel,close}=mountPanel(points,options);
  try {
    await panel.load(); await settle();
    options.failFull=true; panel.precision.value='4h'; await settle();
    assert.equal(panel.status.value,'error');
    panel.selectPresetRange(30); await settle();
    assert.equal(panel.status.value,'ready');
    assert.ok(panel.points.value.length);
  } finally {close();}
});
