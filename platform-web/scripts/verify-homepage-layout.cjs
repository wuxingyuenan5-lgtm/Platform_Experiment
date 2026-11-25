const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const dashboardPath = path.join(root, 'src', 'views', 'dashboard', 'index.vue');
const source = fs.readFileSync(dashboardPath, 'utf8');

const workspace = fs.readFileSync(
  path.join(root, 'src/views/dashboard/workspace/PersonalWorkspace.vue'),
  'utf8',
);
const checks = [
  {
    name: 'desktop hero keeps separate flexible copy and summary columns',
    pass: /\.home-hero\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0,\s*1\.42fr\)\s*minmax\(380px,\s*0\.58fr\)/.test(
      source,
    ),
  },
  {
    name: 'hero collapses at tablet width and summaries at narrow width',
    pass:
      /@media\s*\(max-width:\s*1024px\)[\s\S]*?\.home-hero\s*\{[\s\S]*?grid-template-columns:\s*1fr/.test(
        source,
      ) &&
      /@media\s*\(max-width:\s*768px\)[\s\S]*?\.home-hero__summaries,[\s\S]*?grid-template-columns:\s*1fr/.test(
        source,
      ),
  },
  {
    name: 'LESS avoids unsupported native min/max expressions',
    pass: !/\b(?:min|max)\(/.test(source),
  },
  {
    name: 'homepage title stays real HTML',
    pass: source.includes('class="home-hero__copy"') && source.includes('<h1>全球变量</h1>'),
  },
  {
    name: 'personal workspace replaces old strategy list with bounded responsive cards',
    pass:
      source.includes('<PersonalWorkspace') &&
      workspace.includes('min-width: 0;') &&
      /@media\s*\(max-width:\s*800px\)[\s\S]*?\.cards\s*\{[\s\S]*?grid-template-columns:\s*1fr/.test(
        workspace,
      ) &&
      /\.card > header\s*\{[\s\S]*?padding-bottom:\s*10px/.test(workspace),
  },
];

const failed = checks.filter((check) => !check.pass);

for (const check of checks) {
  console.log(`${check.pass ? 'PASS' : 'FAIL'} ${check.name}`);
}

if (failed.length > 0) {
  process.exitCode = 1;
}
