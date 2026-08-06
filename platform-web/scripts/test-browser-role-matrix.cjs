'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');

function read(relative) {
  return fs.readFileSync(path.join(root, relative), 'utf8');
}

function loadTypeScriptModule(relative, mocks = {}) {
  const source = read(relative);
  const output = ts.transpileModule(source, {
    compilerOptions: {
      esModuleInterop: true,
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
    fileName: relative,
  }).outputText;
  const module = { exports: {} };
  const localRequire = (request) => {
    if (Object.prototype.hasOwnProperty.call(mocks, request)) return mocks[request];
    if (request.startsWith('@/views/')) return {};
    throw new Error(`Unexpected require from ${relative}: ${request}`);
  };
  const wrapper = new vm.Script(`(function (require, module, exports) {\n${output}\n})`, {
    filename: relative,
  });
  wrapper.runInNewContext({ console, Promise })(localRequire, module, module.exports);
  return module.exports;
}

const expected = new Map([
  ['/home', 'dashboard.read'],
  ['/hedge-board', 'research.read'],
  ['/strategy', 'strategy.read'],
  ['/finance', 'finance.read'],
  ['/data', 'data.read'],
  ['/monitor', 'monitor.read'],
  ['/reports', 'reports.read'],
  ['/news-calendar', 'news.read'],
  ['/financial-ai', 'financial_ai.read'],
  ['/settings', 'settings.read'],
  ['/risk', 'risk.read'],
  ['/risk/detail', 'risk.read'],
  ['/risk/users', 'user.read'],
  ['/risk/profile', 'profile.read_self'],
  ['/users', 'user.read'],
  ['/audit', 'audit:read'],
  ['/account', 'profile.read_self'],
]);

test('formal route families and precise child routes use the server capability namespace', () => {
  const source = read('src/access/browserRouteCapabilities.ts');
  for (const [route, permission] of expected) {
    assert.equal(
      source.includes(`'${route}': '${permission}'`),
      true,
      `${route} lacks ${permission}`,
    );
  }
  assert.match(source, /explicitCapability \?\? mappedCapability \?\? inheritedCapability/);
  assert.match(source, /delete meta\.roles/);
});

test('applyBrowserRouteCapabilities preserves precise permissions on the real risk route tree', () => {
  const { applyBrowserRouteCapabilities } = loadTypeScriptModule(
    'src/access/browserRouteCapabilities.ts',
  );
  const riskModule = loadTypeScriptModule('src/router/routes/modules/risk.ts', {
    '@/enums/roleEnum': {
      RoleEnum: {
        CEO: 'ceo',
        EMPLOYEE: 'employee',
        TECH_LEAD: 'tech_lead',
      },
    },
    '@/router/constant': { LAYOUT: Symbol('layout') },
  });
  const { canAccessRoute } = loadTypeScriptModule('src/access/userAccess.ts');
  const transformed = applyBrowserRouteCapabilities([riskModule.default]);
  const risk = transformed[0];
  const detail = risk.children.find((route) => route.path === 'detail');
  const users = risk.children.find((route) => route.path === 'users');
  const profile = risk.children.find((route) => route.path === 'profile');

  assert.equal(risk.meta.permissions, 'risk.read');
  assert.equal(detail.meta.permissions, 'risk.read');
  assert.equal(users.meta.permissions, 'user.read');
  assert.equal(profile.meta.permissions, 'profile.read_self');

  const canAccessMatched = (granted, matched) =>
    matched.every((route) => canAccessRoute(granted, route.meta));
  const employee = ['risk.read', 'user.read', 'profile.read_self'];
  const techLead = ['risk.read', 'user.read', 'profile.read_self'];
  const ceo = ['risk.read', 'user.read', 'profile.read_self'];

  assert.equal(canAccessMatched(['risk.read'], [risk, detail]), true);
  assert.equal(canAccessMatched(['risk.read'], [risk, users]), false);
  assert.equal(canAccessMatched(['profile.read_self'], [risk, users]), false);
  assert.equal(canAccessMatched(employee, [risk, users]), true);
  assert.equal(canAccessMatched(techLead, [risk, users]), true);
  assert.equal(canAccessMatched(ceo, [risk, users]), true);
  assert.equal(canAccessMatched(employee, [risk, profile]), true);
});

test('the exported async route tree receives capability metadata before menu and guard use', () => {
  const source = read('src/router/routes/index.ts');
  assert.match(source, /applyBrowserRouteCapabilities/);
  assert.match(source, /export const asyncRoutes = applyBrowserRouteCapabilities/);
});

test('browser permission helper remains compatible with API-key wildcard permissions', () => {
  const source = read('src/access/userAccess.ts');
  assert.match(
    source,
    /granted\.includes\('\*'\) \|\| granted\.includes\(permission\)/,
  );
});

test('the formal route module directory is part of the full TypeScript project', () => {
  const config = JSON.parse(read('tsconfig.full.json'));
  assert.equal(config.include.includes('src/router/routes/modules/**/*.ts'), true);
});
