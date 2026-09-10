import path from 'node:path';
import { randomUUID } from 'node:crypto';

import { defineConfig, devices } from '@playwright/test';

const frontendRoot = process.cwd();
const repositoryRoot = path.resolve(frontendRoot, '..');
const backendRoot = path.join(repositoryRoot, 'platform-api');
process.env.HEDGE_BOARD_E2E_RUN ||= randomUUID();
process.env.E2E_CEO_PASSWORD ||= 'Isolated-E2E-2026#only';
const run = process.env.HEDGE_BOARD_E2E_RUN;
const e2eRoot = path.join(repositoryRoot, '.e2e', 'hedge-board', run);
const python = path.join(backendRoot, '.venv', 'Scripts', 'python.exe');
const frontendOrigin = 'http://127.0.0.1:4440';
const backendOrigin = 'http://127.0.0.1:8440';
const inheritedEnvironment = Object.fromEntries(
  Object.entries(process.env).filter(
    (entry): entry is [string, string] => typeof entry[1] === 'string',
  ),
);

export default defineConfig({
  testDir: './e2e/strategy',
  fullyParallel: false,
  workers: 1,
  timeout: 150_000,
  expect: {
    timeout: 15_000,
  },
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [['list'], ['html', { open: 'never', outputFolder: 'playwright-report/hedge-board' }]]
    : [['list']],
  outputDir: `test-results/hedge-board/${run}`,
  use: {
    ...devices['Desktop Chrome'],
    actionTimeout: 15_000,
    baseURL: frontendOrigin,
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: [
    {
      command: `"${path.join(
        repositoryRoot,
        'execution-runtime',
        '.venv',
        'Scripts',
        'python.exe',
      )}" -m uvicorn app.main:app --host 127.0.0.1 --port 8140`,
      cwd: path.join(repositoryRoot, 'execution-runtime'),
      url: 'http://127.0.0.1:8140/status',
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        ...inheritedEnvironment,
        VG_RUNTIME_GATEWAY_NAME: 'fake',
        VG_RUNTIME_ENVIRONMENT: 'test',
        VG_RUNTIME_LIVE_WRITE_ENABLED: 'false',
        VG_RUNTIME_JOURNAL_PATH: path.join(e2eRoot, 'runtime.db'),
      },
    },
    {
      command: `"${python}" -m uvicorn strategy_test_server:app --app-dir tests --host 127.0.0.1 --port 8440`,
      cwd: backendRoot,
      url: `${backendOrigin}/health`,
      timeout: 120_000,
      reuseExistingServer: false,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        ...inheritedEnvironment,
        PYTHONPATH: backendRoot,
        PYTHONIOENCODING: 'utf-8',
        VG_RESEARCH_REFRESH_ENABLED: 'false',
        VG_RUNTIME_BASE_URL: 'http://127.0.0.1:8140',
        VG_ENVIRONMENT: 'test',
        VG_AUTH_MODE: 'development',
        VG_DATABASE_PATH: path.join(e2eRoot, 'platform.db'),
        VG_AVATAR_DATA_DIRECTORY: path.join(e2eRoot, 'avatars'),
        VG_OPERATIONS_BACKUP_ROOT: path.join(e2eRoot, 'backups'),
        VG_OPERATIONS_RESTORE_ROOT: path.join(e2eRoot, 'restore-drills'),
        VG_CORS_ORIGINS: frontendOrigin,
        VG_BROWSER_SESSIONS_ENABLED: 'true',
        VG_SESSION_COOKIE_NAME: `vg_strategy_e2e_${run.replaceAll('-', '_')}`,
        // Lifecycle admission requires this Platform flag even for simulation.
        // Every executable binding above uses FakeGateway; Runtime Live Write stays false.
        VG_LIVE_TRADING_ENABLED: 'true',
      },
    },
    {
      command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 4440 --strictPort',
      cwd: frontendRoot,
      url: `${frontendOrigin}/index.html`,
      timeout: 120_000,
      reuseExistingServer: false,
      stdout: 'pipe',
      stderr: 'pipe',
      env: { ...inheritedEnvironment, CI: 'true', VITE_PLATFORM_BACKEND_TARGET: backendOrigin },
    },
  ],
});
