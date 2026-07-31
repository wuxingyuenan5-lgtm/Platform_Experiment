const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const dashboardPath = path.join(root, 'src', 'views', 'dashboard', 'index.vue');
const source = fs.readFileSync(dashboardPath, 'utf8');

const checks = [
  {
    name: 'homepage keeps a dedicated 1200-1599px hero layout',
    pass:
      /@media\s*\(max-width:\s*1599px\)[\s\S]*?\.home-hero\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0,\s*1\.08fr\)\s*minmax\(390px,\s*0\.92fr\)/.test(
        source,
      ),
  },
  {
    name: 'homepage returns to one-column hero below 1200px',
    pass:
      /@media\s*\(max-width:\s*1199px\)[\s\S]*?\.home-hero\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0,\s*1fr\)/.test(
        source,
      ),
  },
  {
    name: 'LESS avoids native min/max function expressions that break Vite LESS',
    pass: !/\b(?:min|max)\(/.test(source),
  },
  {
    name: 'homepage copy remains real HTML instead of baked into the bitmap',
    pass: source.includes('class="home-hero__copy"'),
  },
  {
    name: 'strategy panel keeps visible spacing between title and list',
    pass:
      /\.panel-strategy header\s*\{[\s\S]*?margin-bottom:\s*28px;[\s\S]*?\}/.test(source) &&
      /\.panel-strategy \.strategy-list\s*\{[\s\S]*?margin-top:\s*0;[\s\S]*?\}/.test(source),
  },
];

const failed = checks.filter((check) => !check.pass);

for (const check of checks) {
  console.log(`${check.pass ? 'PASS' : 'FAIL'} ${check.name}`);
}

if (failed.length > 0) {
  process.exitCode = 1;
}
