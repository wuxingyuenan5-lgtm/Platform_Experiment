import path from 'node:path';

import { defineConfig, devices } from '@playwright/test';

const frontendRoot = process.cwd();
const repositoryRoot = path.resolve(frontendRoot, '..');
const backendRoot = path.join(repositoryRoot, 'platform-backend');
const runtimeRoot = path.join(repositoryRoot, 'execution-runtime');
const e2eRoot = path.join(repositoryRoot, '.e2e', 'platform-visual');
const frontendOrigin = 'http://127.0.0.1:4373';
const backendOrigin = 'http://127.0.0.1:8000';
const runtimeOrigin = 'http://127.0.0.1:8100';
const backendPython = process.env.PLATFORM_VISUAL_BACKEND_PYTHON || 'python';
const runtimePython = process.env.PLATFORM_VISUAL_RUNTIME_PYTHON || 'python';
const inheritedEnvironment = Object.fromEntries(
  Object.entries(process.env).filter(
    (entry): entry is [string, string] => typeof entry[1] === 'string',
  ),
);

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
  outputDir: 'test-results/platform-visual',
  use: {
    ...devices['Desktop Chrome'],
    actionTimeout: 20_000,
    baseURL: frontendOrigin,
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    colorScheme: 'light',
    reducedMotion: 'reduce',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: [
    {
      command: `${runtimePython} -m uvicorn app.main:app --host 127.0.0.1 --port 8100`,
      cwd: runtimeRoot,
      url: `${runtimeOrigin}/health`,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        ...inheritedEnvironment,
        VG_RUNTIME_ENVIRONMENT: 'test',
        VG_RUNTIME_JOURNAL_PATH: path.join(e2eRoot, 'runtime.db'),
        VG_RUNTIME_GATEWAY_NAME: 'fake',
        VG_RUNTIME_LIVE_WRITE_ENABLED: 'false',
      },
    },
    {
      command:
        `${backendPython} scripts/seed_platform_visual_e2e.py && ` +
        `${backendPython} -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: backendRoot,
      url: `${backendOrigin}/health`,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        ...inheritedEnvironment,
        PLATFORM_VISUAL_E2E_RESET: '1',
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
      },
    },
    {
      command: 'pnpm sync:trading-tools && pnpm exec vite --host 127.0.0.1',
      cwd: frontendRoot,
      url: `${frontendOrigin}/login`,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        ...inheritedEnvironment,
        VITE_PLATFORM_API_BASE_URL: `${backendOrigin}/api/v1`,
      },
    },
  ],
});
