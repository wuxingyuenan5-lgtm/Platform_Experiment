const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
function load(relative) {
  const file = path.join(__dirname, '../src/views/hedgeBoard', relative);
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText;
  const exports = {};
  vm.runInNewContext(code, { exports, require });
  return exports;
}
const { researchModules } = load('nativeData/dashboardClean.ts');
const { macroDetailGroups, weeklyDetailGroup, hasWeeklyDetail } = load('macro/detailGroups.ts');
const sections = researchModules.find((m) => m.id === 'macro').sections;
test('all macro detail widgets have exactly one group and at most three choices', () => {
  for (const [id, groups] of Object.entries(macroDetailGroups)) {
    assert.ok(groups.length >= 2 && groups.length <= 3, id);
    const widgets = sections.find((section) => section.id === id).widgets;
    for (const widget of widgets) {
      assert.equal(
        groups.filter((group) => group.includes(widget)).length,
        1,
        `${id}: ${widget.title}`,
      );
    }
    for (const group of groups) assert.ok(widgets.some(group.includes), `${id}: ${group.key}`);
  }
});
test('weekly report regional exceptions go to a matching visible subgroup', () => {
  for (const [section, id, expected] of [
    ['macro-liquidity', 'us_m2_yoy', 'global'],
    ['macro-liquidity', 'omo_net', 'cn'],
    ['macro-growth', 'global_composite_pmi', 'other'],
    ['macro-growth', 'passenger_car_retail', 'cn'],
    ['macro-inflation', 'lme_copper_3m', 'other'],
    ['macro-inflation', 'pork_price', 'cn'],
    ['macro-risk-appetite', 'us_epu', 'credit'],
    ['macro-risk-appetite', 'style_large_growth', 'cn'],
    ['macro-fx', 'cfets_rmb', 'fx'],
  ]) {
    assert.equal(weeklyDetailGroup(section, id), expected);
    assert.ok(hasWeeklyDetail(section, expected));
    assert.ok(macroDetailGroups[section].some((group) => group.key === expected));
  }
  assert.equal(hasWeeklyDetail('macro-growth', 'us'), false);
  assert.equal(hasWeeklyDetail('macro-fx', 'funding'), false);
});
