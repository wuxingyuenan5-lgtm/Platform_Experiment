const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const vm = require('node:vm');

function panel(asset = 'btc') {
  const source = fs.readFileSync(path.join(__dirname, '../src/views/hedgeBoard/components/BtcEtfFlowPanel.vue'), 'utf8');
  const script = source.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1];
  const code = ts.transpileModule(script + '\nexports.state = { data, startIndex, endIndex, chart, showPrice };', {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const vue = { ref: value => ({ value }), computed: get => ({ get value() { return get(); } }), watch: () => {}, onMounted: () => {} };
  const exports = {};
  vm.runInNewContext(code, { exports, require: name => name === 'vue' ? vue : {}, defineProps: () => ({ asset }), withDefaults: props => props });
  return exports.state;
}

test('sparse prices draw real segments, break gaps, and retain isolated points', () => {
  const state = panel();
  state.data.value = { days: Array.from({ length: 12 }, (_, index) => ({ date: `2026-10-${String(index+1).padStart(2, '0')}`, flows: { Total: 5 }, price: ({ 0: 80000, 1: 81000, 8: 82000 })[index] ?? null })) };
  state.endIndex.value = 11;
  const chart = state.chart.value;
  assert.equal(chart.hasPriceLine, true);
  assert.equal(chart.priceLine.match(/M /g).length, 2);
  assert.equal(chart.priceLine.match(/L /g).length, 1);
  assert.equal(chart.isolatedPrices.length, 1);
  assert.equal(chart.isolatedPrices[0].date, '2026-10-09');
  assert.equal(chart.pricedCount, 3);
  assert.equal(chart.lastPrice, 82000);
  assert.ok(chart.priceTicks.every(tick => Number.isFinite(tick.y)));
  const axisBefore = chart.priceTicks.map(tick => tick.value).join();
  state.showPrice.value = false;
  assert.equal(state.chart.value.priceTicks.map(tick => tick.value).join(), axisBefore);
  state.showPrice.value = true;
  assert.equal(state.chart.value.hasPriceLine, true);
});

test('BTC and ETH use left price axis; missing prices remain absent', () => {
  for (const asset of ['btc', 'eth']) {
    const state = panel(asset);
    state.data.value = { days: [{ date: '2026-10-01', flows: { Total: -5 }, price: null }] };
    assert.equal(state.chart.value.pad.left, 74);
    assert.equal(state.chart.value.pad.right, 18);
    assert.equal(state.chart.value.hasPriceAxis, false);
    assert.equal(state.chart.value.priceLine, '');
    assert.equal(state.chart.value.isolatedPrices.length, 0);
  }
});
