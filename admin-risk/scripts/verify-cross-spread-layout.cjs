const fs = require('fs');
const path = require('path');
const assert = require('assert');

const componentPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'components',
  'CrossVenueExecutionReplica.vue',
);

const source = fs.readFileSync(componentPath, 'utf8');

const baseQuoteStatsRule = source.match(/\.quote-stats\s*\{[\s\S]*?\n  \}/m);
assert(baseQuoteStatsRule, 'Could not find the base .quote-stats rule.');
assert.match(
  baseQuoteStatsRule[0],
  /grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\);/m,
  'Expected the base quote stats layout to preserve the original 4-column layout.',
);

const compactSummaryRule = source.match(/\.summary-item--compact strong\s*\{[\s\S]*?\n  \}/m);
assert(compactSummaryRule, 'Could not find the .summary-item--compact strong rule.');
assert.match(
  compactSummaryRule[0],
  /font-size:\s*16px;/m,
  'Expected compact summary metrics to use a unified 16px font size.',
);

const summaryStrongRule = source.match(/\.summary-item strong\s*\{[\s\S]*?\n  \}/m);
assert(summaryStrongRule, 'Could not find the .summary-item strong rule.');
assert.match(
  summaryStrongRule[0],
  /font-size:\s*16px;/m,
  'Expected summary metrics to align to the same 16px font size.',
);

assert.match(
  source,
  /\.cross-card--summary\s+\.summary-item\s+\.(?:red|green)\s*\{[\s\S]*?color:\s*var\(--strategy-text-1\)\s*!important;/m,
  'Expected summary card numbers to override special red/green colors with the default text color.',
);

console.log('Cross spread layout checks passed.');
