const fs = require('node:fs');
const path = require('node:path');
const { checkManifest } = require('./formal-route-manifest.cjs');
const { checkRegistry } = require('./formal-view-registry.cjs');

const root = path.resolve(__dirname, '..');
const read = (relative) => fs.readFileSync(path.join(root, relative), 'utf8');
const exists = (relative) => fs.existsSync(path.join(root, relative));
const lineCount = (relative) => read(relative).split(/\r?\n/).length;
const fail = (message) => {
  throw new Error(`[codebase-boundary] ${message}`);
};
const assert = (condition, message) => {
  if (!condition) fail(message);
};

const removedPaths = [
  'apps/test-server',
  'mock',
  'src/api/demo',
  'src/views/demo',
  'src/views/hooks/request',
  'src/router/routes/modules/hooks/request.ts',
  'src/views/account/components/LegacyAccountDataManager.vue',
  'src/views/hedgeBoard/nativeData/marketSnapshotTables.ts',
  'src/views/strategy/spread-carry/components/CrossVenueExecutionReplica.vue',
  'internal/vite-config/src/plugins/mock.ts',
];
for (const relative of removedPaths) {
  assert(!exists(relative), `removed template path returned: ${relative}`);
}

const workspace = read('pnpm-workspace.yaml');
assert(!workspace.includes("'apps/*'"), 'apps/* returned to the Workspace boundary');
assert(
  workspace.includes("'internal/*'") && workspace.includes("'packages/*'"),
  'maintained Workspace roots changed',
);

const rootPackage = JSON.parse(read('package.json'));
const vitePackage = JSON.parse(read('internal/vite-config/package.json'));
for (const dependency of ['mockjs', '@types/mockjs', 'vite-plugin-mock']) {
  assert(!rootPackage.dependencies?.[dependency], `runtime Mock dependency returned: ${dependency}`);
  assert(
    !rootPackage.devDependencies?.[dependency],
    `development Mock dependency returned: ${dependency}`,
  );
  assert(!vitePackage.dependencies?.[dependency], `Vite Mock dependency returned: ${dependency}`);
  assert(
    !vitePackage.devDependencies?.[dependency],
    `Vite Mock dependency returned: ${dependency}`,
  );
}

for (const envFile of [
  '.env.analyze',
  '.env.development',
  '.env.docker',
  '.env.production',
  '.env.test',
]) {
  assert(!read(envFile).includes('VITE_USE_MOCK'), `${envFile} re-enabled template Mock loading`);
}

const routeIndex = read('src/router/routes/index.ts');
const menuIndex = read('src/router/menus/index.ts');
for (const [name, source] of [
  ['routes', routeIndex],
  ['menus', menuIndex],
]) {
  assert(
    source.includes("import.meta.glob('./modules/*.ts'"),
    `${name} module discovery is not top-level bounded`,
  );
  assert(!source.includes('./modules/**/*.ts'), `${name} recursive module discovery returned`);
}

const helper = read('src/router/helper/routeHelper.ts');
assert(!helper.includes('import.meta.glob'), 'runtime View Glob authority returned');
assert(!helper.includes('@ts-nocheck'), 'routeHelper.ts returned to @ts-nocheck');
assert(helper.includes('resolveViewComponent'), 'runtime routes do not use the typed View Registry');
assert(helper.includes('return EXCEPTION_COMPONENT;'), 'missing dynamic View key is not fail-closed');

const hedgeBoardShell = 'src/views/hedgeBoard/index.vue';
const hedgeBoardOwners = [
  'src/views/hedgeBoard/composables/useHedgeBoardPage.ts',
  'src/views/hedgeBoard/charts/chartCore.ts',
  'src/views/hedgeBoard/charts/chartRange.ts',
  'src/views/hedgeBoard/charts/DualAxisChart.ts',
  'src/views/hedgeBoard/charts/TreasuryFlowChart.ts',
  'src/views/hedgeBoard/charts/EtfResearchPanels.ts',
  'src/views/hedgeBoard/charts/LocalChartWidget.ts',
  'src/views/hedgeBoard/hedgeBoard.less',
];
assert(lineCount(hedgeBoardShell) <= 700, 'Hedge Board page shell exceeds 700 lines');
for (const relative of hedgeBoardOwners) {
  assert(exists(relative), `Hedge Board owner is missing: ${relative}`);
  assert(lineCount(relative) <= 500, `Hedge Board owner exceeds 500 lines: ${relative}`);
}
const hedgeBoardSource = read(hedgeBoardShell);
assert(hedgeBoardSource.includes('useHedgeBoardPage'), 'Hedge Board page state owner is not wired');
assert(hedgeBoardSource.includes('LocalChartWidget'), 'Hedge Board chart owner is not wired');
assert(
  hedgeBoardSource.includes('src="./hedgeBoard.less"'),
  'Hedge Board style owner is not wired',
);
for (const legacyOwner of ['GroupedBarChart', 'SnapshotDetailTable', 'LOCAL_MARKET_DETAIL_TABLES']) {
  assert(
    !hedgeBoardSource.includes(legacyOwner),
    `Hedge Board legacy owner remains in page shell: ${legacyOwner}`,
  );
}

const crossVenueShell =
  'src/views/strategy/spread-carry/components/CrossVenueExecutionWorkspace.vue';
const crossVenueOwners = [
  crossVenueShell,
  'src/views/strategy/spread-carry/components/crossVenueExecutionWorkspace.less',
  'src/views/strategy/spread-carry/composables/useCrossVenueExecutionWorkspace.ts',
];
for (const relative of crossVenueOwners) {
  assert(exists(relative), `Cross Venue owner is missing: ${relative}`);
  assert(lineCount(relative) <= 500, `Cross Venue owner exceeds 500 lines: ${relative}`);
}
const spreadWorkspace = read(
  'src/views/strategy/spread-carry/components/SpreadExecutionWorkspace.vue',
);
assert(
  spreadWorkspace.includes('CrossVenueExecutionWorkspace'),
  'Spread workspace does not use the formal Cross Venue owner',
);
assert(
  !spreadWorkspace.includes('CrossVenueExecutionReplica'),
  'Spread workspace still imports the Replica owner',
);
const crossVenueSource = read(crossVenueShell);
assert(
  crossVenueSource.includes('useCrossVenueExecutionWorkspace'),
  'Cross Venue page state owner is not wired',
);
assert(
  crossVenueSource.includes('src="./crossVenueExecutionWorkspace.less"'),
  'Cross Venue style owner is not wired',
);

const registryResult = checkRegistry({ root });
for (const entry of registryResult.entries) {
  for (const forbidden of ['demo', 'mock', 'test', 'example', 'template', 'archive']) {
    assert(
      !entry.relative.toLowerCase().split('/').includes(forbidden),
      `non-product View entered the Registry: ${entry.relative}`,
    );
  }
}

const manifestResult = checkManifest({ root });
const manifest = JSON.parse(manifestResult.bytes.toString('utf8'));
for (const module of manifest.modules) {
  assert(!module.path.includes('/demo/'), `formal route references Demo module: ${module.path}`);
  for (const route of module.routes) {
    if (!route.view_import) continue;
    for (const forbidden of ['demo', 'mock', 'test', 'example', 'template']) {
      assert(
        !route.view_import.toLowerCase().split('/').includes(forbidden),
        `non-product View entered formal manifest: ${route.view_import}`,
      );
    }
  }
}
console.log(
  `Codebase boundaries passed: ${manifest.modules.length} formal route modules, ${registryResult.entries.length} View keys; manifest ${manifestResult.sha256}.`,
);
