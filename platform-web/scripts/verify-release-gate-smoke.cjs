const fs = require('fs');
const path = require('path');

const { chromium } = require(path.join(process.cwd(), 'node_modules', '@playwright', 'test'));

const origin = 'http://127.0.0.1:4373';
const outDir = path.join(process.cwd(), 'test-results', 'release-gate-smoke');
fs.mkdirSync(outDir, { recursive: true });

const pages = [
  { name: 'dashboard', hash: '/home/index', expect: ['\u5168\u7403\u53d8\u91cf'] },
  {
    name: 'settings',
    hash: '/settings/profile',
    expect: ['\u8d26\u6237\u4e0e\u504f\u597d', '\u670d\u52a1\u72b6\u6001'],
  },
  { name: 'monitor', hash: '/monitor/index', expect: ['\u76d1\u63a7'] },
  { name: 'finance', hash: '/finance/index', expect: ['\u8d22\u52a1'] },
  { name: 'data', hash: '/data/index', expect: ['\u6570\u636e'] },
  { name: 'notification', hash: '/notification/index', expect: ['\u6d88\u606f'] },
  {
    name: 'about',
    hash: '',
    expect: [],
    skipped: 'no formal route registered for src/views/sys/about/index.vue',
  },
];

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for authenticated E2E checks`);
  return value;
}

async function login(page) {
  await page.goto(`${origin}/index.html#/login`, { waitUntil: 'domcontentloaded' });
  await page
    .getByPlaceholder(/\u8d26\u53f7|\u8d26\u6237|\u8bf7\u8f93\u5165\u8d26\u53f7/)
    .fill(requiredEnv('E2E_CEO_USERNAME'));
  await page
    .getByPlaceholder(/\u5bc6\u7801|\u8bf7\u8f93\u5165\u5bc6\u7801/)
    .fill(requiredEnv('E2E_CEO_PASSWORD'));
  const response = page.waitForResponse((item) => item.url().endsWith('/api/v1/auth/login'));
  await page.getByRole('button', { name: /\u767b\u5f55/ }).click();
  if (!(await response).ok()) throw new Error('login failed');
  await page.waitForURL((url) => !url.hash.includes('/login'), { timeout: 20_000 });
  await page.waitForFunction(
    () => (document.body.innerText || '').includes('\u5168\u7403\u53d8\u91cf'),
    {
      timeout: 20_000,
    },
  );
}

async function checkPage(browser, item) {
  if (item.skipped) {
    return {
      page: item.name,
      hash: item.hash,
      status: 'skipped',
      reason: item.skipped,
      errors: [],
    };
  }

  const context = await browser.newContext({
    viewport: { width: 1366, height: 768 },
    locale: 'zh-CN',
  });
  const page = await context.newPage();
  const errors = [];

  try {
    await login(page);

    page.on('pageerror', (error) => errors.push(`pageerror:${error.message}`));
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(`console:${message.text()}`);
    });
    page.on('requestfailed', (request) => {
      errors.push(`requestfailed:${request.url()}:${request.failure()?.errorText || ''}`);
    });
    page.on('request', (request) => {
      const url = request.url();
      if (/\/undefined\/|\/null\//.test(url)) errors.push(`bad-url:${url}`);
    });
    page.on('response', (response) => {
      const status = response.status();
      if (status >= 400) errors.push(`http:${status}:${response.url()}`);
    });

    await page.goto(`${origin}/index.html#${item.hash}`, { waitUntil: 'domcontentloaded' });
    await page.waitForURL((url) => url.hash === `#${item.hash}`, { timeout: 8_000 });
    await page
      .waitForFunction(
        (expected) => {
          const text = document.body.innerText || '';
          const main =
            document.querySelector('main') ||
            document.querySelector('.ant-layout-content') ||
            document.body;
          return (
            expected.some((label) => text.includes(label)) &&
            main.getBoundingClientRect().height >= 80
          );
        },
        item.expect,
        { timeout: 8_000 },
      )
      .catch(() => undefined);

    const result = await page.evaluate(() => {
      const text = document.body.innerText || '';
      const main =
        document.querySelector('main') ||
        document.querySelector('.ant-layout-content') ||
        document.body;
      return {
        text,
        textLength: text.trim().length,
        mainHeight: main.getBoundingClientRect().height,
        url: location.href,
      };
    });

    for (const label of item.expect) {
      if (!result.text.includes(label)) errors.push(`missing:${label}`);
    }
    if (result.textLength < 20 || result.mainHeight < 80) errors.push('blank-page');

    return {
      page: item.name,
      hash: item.hash,
      url: result.url,
      status: errors.length ? 'failed' : 'passed',
      textLength: result.textLength,
      mainHeight: result.mainHeight,
      errors,
    };
  } finally {
    await context.close();
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const matrix = [];
  try {
    for (const item of pages) {
      const result = await checkPage(browser, item);
      matrix.push(result);
      if (result.status === 'failed') {
        throw new Error(`${result.page}: ${result.errors.join(' | ')}`);
      }
    }
  } finally {
    await browser.close();
    fs.writeFileSync(
      path.join(outDir, 'smoke-matrix.json'),
      JSON.stringify(matrix, null, 2),
      'utf8',
    );
  }
  console.log(
    `release gate smoke checks passed, checked=${
      matrix.filter((item) => item.status === 'passed').length
    }, skipped=${matrix.filter((item) => item.status === 'skipped').length}`,
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
