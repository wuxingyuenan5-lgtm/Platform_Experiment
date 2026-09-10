#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  ManifestError,
  checkManifest,
  generateManifest,
  generatedBytes,
  writeManifest,
} = require('./formal-route-manifest.cjs');

const root = path.resolve(__dirname, '..');
const manifestPath = path.join(root, 'scripts', 'formal-route-manifest.json');

function expectManifestError(callback, pattern) {
  assert.throws(callback, (error) => error instanceof ManifestError && pattern.test(error.message));
}

function copyFixture() {
  const fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'formal-route-manifest-'));
  const routeTarget = path.join(fixture, 'src', 'router', 'routes', 'modules');
  fs.mkdirSync(path.dirname(routeTarget), { recursive: true });
  fs.cpSync(path.join(root, 'src', 'router', 'routes', 'modules'), routeTarget, { recursive: true });
  const viewsTarget = path.join(fixture, 'src', 'views');
  fs.mkdirSync(path.dirname(viewsTarget), { recursive: true });
  fs.symlinkSync(path.join(root, 'src', 'views'), viewsTarget, 'dir');
  return fixture;
}

function accountModule(fixture) {
  return path.join(fixture, 'src', 'router', 'routes', 'modules', 'account.ts');
}

function testCurrentManifest() {
  const result = checkManifest({ root, manifestPath });
  assert.match(result.sha256, /^[0-9a-f]{64}$/);
}

function testRepeatedGenerationIsByteIdentical() {
  assert.deepEqual(generatedBytes({ root }), generatedBytes({ root }));
}

function testDriftAndRewrite() {
  const fixture = copyFixture();
  try {
    const candidate = path.join(fixture, 'formal-route-manifest.json');
    writeManifest({ root: fixture, manifestPath: candidate });
    checkManifest({ root: fixture, manifestPath: candidate });
    const modulePath = accountModule(fixture);
    fs.appendFileSync(modulePath, '\n// deterministic drift test\n', 'utf8');
    expectManifestError(
      () => checkManifest({ root: fixture, manifestPath: candidate }),
      /manifest drift detected.*--write/,
    );
    writeManifest({ root: fixture, manifestPath: candidate });
    checkManifest({ root: fixture, manifestPath: candidate });
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
}

function testMissingViewFails() {
  const fixture = copyFixture();
  try {
    const modulePath = accountModule(fixture);
    const source = fs.readFileSync(modulePath, 'utf8').replace(
      "@/views/account/index.vue",
      "@/views/account/does-not-exist.vue",
    );
    fs.writeFileSync(modulePath, source, 'utf8');
    expectManifestError(() => generateManifest({ root: fixture }), /View cannot resolve/);
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
}

function testDuplicateNameFails() {
  const fixture = copyFixture();
  try {
    const source = fs.readFileSync(accountModule(fixture), 'utf8')
      .replace("path: '/account'", "path: '/account-copy'")
      .replace("redirect: '/account/index'", "redirect: '/account-copy/copy'")
      .replace("path: 'index'", "path: 'copy'");
    fs.writeFileSync(
      path.join(fixture, 'src', 'router', 'routes', 'modules', 'account-copy.ts'),
      source,
      'utf8',
    );
    expectManifestError(() => generateManifest({ root: fixture }), /duplicate Route name/);
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
}

function testDuplicatePathFails() {
  const fixture = copyFixture();
  try {
    const source = fs.readFileSync(accountModule(fixture), 'utf8')
      .replace("name: 'Account'", "name: 'AccountCopy'")
      .replace("name: 'AccountIndex'", "name: 'AccountCopyIndex'");
    fs.writeFileSync(
      path.join(fixture, 'src', 'router', 'routes', 'modules', 'account-copy.ts'),
      source,
      'utf8',
    );
    expectManifestError(() => generateManifest({ root: fixture }), /duplicate Route path/);
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
}

function testNestedDemoMockTestDirectoriesAreExcluded() {
  const fixture = copyFixture();
  try {
    for (const name of ['demo', 'mock', 'test']) {
      const target = path.join(fixture, 'src', 'router', 'routes', 'modules', name);
      fs.mkdirSync(target, { recursive: true });
      fs.writeFileSync(path.join(target, 'nested.ts'), 'throw new Error("must not load");\n');
    }
    const manifest = generateManifest({ root: fixture });
    assert.equal(manifest.modules.length, 15);
    assert.ok(manifest.modules.every((module) => !/[\\/](demo|mock|test)[\\/]/.test(module.path)));
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
}

function testManifestIsNotRuntimeImported() {
  const sourceRoot = path.join(root, 'src');
  const pending = [sourceRoot];
  while (pending.length) {
    const current = pending.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const target = path.join(current, entry.name);
      if (entry.isDirectory()) pending.push(target);
      if (!entry.isFile() || !/\.(?:ts|tsx|vue|js|jsx)$/.test(entry.name)) continue;
      assert.ok(
        !fs.readFileSync(target, 'utf8').includes('formal-route-manifest'),
        `runtime source imports the acceptance manifest: ${path.relative(root, target)}`,
      );
    }
  }
}

const tests = [
  testCurrentManifest,
  testRepeatedGenerationIsByteIdentical,
  testDriftAndRewrite,
  testMissingViewFails,
  testDuplicateNameFails,
  testDuplicatePathFails,
  testNestedDemoMockTestDirectoriesAreExcluded,
  testManifestIsNotRuntimeImported,
];

for (const test of tests) {
  test();
  console.log(`PASS ${test.name}`);
}
console.log(`Formal route manifest tests passed: ${tests.length}/${tests.length}`);
