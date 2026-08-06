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
const sampleModules = [
  'src/data/sample/dashboard/index.ts',
  'src/data/sample/strategy/index.ts',
  'src/data/sample/funding/index.ts',
  'src/data/sample/spread/index.ts',
  'src/data/sample/news/index.ts',
];

function read(relative) {
  return fs.readFileSync(path.join(root, relative), 'utf8');
}

test('restored product pages render a product state surface or banner', () => {
  for (const relative of restoredPages) {
    assert.match(read(relative), /RestoredProduct(?:Surface|DataBanner)/, relative);
  }
});

test('sample data envelopes are explicit, sourced and non-actionable', () => {
  for (const relative of sampleModules) {
    const source = read(relative);
    assert.match(source, /state:\s*'sample'/, relative);
    assert.match(source, /source:\s*'sample:/, relative);
    assert.match(source, /actionable:\s*false/, relative);
    assert.match(source, /asOf:/, relative);
  }
});

test('unavailable product surfaces remain explicitly non-actionable', () => {
  const financialAi = read('src/views/financialAi/index.vue');
  assert.match(financialAi, /state="unavailable"/);
  assert.match(financialAi, /source="not-configured:financial-ai-provider"/);
  assert.match(financialAi, /:actionable="false"/);

  const settings = read('src/views/settings/index.vue');
  assert.match(settings, /state="unavailable"/);
  assert.match(settings, /source="not-configured:settings-write-owner"/);
  assert.match(settings, /:actionable="false"/);
});

test('production restored pages do not import fixture mock or seed directories', () => {
  for (const relative of restoredPages) {
    const source = read(relative);
    assert.equal(
      /(?:from|import|require)[^\n]{0,120}[\\/](?:fixtures?|seeds?|mocks?)[\\/]/i.test(source),
      false,
      relative,
    );
  }
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
