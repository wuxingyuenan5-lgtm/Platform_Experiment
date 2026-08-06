'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');
const ts = require('typescript');

const webRoot = path.resolve(__dirname, '..');
const contractsPath = path.join(
  webRoot,
  'src/views/risk/profile/security/contracts.ts',
);
const modulesPath = path.join(webRoot, 'src/views/risk/profile/security/modules.tsx');
const regexPath = path.join(webRoot, 'src/utils/regex.ts');

function loadTypeScriptModule(filePath) {
  const source = fs.readFileSync(filePath, 'utf8');
  const transpiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
      strict: true,
    },
    fileName: filePath,
    reportDiagnostics: true,
  });
  const errors = (transpiled.diagnostics || []).filter(
    (diagnostic) => diagnostic.category === ts.DiagnosticCategory.Error,
  );
  assert.equal(errors.length, 0, `TypeScript transpilation failed for ${filePath}`);

  const loaded = new Module(filePath, module);
  loaded.filename = filePath;
  loaded.paths = Module._nodeModulePaths(path.dirname(filePath));
  loaded._compile(transpiled.outputText, filePath);
  return loaded.exports;
}

const contracts = loadTypeScriptModule(contractsPath);
const regex = loadTypeScriptModule(regexPath);
const moduleSource = fs.readFileSync(modulesPath, 'utf8');

test('Password submits oldPw, newPw1, newPw2 and code without rewriting fields', () => {
  assert.deepEqual(
    contracts.buildPasswordPayload({
      oldPw: 'old-password',
      newPw1: 'new-password-1',
      newPw2: 'new-password-1',
      code: '123456',
    }),
    {
      oldPw: 'old-password',
      newPw1: 'new-password-1',
      newPw2: 'new-password-1',
      code: '123456',
    },
  );
  assert.match(moduleSource, /await loginChangepw\(payload\)/);
});

test('Password failure restores loading and remains retryable', async () => {
  const loadingStates = [];
  await assert.rejects(
    contracts.executeWithLoading(
      (loading) => loadingStates.push(loading),
      async () => {
        throw new Error('request failed');
      },
    ),
    /request failed/,
  );
  assert.deepEqual(loadingStates, [true, false]);
});

test('Phone BIND payload keeps phone action and bind discriminator', () => {
  assert.deepEqual(contracts.buildPhonePayload(0, { newPhone: '13800138000', code: '111111' }), {
    newPhone: '13800138000',
    code: '111111',
    action: 'phone',
    operation: 'bind',
  });
});

test('Phone CHANGE payload keeps phone action and change discriminator', () => {
  assert.deepEqual(contracts.buildPhonePayload(1, { newPhone: '13900139000', code: '222222' }), {
    newPhone: '13900139000',
    code: '222222',
    action: 'phone',
    operation: 'change',
  });
});

test('Email payload keeps email action, operation and validation', () => {
  assert.deepEqual(contracts.buildEmailPayload(1, { newEmail: 'member@example.com', code: '333333' }), {
    newEmail: 'member@example.com',
    code: '333333',
    action: 'email',
    operation: 'change',
  });
  assert.equal(regex.validateEmail('member@example.com'), true);
  assert.equal(regex.validateEmail('invalid-email'), false);
  assert.match(moduleSource, /validator: validateEmail/);
});

test('Feishu payload uses feishu action rather than password action', () => {
  assert.deepEqual(contracts.buildFeishuPayload(0, { url: 'https://open.feishu.cn/hook', code: '444444' }), {
    url: 'https://open.feishu.cn/hook',
    code: '444444',
    action: 'feishu',
    operation: 'bind',
  });
  assert.doesNotMatch(moduleSource, /action:\s*['"]changePassword['"]/);
});

test('Binding submissions restore loading after completion', async () => {
  const loadingStates = [];
  const result = await contracts.executeWithLoading(
    (loading) => loadingStates.push(loading),
    () => 'submitted',
  );
  assert.equal(result, 'submitted');
  assert.deepEqual(loadingStates, [true, false]);
});

test('Closing a modal resets its form and opening does not', () => {
  let resets = 0;
  contracts.resetFormWhenClosed(true, () => {
    resets += 1;
  });
  assert.equal(resets, 0);
  contracts.resetFormWhenClosed(false, () => {
    resets += 1;
  });
  assert.equal(resets, 1);
  assert.match(moduleSource, /resetFormWhenClosed\(open,/);
});

test('Security modules contain no broad component any or TypeScript suppression', () => {
  for (const forbidden of [
    /Modal\s+as\s+any/,
    /Form\s+as\s+any/,
    /Form\.Item\s+as\s+any/,
    /Input\s+as\s+any/,
    /Input\.Password\s+as\s+any/,
    /@ts-ignore/,
    /@ts-nocheck/,
  ]) {
    assert.doesNotMatch(moduleSource, forbidden);
  }
});
