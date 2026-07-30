import path from 'node:path';

import { defineConfig, devices } from '@playwright/test';

const frontendRoot = process.cwd();
const repositoryRoot = path.resolve(frontendRoot, '..');
const backendRoot = path.join(repositoryRoot, 'platform-backend');
const e2eRoot = path.join(repositoryRoot, '.e2e', 'user-system', 'hedge-board');
const frontendOrigin = 'http://127.0.0.1:4373';
const backendOrigin = 'http://127.0.0.1:8000';
const inheritedEnvironment = Object.fromEntries(
  Object.entries(process.env).filter((entry): entry is [string, string] => typeof entry[1] === 'string'),
);

export default defineConfig({
  testDir: './e2e/hedge-board',
  fullyParallel: false,
  workers: 1,
  timeout: 150_000,
  expect: {
    timeout: 15_000,
  },
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [
        ['list'],
        ['html', { open: 'never', outputFolder: 'playwright-report/hedge-board' }],
      ]
    : [['list']],
  outputDir: 'test-results/hedge-board',
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
      command:
        'python scripts/seed_user_system_e2e.py && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      cwd: backendRoot,
      url: `${backendOrigin}/health`,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        ...inheritedEnvironment,
        USER_SYSTEM_E2E_RESET: '1',
        VG_ENVIRONMENT: 'test',
        VG_AUTH_MODE: 'development',
        VG_DATABASE_PATH: path.join(e2eRoot, 'platform.db'),
        VG_AVATAR_DATA_DIRECTORY: path.join(e2eRoot, 'avatars'),
        VG_OPERATIONS_BACKUP_ROOT: path.join(e2eRoot, 'backups'),
        VG_OPERATIONS_RESTORE_ROOT: path.join(e2eRoot, 'restore-drills'),
        VG_CORS_ORIGINS: frontendOrigin,
        VG_BROWSER_SESSIONS_ENABLED: 'true',
        VG_LIVE_TRADING_ENABLED: 'false',
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
      env: inheritedEnvironment,
    },
  ],
});
