const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const filename = path.resolve(
  __dirname,
  '../src/views/hedgeBoard/aShare/components/industryResearch.ts',
);
const code = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const mod = { exports: {} };
new Function('require', 'module', 'exports', code)(require, mod, mod.exports);
const { industryCode, industryThemes, themeIndustries } = mod.exports;

test('industry relationships use SW level-one codes, not ambiguous lower-level labels', () => {
  const data = {
    items: [
      {
        name: 'AI',
        members: [
          { code: '688981', industryCode: '801080', industry: '半导体' },
          { code: '000001', industryCode: '801750.SI', industry: '电子' },
          { code: '000002', industry: '电子' },
        ],
      },
    ],
  };
  assert.deepEqual(
    industryThemes(data, '801080.SI')[0].members.map((x) => x.code),
    ['688981'],
  );
  assert.deepEqual(industryThemes(data, ''), []);
  assert.equal(industryCode('801080.si'), '801080');
  assert.equal(industryCode('801080.SH'), '');
});

test('overlapping themes and repeated segments do not duplicate member counts', () => {
  const member = { code: '688981', industryCode: '801080', return20: null };
  const data = {
    items: [
      { name: 'AI', members: [member, { ...member, segment: '设备' }] },
      { name: '制造', members: [member, { code: '600000', industryCode: '801080' }] },
    ],
  };
  const links = industryThemes(data, '801080');
  assert.deepEqual(
    links.map((x) => x.members.length),
    [1, 2],
  );
  assert.equal(links[0].members[0].return20, null);
});

test('theme industry cards retain the industry observation and missingness without theme-level estimates', () => {
  const industries = [
    { code: '801080', name: '电子', medianPe: null, medianPb: '3.8200', count: 511 },
  ];
  const theme = {
    members: [
      { code: '688981', industryCode: '801080' },
      { code: '688981', industryCode: '801080' },
      { code: '000001', industryCode: '801750' },
    ],
  };
  assert.deepEqual(themeIndustries(theme, industries), [{ ...industries[0], themeMemberCount: 1 }]);
  assert.deepEqual(industries, [
    { code: '801080', name: '电子', medianPe: null, medianPb: '3.8200', count: 511 },
  ]);
});
