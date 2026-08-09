const fs = require('fs');
const path = require('path');

const { chromium } = require(path.join(process.cwd(), 'node_modules', '@playwright', 'test'));

const origin = 'http://127.0.0.1:4373';
const outDir = path.join(process.cwd(), 'test-results', 'final-closeout');
fs.mkdirSync(outDir, { recursive: true });

const routes = [
  { name: '首页', hash: '/home/index', expect: ['全球变量'] },
  { name: '宏观日历', hash: '/news-calendar/macro', expect: ['宏观日历'] },
  { name: '新闻整理', hash: '/news-calendar/news', expect: ['新闻整理', '美股'] },
  { name: '理财信息', hash: '/news-calendar/wealth', expect: ['理财信息', '期限'] },
  { name: '宏观看板', hash: '/hedge-board/macro', expect: ['宏观市场明细'] },
  { name: '全球看板', hash: '/hedge-board/global', expect: ['全球'] },
  { name: '商品看板', hash: '/hedge-board/gold', expect: ['商品市场明细'] },
  { name: '加密看板', hash: '/hedge-board/crypto', expect: ['加密市场明细'] },
  { name: 'A股看板', hash: '/hedge-board/a-share', expect: ['A股', '市场明细'] },
  { name: '美股看板', hash: '/hedge-board/us', expect: ['美股'] },
  { name: '策略管理', hash: '/strategy/management', expect: ['资费', '跨所价差', '海内外价差'] },
  { name: '资费', hash: '/strategy/platform?desk=funding', expect: ['资费'] },
  {
    name: '跨所价差行情分析',
    hash: '/strategy/platform?desk=crossSpread',
    expect: ['跨所价差'],
  },
  {
    name: '跨所价差交易执行',
    hash: '/strategy/platform?desk=crossSpread',
    section: '交易执行',
    expect: ['交易执行', '标的', '执行指令'],
  },
  {
    name: '海内外价差行情分析',
    hash: '/strategy/platform?desk=domesticOverseas',
    expect: ['海内外价差'],
  },
  {
    name: '海内外价差交易执行',
    hash: '/strategy/platform?desk=domesticOverseas',
    section: '交易执行',
    expect: ['资产水平（CNY）', '仓位平衡', '国内交易腿', '海外交易腿'],
  },
  { name: '风控详情', hash: '/risk/detail', expect: ['风险总览', '风险限额'] },
  { name: '金融AI', hash: '/financial-ai/index', expect: ['研究问题', '分析结果'] },
  { name: '用户管理', hash: '/user/list', expect: ['用户'] },
  { name: '个人账号', hash: '/account/index', expect: ['个人账号'] },
];

function isExternal(url) {
  try {
    const parsed = new URL(url);
    return parsed.origin !== origin;
  } catch {
    return false;
  }
}

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for authenticated E2E checks`);
  return value;
}

async function login(page) {
  await page.goto(`${origin}/index.html#/login`, { waitUntil: 'domcontentloaded' });
  await page.getByPlaceholder(/账号|账户|请输入账号/).fill(requiredEnv('E2E_CEO_USERNAME'));
  await page.getByPlaceholder(/密码|请输入密码/).fill(requiredEnv('E2E_CEO_PASSWORD'));
  const response = page.waitForResponse((item) => item.url().endsWith('/api/v1/auth/login'));
  await page.getByRole('button', { name: /登录/ }).click();
  if (!(await response).ok()) throw new Error('login failed');
  await page.waitForURL((url) => !url.hash.includes('/login'), { timeout: 20_000 });
  await page.waitForFunction(() => (document.body.innerText || '').includes('全球变量'), {
    timeout: 20_000,
  });
  await page.waitForTimeout(1_000);
}

function assertNoEngineeringCopy(text, label) {
  const forbidden =
    /Provider|Owner|Sample|Non-actionable|Live Write|static_design|result_unknown|actionable=false|正式组件|旧版恢复|恢复中|示例策略不可启停|Prompt|Token|模型名|数据未配置|Provider 未配置/;
  if (forbidden.test(text)) throw new Error(`${label} exposes engineering copy`);
}

async function checkRoute(page, route, matrix, externalFailures) {
  const localErrors = [];
  const onPageError = (error) => localErrors.push(`pageerror:${error.message}`);
  const onConsole = (message) => {
    if (message.type() === 'error') localErrors.push(`console:${message.text()}`);
  };
  const onRequestFailed = (request) => {
    const url = request.url();
    if (isExternal(url)) {
      externalFailures.push(`${route.name}: ${url}`);
      return;
    }
    localErrors.push(`requestfailed:${url}:${request.failure()?.errorText || ''}`);
  };
  const onResponse = (response) => {
    const url = response.url();
    const status = response.status();
    if ((status === 404 || status >= 500) && !isExternal(url)) {
      localErrors.push(`http:${status}:${url}`);
    }
  };
  const onRequest = (request) => {
    const url = request.url();
    if (/\/undefined\/|\/null\//.test(url)) localErrors.push(`bad-url:${url}`);
  };

  page.on('pageerror', onPageError);
  page.on('console', onConsole);
  page.on('requestfailed', onRequestFailed);
  page.on('response', onResponse);
  page.on('request', onRequest);
  try {
    await page.goto(`${origin}/index.html#${route.hash}`, { waitUntil: 'domcontentloaded' });
    await page.waitForURL((url) => url.hash === `#${route.hash}`, { timeout: 8_000 });
    await page
      .waitForFunction(
        (expected) => {
          const text = document.body.innerText || '';
          const main =
            document.querySelector('main') ||
            document.querySelector('.ant-layout-content') ||
            document.body;
          return (
            expected.some((item) => text.includes(item)) &&
            main.getBoundingClientRect().height >= 80
          );
        },
        route.expect,
        { timeout: 8_000 },
      )
      .catch(() => undefined);
    if (route.section) {
      await page.locator('.section-switcher').getByRole('button', { name: route.section }).click();
      await page.waitForTimeout(600);
    }
    const result = await page.evaluate(() => {
      const text = document.body.innerText || '';
      const doc = document.documentElement;
      const scrollHost = document.scrollingElement || doc;
      const main =
        document.querySelector('main') ||
        document.querySelector('.ant-layout-content') ||
        document.body;
      const rect = main.getBoundingClientRect();
      return {
        text,
        textLength: text.trim().length,
        overflowX: doc.scrollWidth - doc.clientWidth,
        scrollHeight: scrollHost.scrollHeight,
        clientHeight: scrollHost.clientHeight,
        mainHeight: rect.height,
      };
    });
    for (const item of route.expect) {
      if (!result.text.includes(item)) localErrors.push(`missing:${item}`);
    }
    if (result.textLength < 20 || result.mainHeight < 80) localErrors.push('blank-page');
    if (result.overflowX > 2) localErrors.push(`horizontal-overflow:${result.overflowX}`);
    assertNoEngineeringCopy(result.text, route.name);
    matrix.push({
      route: route.name,
      hash: route.hash,
      url: page.url(),
      status: localErrors.length ? 'failed' : 'passed',
      textLength: result.textLength,
      textSample: result.text.slice(0, 120),
      scrollHeight: result.scrollHeight,
      clientHeight: result.clientHeight,
      mainHeight: result.mainHeight,
      errors: localErrors,
    });
    if (localErrors.length) throw new Error(`${route.name}: ${localErrors.join(' | ')}`);
  } finally {
    page.off('pageerror', onPageError);
    page.off('console', onConsole);
    page.off('requestfailed', onRequestFailed);
    page.off('response', onResponse);
    page.off('request', onRequest);
  }
}

(async () => {
  const matrix = [];
  const externalFailures = [];
  try {
    for (const route of routes) {
      const browser = await chromium.launch({ headless: true });
      const context = await browser.newContext({
        viewport: { width: 1366, height: 768 },
        locale: 'zh-CN',
      });
      const page = await context.newPage();
      try {
        await login(page);
        await checkRoute(page, route, matrix, externalFailures);
      } finally {
        await browser.close();
      }
    }
  } finally {
    fs.writeFileSync(
      path.join(outDir, 'route-matrix.json'),
      JSON.stringify({ matrix, externalFailures: [...new Set(externalFailures)] }, null, 2),
      'utf8',
    );
  }
  console.log(`final closeout route checks passed, routes=${routes.length}`);
  if (externalFailures.length) {
    console.log(`external resource failures recorded=${new Set(externalFailures).size}`);
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
