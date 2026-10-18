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

test('detail retains source observation semantics and clears them when a row disappears', () => {
  const groups = [{label:'US', rows:[{id:'us-spy', symbol:'SPY', spark:[]}]}];
  const rows = [{id:'us-spy', symbol:'SPY', status:'stale', unit:'price', changeUnit:'percent',
    observationDate:'2026-10-15', asOf:'2026-10-15T10:32:00-04:00', currency:'USD',
    priceKind:'intraday', source:'Yahoo Finance', qualityFlags:['unfinished_daily_bar'], spark30d:[], close:'12'}];
  const merged = moduleUnderTest.exports.mergeLiveMarketDetail(groups, rows);
  assert.equal(merged[0].rows[0].asOf, rows[0].asOf);
  assert.equal(merged[0].rows[0].priceKind, 'intraday');
  assert.equal(merged[0].rows[0].dataStatus, 'stale');
  const removed = moduleUnderTest.exports.mergeLiveMarketDetail(merged, []);
  assert.equal(removed[0].rows[0].observationDate, undefined);
  assert.equal(removed[0].rows[0].dataStatus, 'no_data');
});

test('US/global cards, table, breadth and rotation never fall back to sample facts', () => {
  const seed = { id: 'us-spy', symbol: 'SPY', name: '标普500', price: '$999', d1: '+99%', spark: [99], d200: '▲', x50200: '▲' };
  const config = { id: 'us', detailGroups: [{ label: '指数', rows: [seed] }],
    overviewChip: 'sample', updatedAt: 'sample', overviewCards: [{...seed, change: '+99%'}],
    moverCards: [], breadthCards: [{ value: '99%', tag: 'high', delta: '5' }],
    volatilityCards: [{ title: 'VIX', value: '99' }], rotationHeatmap: [{ symbol: 'SPY', d1: '+99%' }] };
  const empty = moduleUnderTest.exports.mergeTerminalMarket(config, []);
  assert.equal(empty.detailGroups[0].rows[0].price, '—');
  assert.equal(empty.detailGroups[0].rows[0].x50200, '—');
  assert.deepEqual(empty.overviewCards[0].spark, []);
  assert.equal(empty.overviewCards[0].change, '—');
  assert.equal(empty.rotationHeatmap[0].d1, '—');
  assert.equal(empty.breadthCards[0].value, '—');
  assert.equal(empty.volatilityCards[0].value, '—');
  const live = moduleUnderTest.exports.mergeTerminalMarket(config, [{
    id: 'us-spy', symbol: 'SPY', status: 'ready', unit: 'price', changeUnit: 'percent',
    close: '12.34', change1d: '2.5', spark30d: ['12', '12.34'], signals: { d10: '▲' },
  }]);
  assert.equal(live.detailGroups[0].rows[0].price, '$12.34');
  assert.equal(live.detailGroups[0].rows[0].d10, '▲');
  assert.equal(live.overviewCards[0].change, '+2.50%');
  assert.equal(live.rotationHeatmap[0].d1, '+2.50%');
  assert.equal(config.overviewChip, 'sample');
});

test('rotation preserves each instrument source date and stale state, missing rows stay empty', () => {
  const config = { id: 'global', detailGroups: [], rotationHeatmap: [{symbol: 'EWA'}, {symbol: 'RSX'}] };
  const result = moduleUnderTest.exports.mergeTerminalMarket(config, [{symbol:'EWA', status:'stale', observationDate:'2026-10-08', source:'Yahoo Finance', sourceUrl:'https://finance.yahoo.com/quote/EWA', change1d:'1.5'}]);
  assert.equal(result.rotationHeatmap[0].observationDate, '2026-10-08');
  assert.equal(result.rotationHeatmap[0].dataStatus, 'stale');
  assert.equal(result.rotationHeatmap[0].source, 'Yahoo Finance');
  assert.equal(result.rotationHeatmap[1].observationDate, undefined);
  assert.equal(result.rotationHeatmap[1].d1, '—');
});

test('macro missing rows and continuous commodity futures preserve truthful display', () => {
  const config = [{ label: '商品', rows: [{ id: 'gold-xauusd', name: '现货黄金', symbol: 'XAUUSD', price: '99', spark: [99] }] }];
  assert.equal(moduleUnderTest.exports.mergeMacroMarketDetail(config, [])[0].rows[0].price, '—');
  const result = moduleUnderTest.exports.mergeLiveMarketDetail(config, [{
    id: 'gold-xau-row', name: '黄金期货（连续合约）', symbol: 'GC=F', status: 'ready',
    qualityFlags: ['continuous_futures_not_spot'], spark30d: ['10'], unit: 'price', changeUnit: 'percent', close: '10',
  }])[0].rows[0];
  assert.equal(result.symbol, 'GC=F');
  assert.equal(result.name, '黄金期货（连续合约）');
});

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

test('breadth displays coverage and source date, not seed values', () => {
  const config = { detailGroups: [], breadthCards: [{ id: 'gold-b20', value: '99%' }] };
  const result = moduleUnderTest.exports.mergeTerminalMarket(config, [{
    id: 'gold-b20', symbol: 'BREADTH20', status: 'partial', close: '62.5',
    sampleSize: 7, expectedSampleSize: 8, observationDate: '2026-10-09',
  }]);
  assert.equal(result.breadthCards[0].value, '62.5%');
  assert.equal(result.breadthCards[0].tag, '7/8 样本');
  assert.equal(result.breadthCards[0].delta, '2026-10-09');
});

test('IMOEX never displays obsolete RSX values under the replacement symbol', () => {
 const groups=[{label:'新兴市场',rows:[{id:'global-rsx',name:'俄罗斯（MOEX 指数）',symbol:'IMOEX',spark:[]}]}];
 const source={id:'global-rsx',symbol:'RSX',status:'ready',unit:'price',changeUnit:'percent',close:'5.62',spark30d:[5.6],spark90d:[]};
 assert.equal(moduleUnderTest.exports.mergeLiveMarketDetail(groups,[source])[0].rows[0].price,'—');
 const row=moduleUnderTest.exports.mergeLiveMarketDetail(groups,[{...source,symbol:'IMOEX',unit:'index',close:'2400.12',currency:'RUB'}])[0].rows[0];
 assert.equal(row.price,'2400.12');
 assert.equal(row.currency,'RUB');
});
