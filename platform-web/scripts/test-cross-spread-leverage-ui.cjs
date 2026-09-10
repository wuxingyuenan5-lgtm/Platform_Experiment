const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const test = require('node:test');
const source = fs.readFileSync(
  require('node:path').join(
    __dirname,
    '../src/views/strategy/spread-carry/components/SpreadExecutionCommand.vue',
  ),
  'utf8',
);
const functions = source.slice(
  source.indexOf('  async function applyBybitLeverage()'),
  source.indexOf('  onMounted(refreshLeverage)'),
);
function harness(accept, failure) {
  const writes = [];
  const context = {
    isCeo: { value: true },
    leverageLoading: { value: false },
    bybitLeverageInput: { value: '50' },
    currentLeverage: { value: '20' },
    leverageMessage: { value: '' },
    Modal: {
      confirm(options) {
        accept ? options.onOk() : options.onCancel();
      },
    },
    setCrossSpreadLeverage: async (value) => {
      writes.push(value);
      if (failure) throw failure;
      return { symbol: 'XAUTUSDT', leverage: value };
    },
    getCrossSpreadLeverage: async () => ({ leverage: '20' }),
  };
  vm.createContext(context);
  vm.runInContext(
    ts.transpileModule(functions, { compilerOptions: { target: ts.ScriptTarget.ES2022 } })
      .outputText,
    context,
  );
  return { context, writes };
}
test('refresh preserves the proposed 50x while showing actual 20x; confirmation sends once', async () => {
  const { context: c, writes } = harness(true);
  await c.refreshLeverage();
  assert.equal(c.bybitLeverageInput.value, '50');
  assert.equal(c.currentLeverage.value, '20');
  await c.applyBybitLeverage();
  assert.deepEqual(writes, ['50']);
  assert.equal(c.currentLeverage.value, '50');
});
test('cancellation never sends a leverage write', async () => {
  const { context: c, writes } = harness(false);
  await c.applyBybitLeverage();
  assert.deepEqual(writes, []);
});
test('unconfirmed failure retains exchange value and does not retry', async () => {
  const { context: c, writes } = harness(true, new Error('timeout'));
  await c.applyBybitLeverage();
  assert.deepEqual(writes, ['50']);
  assert.equal(c.currentLeverage.value, '20');
  assert.match(c.leverageMessage.value, /未确认/);
  assert.equal(c.leverageLoading.value, false);
});
