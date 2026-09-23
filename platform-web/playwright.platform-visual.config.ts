import path from 'node:path';
import { randomUUID } from 'node:crypto';

import { defineConfig, devices } from '@playwright/test';

const frontendRoot = process.cwd();
const repositoryRoot = path.resolve(frontendRoot, '..');
const backendRoot = path.join(repositoryRoot, 'platform-api');
const runtimeRoot = path.join(repositoryRoot, 'execution-runtime');
const run = process.env.PLATFORM_VISUAL_E2E_RUN || randomUUID();
if (!/^[A-Za-z0-9_-]{1,64}$/.test(run)) {
  throw new Error('PLATFORM_VISUAL_E2E_RUN must be a simple isolated run name');
}
const e2eRoot = path.join(repositoryRoot, '.e2e', 'platform-visual', run);
const frontendPort = Number(process.env.PLATFORM_VISUAL_FRONTEND_PORT || 4473);
const backendPort = Number(process.env.PLATFORM_VISUAL_BACKEND_PORT || 8400);
const runtimePort = Number(process.env.PLATFORM_VISUAL_RUNTIME_PORT || 8401);
const frontendOrigin = `http://127.0.0.1:${frontendPort}`;
const backendOrigin = `http://127.0.0.1:${backendPort}`;
const runtimeOrigin = `http://127.0.0.1:${runtimePort}`;
const backendPython =
  process.env.PLATFORM_VISUAL_BACKEND_PYTHON ||
  path.join(backendRoot, '.venv', 'Scripts', 'python.exe');
const runtimePython =
  process.env.PLATFORM_VISUAL_RUNTIME_PYTHON ||
  path.join(runtimeRoot, '.venv', 'Scripts', 'python.exe');
const sharedPassword = process.env.E2E_SHARED_PASSWORD || 'Isolated-E2E-2026#only';

// Playwright merges webServer.env with the runner environment. Remove inherited
// platform settings before constructing the test servers so repository .env or
// operator shells cannot silently override the explicit test values below.
for (const key of Object.keys(process.env)) {
  if (key.startsWith('VG_') || key.startsWith('VITE_')) {
    delete process.env[key];
  }
}

function assertPort(value: number, name: string): number {
  if (!Number.isInteger(value) || value < 1024 || value > 65535) {
    throw new Error(`${name} must be an integer between 1024 and 65535`);
  }
  return value;
}

function assertPortsAreDistinct(): void {
  const ports = new Map([
    [frontendPort, 'frontend'],
    [backendPort, 'backend'],
    [runtimePort, 'runtime'],
  ]);
  if (ports.size !== 3) {
    throw new Error('Platform visual E2E frontend, backend and runtime ports must be distinct');
  }
  for (const [port, name] of ports) {
    if ([4373, 8000, 8100].includes(port)) {
      throw new Error(`${name} port ${port} is reserved by the normal platform services`);
    }
  }
}

assertPort(frontendPort, 'PLATFORM_VISUAL_FRONTEND_PORT');
assertPort(backendPort, 'PLATFORM_VISUAL_BACKEND_PORT');
assertPort(runtimePort, 'PLATFORM_VISUAL_RUNTIME_PORT');
assertPortsAreDistinct();

const processEnvironment = {
  PATH: process.env.PATH,
  PATHEXT: process.env.PATHEXT,
  SystemRoot: process.env.SystemRoot,
  SYSTEMROOT: process.env.SYSTEMROOT,
  TEMP: process.env.TEMP,
  TMP: process.env.TMP,
  VIRTUAL_ENV: process.env.VIRTUAL_ENV,
  CI: process.env.CI,
  PLATFORM_VISUAL_BACKEND_PYTHON: backendPython,
  PLATFORM_VISUAL_RUNTIME_PYTHON: runtimePython,
  E2E_SHARED_PASSWORD: sharedPassword,
  PLATFORM_VISUAL_E2E_RUN: run,
  PLATFORM_VISUAL_E2E_ROOT: e2eRoot,
  PLATFORM_VISUAL_FRONTEND_PORT: String(frontendPort),
  PLATFORM_VISUAL_BACKEND_PORT: String(backendPort),
  PLATFORM_VISUAL_RUNTIME_PORT: String(runtimePort),
  PLATFORM_VISUAL_RUNTIME_ORIGIN: runtimeOrigin,
  PLATFORM_VISUAL_E2E_RESET: '0',
  PYTHON_DOTENV_DISABLED: '1',
};
const testEnvironment = Object.fromEntries(
  Object.entries(processEnvironment).filter(
    (entry): entry is [string, string] => typeof entry[1] === 'string',
  ),
);
process.env.PLATFORM_VISUAL_FRONTEND_ORIGIN = frontendOrigin;
process.env.PLATFORM_VISUAL_BACKEND_ORIGIN = backendOrigin;
process.env.PLATFORM_VISUAL_RUNTIME_ORIGIN = runtimeOrigin;
process.env.PLATFORM_VISUAL_E2E_RUN = run;
process.env.PLATFORM_VISUAL_E2E_ROOT = e2eRoot;
process.env.E2E_SHARED_PASSWORD = sharedPassword;

export default defineConfig({
  testDir: './e2e/platform-visual',
  fullyParallel: false,
  workers: 1,
  timeout: 240_000,
  expect: {
    timeout: 20_000,
  },
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [['list'], ['html', { open: 'never', outputFolder: 'playwright-report/platform-visual' }]]
    : [['list']],
  outputDir: `test-results/platform-visual/${run}`,
  use: {
    ...devices['Desktop Chrome'],
    actionTimeout: 20_000,
    baseURL: frontendOrigin,
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    colorScheme: 'light',
    contextOptions: { reducedMotion: 'reduce' },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: [
    {
      command:
        `node "${path.join(
          frontendRoot,
          'scripts',
          'verify-platform-visual-isolation.cjs',
        )}" runtime && ` +
        `"${runtimePython}" "${path.join(
          frontendRoot,
          'scripts',
          'run-platform-visual-service.py',
        )}" runtime`,
      cwd: runtimeRoot,
      url: `${runtimeOrigin}/health`,
      timeout: 120_000,
      reuseExistingServer: false,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        ...testEnvironment,
        VG_RUNTIME_ENVIRONMENT: 'test',
        VG_RUNTIME_JOURNAL_PATH: path.join(e2eRoot, 'runtime.db'),
        VG_RUNTIME_GATEWAY_NAME: 'fake',
        VG_RUNTIME_LIVE_WRITE_ENABLED: 'false',
        VG_RUNTIME_CREDENTIAL_REFS: '',
        VG_RUNTIME_BYBIT_CREDENTIAL_REF: '',
        VG_RUNTIME_MT5_CREDENTIAL_REF: '',
        VG_RUNTIME_BYBIT_ACCOUNT_IDS: '',
        VG_RUNTIME_MT5_ACCOUNT_IDS: '',
        VG_RUNTIME_BYBIT_DEMO_MODE: 'false',
        PYTHON_DOTENV_DISABLED: '1',
      },
    },
    {
      command:
        `node "${path.join(
          frontendRoot,
          'scripts',
          'verify-platform-visual-isolation.cjs',
        )}" backend && ` +
        `"${backendPython}" "${path.join(
          frontendRoot,
          'scripts',
          'run-platform-visual-service.py',
        )}" backend`,
      cwd: backendRoot,
      url: `${backendOrigin}/health`,
      timeout: 120_000,
      reuseExistingServer: false,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        ...testEnvironment,
        VG_ENVIRONMENT: 'test',
        VG_AUTH_MODE: 'development',
        VG_DATABASE_PATH: path.join(e2eRoot, 'platform.db'),
        VG_AVATAR_DATA_DIRECTORY: path.join(e2eRoot, 'avatars'),
        VG_OPERATIONS_BACKUP_ROOT: path.join(e2eRoot, 'backups'),
        VG_OPERATIONS_RESTORE_ROOT: path.join(e2eRoot, 'restore-drills'),
        VG_RUNTIME_BASE_URL: runtimeOrigin,
        VG_CORS_ORIGINS: frontendOrigin,
        VG_BROWSER_SESSIONS_ENABLED: 'true',
        VG_LIVE_TRADING_ENABLED: 'false',
        VG_DEFAULT_TRADING_ENVIRONMENT: 'simulation',
        VG_RESEARCH_REFRESH_ENABLED: 'false',
        VG_CROSS_SPREAD_EXIT_MONITOR_ENABLED: 'false',
        VG_AUTH_CREDENTIALS_JSON: '[]',
        VG_FINANCIAL_AI_ACCESS_KEY_SHA256: '',
        VG_BYBIT_MT5_FUNDING_URL: 'http://127.0.0.1:1',
        PYTHON_DOTENV_DISABLED: '1',
      },
    },
    {
      command:
        `node "${path.join(
          frontendRoot,
          'scripts',
          'verify-platform-visual-isolation.cjs',
        )}" frontend && ` +
        `corepack pnpm sync:trading-tools && corepack pnpm exec vite --host 127.0.0.1 --port ${frontendPort} --strictPort`,
      cwd: frontendRoot,
      url: `${frontendOrigin}/`,
      timeout: 120_000,
      reuseExistingServer: false,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        ...testEnvironment,
        VITE_PLATFORM_API_BASE_URL: `${backendOrigin}/api/v1`,
        VITE_PLATFORM_BACKEND_TARGET: backendOrigin,
      },
    },
  ],
});
