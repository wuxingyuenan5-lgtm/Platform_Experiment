'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');
const {
  findChangedFileDiagnostics,
  findNewDiagnostics,
  parseDiagnostics,
} = require('./full-typecheck-core.cjs');

const repoRoot = path.resolve('/repo');
const webRoot = path.join(repoRoot, 'platform-web');

function diagnosticOutput(file, line, column, code, message) {
  return `${file}(${line},${column}): error TS${code}: ${message}`;
}

test('parses and normalizes vue-tsc diagnostics', () => {
  const diagnostics = parseDiagnostics(
    diagnosticOutput('src/views/example.vue', 12, 4, 2322, 'Type mismatch.'),
    webRoot,
    repoRoot,
  );

  assert.deepEqual(diagnostics, [
    {
      path: 'platform-web/src/views/example.vue',
      line: 12,
      column: 4,
      code: 'TS2322',
      message: 'Type mismatch.',
    },
  ]);
});

test('allows only diagnostics proven to exist in the base', () => {
  const baseline = parseDiagnostics(
    diagnosticOutput('src/legacy.ts', 1, 1, 7006, 'Implicit any.'),
    webRoot,
    repoRoot,
  );
  const head = parseDiagnostics(
    [
      diagnosticOutput('src/legacy.ts', 1, 1, 7006, 'Implicit any.'),
      diagnosticOutput('src/new.ts', 2, 3, 2322, 'Type mismatch.'),
    ].join('\n'),
    webRoot,
    repoRoot,
  );

  assert.deepEqual(findNewDiagnostics(baseline, head).map((item) => item.path), [
    'platform-web/src/new.ts',
  ]);
});

test('rejects diagnostics in any file changed by the pull request', () => {
  const head = parseDiagnostics(
    diagnosticOutput('src/changed.ts', 3, 5, 2345, 'Invalid argument.'),
    webRoot,
    repoRoot,
  );

  assert.equal(
    findChangedFileDiagnostics(head, ['platform-web/src/changed.ts']).length,
    1,
  );
});
