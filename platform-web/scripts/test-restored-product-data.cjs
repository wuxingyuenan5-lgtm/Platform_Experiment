'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const root = path.resolve(__dirname, '..');
const restoredPages = [
  'src/views/dashboard/index.vue',
  'src/views/financialAi/index.vue',
  'src/views/strategy/management/index.vue',
  'src/views/strategy/funding-carry/index.vue',
  'src/views/strategy/spread-carry/index.vue',
  'src/views/newsCalendar/index.vue',
  'src/views/settings/index.vue',
];

test('restored product pages disclose data state and actionable boundary', () => {
  for (const relative of restoredPages) {
    const source = fs.readFileSync(path.join(root, relative), 'utf8');
    assert.match(source, /RestoredProduct(?:Surface|DataBanner)/, relative);
    assert.match(source, /(?:actionable|:actionable)="?false/, relative);
  }
});

test('production restored pages do not import fixture mock or seed directories', () => {
  for (const relative of restoredPages) {
    const source = fs.readFileSync(path.join(root, relative), 'utf8');
    assert.equal(/(?:from|import|require)[^\n]{0,120}[\\/](?:fixtures?|seeds?|mocks?)[\\/]/i.test(source), false, relative);
  }
});

test('sample product data contract rejects actionable sample state', () => {
  const source = fs.readFileSync(path.join(root, 'src/data/productDataEnvelope.ts'), 'utf8');
  assert.match(source, /value\.state === 'sample' && value\.actionable/);
  assert.match(source, /sample product data must not be actionable/);
});

test('cross venue execution workspace remains the formal execution owner', () => {
  const source = fs.readFileSync(path.join(root, 'src/views/strategy/spread-carry/index.vue'), 'utf8');
  assert.match(source, /CrossVenueExecutionWorkspace/);
  assert.doesNotMatch(source, /SpreadExecutionWorkspace/);
});
