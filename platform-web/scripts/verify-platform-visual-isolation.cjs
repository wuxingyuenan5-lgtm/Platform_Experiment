'use strict';

const net = require('node:net');
const path = require('node:path');

const service = process.argv[2];
const expected = {
  frontend: { port: Number(process.env.PLATFORM_VISUAL_FRONTEND_PORT || 4473) },
  backend: { port: Number(process.env.PLATFORM_VISUAL_BACKEND_PORT || 8400) },
  runtime: { port: Number(process.env.PLATFORM_VISUAL_RUNTIME_PORT || 8401) },
}[service];

function fail(message) {
  console.error(`[platform-visual-isolation] ${message}`);
  process.exitCode = 1;
}

function assertPathUnderE2eRoot(name) {
  const root = process.env.PLATFORM_VISUAL_E2E_ROOT;
  const value = process.env[name];
  const resolvedRoot = root && path.resolve(root);
  const resolvedValue = value && path.resolve(value);
  if (
    !resolvedRoot ||
    !resolvedValue ||
    (resolvedValue !== resolvedRoot && !resolvedValue.startsWith(`${resolvedRoot}${path.sep}`))
  ) {
    fail(`${name} must point inside PLATFORM_VISUAL_E2E_ROOT`);
  }
}

function assertCommonEnvironment() {
  if (process.env.PLATFORM_VISUAL_E2E_RUN === undefined) {
    fail('PLATFORM_VISUAL_E2E_RUN is required');
  }
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(process.env.PLATFORM_VISUAL_E2E_RUN || '')) {
    fail('PLATFORM_VISUAL_E2E_RUN must be a simple isolated run name');
  }
  if (process.env.PYTHON_DOTENV_DISABLED !== '1') {
    fail(
      'PYTHON_DOTENV_DISABLED=1 is required to keep repository .env files out of the test process',
    );
  }
}

function assertBackendEnvironment() {
  assertCommonEnvironment();
  if (process.env.VG_ENVIRONMENT !== 'test' || process.env.VG_AUTH_MODE !== 'development') {
    fail('backend must use VG_ENVIRONMENT=test and VG_AUTH_MODE=development');
  }
  if (
    process.env.VG_LIVE_TRADING_ENABLED !== 'false' ||
    process.env.VG_RESEARCH_REFRESH_ENABLED !== 'false'
  ) {
    fail('backend live trading and research refresh must both be disabled');
  }
  assertPathUnderE2eRoot('VG_DATABASE_PATH');
  assertPathUnderE2eRoot('VG_AVATAR_DATA_DIRECTORY');
  assertPathUnderE2eRoot('VG_OPERATIONS_BACKUP_ROOT');
  assertPathUnderE2eRoot('VG_OPERATIONS_RESTORE_ROOT');
}

function assertRuntimeEnvironment() {
  assertCommonEnvironment();
  if (
    process.env.VG_RUNTIME_ENVIRONMENT !== 'test' ||
    process.env.VG_RUNTIME_GATEWAY_NAME !== 'fake'
  ) {
    fail('runtime must use VG_RUNTIME_ENVIRONMENT=test and VG_RUNTIME_GATEWAY_NAME=fake');
  }
  if (process.env.VG_RUNTIME_LIVE_WRITE_ENABLED !== 'false') {
    fail('runtime live writes must be disabled');
  }
  assertPathUnderE2eRoot('VG_RUNTIME_JOURNAL_PATH');
}

function assertPortAvailable(port) {
  if (!Number.isInteger(port) || port < 1024 || port > 65535) {
    fail(`invalid isolated port: ${port}`);
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const probe = net.createServer();
    probe.once('error', (error) => {
      if (error.code === 'EADDRINUSE') {
        fail(`port ${port} is already occupied; refusing to reuse an existing server`);
      } else {
        fail(`cannot validate port ${port}: ${error.message}`);
      }
      resolve();
    });
    probe.listen(port, '127.0.0.1', () => probe.close(resolve));
  });
}

async function main() {
  if (!expected) {
    fail('usage: node verify-platform-visual-isolation.cjs <frontend|backend|runtime>');
    return;
  }
  if (service === 'backend') assertBackendEnvironment();
  if (service === 'runtime') assertRuntimeEnvironment();
  if (service === 'frontend') assertCommonEnvironment();
  await assertPortAvailable(expected.port);
  if (process.exitCode) return;
  console.log(`[platform-visual-isolation] ${service} identity and port ${expected.port} verified`);
}

main().catch((error) => {
  fail(error instanceof Error ? error.message : String(error));
});
