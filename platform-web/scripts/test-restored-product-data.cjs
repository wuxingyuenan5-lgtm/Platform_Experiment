'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const root = path.resolve(__dirname, '..');
const productionPages = [
  'src/views/dashboard/index.vue',
  'src/views/financialAi/dailyReview.vue',
  'src/views/financialAi/stockAnalysis.vue',
  'src/views/financialAi/newsRadar.vue',
  'src/views/financialAi/aiConnection.vue',
  'src/views/strategy/management/index.vue',
  'src/views/strategy/funding-carry/index.vue',
  'src/views/strategy/spread-carry/index.vue',
  'src/views/newsCalendar/index.vue',
  'src/views/settings/index.vue',
];

function read(relative) {
  return fs.readFileSync(path.join(root, relative), 'utf8');
}

test('formal product pages do not import fixture, mock or seed directories', () => {
  for (const relative of productionPages) {
    const source = read(relative);
    assert.equal(
      /(?:from|import|require)[^\n]{0,120}[\\/](?:fixtures?|seeds?|mocks?)[\\/]/i.test(source),
      false,
      relative,
    );
  }
});

test('financial AI routes use the four current pages instead of the retired aggregate page', () => {
  const routes = read('src/router/routes/modules/financial-ai.ts');
  for (const page of ['dailyReview.vue', 'stockAnalysis.vue', 'newsRadar.vue', 'aiConnection.vue']) {
    assert.equal(routes.includes(page), true, `financial AI routes do not use ${page}`);
  }
  assert.doesNotMatch(routes, /financialAi\/index\.vue/);
});

test('sample product data contract rejects actionable sample state', () => {
  const source = read('src/data/productDataEnvelope.ts');
  assert.match(source, /value\.state === 'sample' && value\.actionable/);
  assert.match(source, /sample product data must not be actionable/);
});

test('cross venue execution workspace remains the formal execution owner', () => {
  const source = read('src/views/strategy/spread-carry/index.vue');
  assert.match(source, /CrossVenueExecutionWorkspace/);
  assert.doesNotMatch(source, /SpreadExecutionWorkspace/);
});
