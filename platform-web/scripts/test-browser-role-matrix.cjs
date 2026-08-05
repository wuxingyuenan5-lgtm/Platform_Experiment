'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const root = path.resolve(__dirname, '..');

function read(relative) {
  return fs.readFileSync(path.join(root, relative), 'utf8');
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
  ['/users', 'user.read'],
  ['/audit', 'audit:read'],
  ['/account', 'profile.read_self'],
]);

test('formal route families are mapped to one server capability namespace', () => {
  const source = read('src/access/browserRouteCapabilities.ts');
  for (const [route, permission] of expected) {
    assert.equal(
      source.includes(`'${route}': '${permission}'`),
      true,
      `${route} lacks ${permission}`,
    );
  }
  assert.match(source, /delete meta\.roles/);
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
