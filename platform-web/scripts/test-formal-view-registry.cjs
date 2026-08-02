#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  ViewRegistryError,
  checkRegistry,
  generatedBytes,
  registryEntries,
  writeRegistry,
} = require('./formal-view-registry.cjs');

const root = path.resolve(__dirname, '..');
const output = path.join(root, 'src', 'router', 'viewRegistry.generated.ts');

function copyFixture() {
  const fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'formal-view-registry-'));
  fs.cpSync(path.join(root, 'src', 'router'), path.join(fixture, 'src', 'router'), {
    recursive: true,
  });
  fs.cpSync(path.join(root, 'src', 'views'), path.join(fixture, 'src', 'views'), {
    recursive: true,
  });
  return fixture;
}

function testCurrentRegistry() {
  const result = checkRegistry({ root, output });
  assert.ok(result.entries.length >= 15);
}

function testRepeatedGenerationIsByteIdentical() {
  assert.deepEqual(generatedBytes({ root }), generatedBytes({ root }));
}

function testDriftAndRewrite() {
  const fixture = copyFixture();
  try {
    const candidate = path.join(fixture, 'viewRegistry.generated.ts');
    writeRegistry({ root: fixture, output: candidate });
    checkRegistry({ root: fixture, output: candidate });
    fs.appendFileSync(candidate, '// drift\n', 'utf8');
    assert.throws(
      () => checkRegistry({ root: fixture, output: candidate }),
      (error) => error instanceof ViewRegistryError && /drift.*--write/.test(error.message),
    );
    writeRegistry({ root: fixture, output: candidate });
    checkRegistry({ root: fixture, output: candidate });
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
}

function testMissingViewFails() {
  const fixture = copyFixture();
  try {
    const target = path.join(fixture, 'src', 'views', 'account', 'index.vue');
    fs.rmSync(target);
    assert.throws(
      () => registryEntries({ root: fixture }),
      (error) => error instanceof ViewRegistryError && /missing View/.test(error.message),
    );
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
}

function testForbiddenViewFails() {
  const fixture = copyFixture();
  try {
    const view = path.join(fixture, 'src', 'views', 'demo', 'Hidden.vue');
    fs.mkdirSync(path.dirname(view), { recursive: true });
    fs.writeFileSync(view, '<template />\n', 'utf8');
    const route = path.join(fixture, 'src', 'router', 'routes', 'modules', 'forbidden.ts');
    fs.writeFileSync(route, "const component = () => import('@/views/demo/Hidden.vue');\n", 'utf8');
    assert.throws(
      () => registryEntries({ root: fixture }),
      (error) => error instanceof ViewRegistryError && /forbidden View key/.test(error.message),
    );
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
}

function testRuntimeUsesRegistryWithoutGlobOrIgnore() {
  const helper = fs.readFileSync(
    path.join(root, 'src', 'router', 'helper', 'routeHelper.ts'),
    'utf8',
  );
  assert.ok(helper.includes('resolveViewComponent'));
  assert.ok(!helper.includes('import.meta.glob'));
  assert.ok(!helper.includes('@ts-nocheck'));
}

const tests = [
  testCurrentRegistry,
  testRepeatedGenerationIsByteIdentical,
  testDriftAndRewrite,
  testMissingViewFails,
  testForbiddenViewFails,
  testRuntimeUsesRegistryWithoutGlobOrIgnore,
];

for (const test of tests) {
  test();
  console.log(`PASS ${test.name}`);
}
console.log(`Formal View Registry tests passed: ${tests.length}/${tests.length}`);
