'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const ts = require('typescript');

const source = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'views', 'hedgeBoard', 'nativeData', 'marketDetailAdapter.ts'),
  'utf8',
);
const output = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;
const moduleUnderTest = { exports: {} };
new vm.Script(`(function (require, module, exports) { ${output}\n})`).runInThisContext()(
  require,
  moduleUnderTest,
  moduleUnderTest.exports,
);

test('live market detail updates the complete visible row instead of only the sparkline', () => {
  const groups = [
    {
      title: '主要资产',
      rows: [
        {
          id: 'crypto-btc-row',
          name: 'Bitcoin',
          symbol: 'BTC',
          price: 'old',
          d1: 'old',
          w1: 'old',
          m1: 'old',
          qtd: 'old',
          ytd: 'old',
          y1: 'old',
          high: 'old',
          spark: [],
        },
      ],
    },
  ];
  const remoteRows = [
    {
      id: 'crypto-btc-row',
      name: 'remote-name',
      symbol: 'remote-symbol',
      status: 'ready',
      unit: 'price',
      changeUnit: 'percent',
      close: 100,
      change1d: 1,
      change1w: 2,
      change1m: 3,
      changeQtd: 4,
      changeYtd: 5,
      change1y: 6,
      distance52wHigh: -7,
      spark30d: [98, 99, 100],
      spark90d: [],
    },
  ];

  const [row] = moduleUnderTest.exports.mergeLiveMarketDetail(groups, remoteRows)[0].rows;

  assert.equal(row.name, 'Bitcoin');
  assert.equal(row.symbol, 'BTC');
  assert.equal(row.price, '$100.00');
  assert.equal(row.d1, '+1.00%');
  assert.equal(row.w1, '+2.00%');
  assert.equal(row.m1, '+3.00%');
  assert.equal(row.qtd, '+4.00%');
  assert.equal(row.ytd, '+5.00%');
  assert.equal(row.y1, '+6.00%');
  assert.equal(row.high, '-7.00%');
  assert.deepEqual(row.spark, [98, 99, 100]);
});
