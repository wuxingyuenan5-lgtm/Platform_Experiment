const fs = require('fs');
const path = require('path');

const { chromium } = require(path.join(process.cwd(), 'node_modules', '@playwright', 'test'));

const origin = 'http://127.0.0.1:4373';
const outDir = path.join(process.cwd(), 'test-results', 'hedge-board-chart-heights');
fs.mkdirSync(outDir, { recursive: true });

const pages = [
  { route: '/hedge-board/macro', detail: '#macro-market', title: '宏观市场明细' },
  { route: '/hedge-board/gold', detail: '#gold-market', title: '商品市场明细' },
  { route: '/hedge-board/crypto', detail: '#crypto-market', title: '加密市场明细' },
];

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for authenticated E2E checks`);
  return value;
}

async function login(page) {
  await page.goto(`${origin}/#/login`, { waitUntil: 'domcontentloaded' });
  await page.getByPlaceholder(/账号|账户|请输入账号/).fill(requiredEnv('E2E_CEO_USERNAME'));
  await page.getByPlaceholder(/密码|请输入密码/).fill(requiredEnv('E2E_CEO_PASSWORD'));
  const response = page.waitForResponse((item) => item.url().endsWith('/api/v1/auth/login'));
  await page.getByRole('button', { name: /登录/ }).click();
  if (!(await response).ok()) throw new Error('login failed');
  await page.waitForURL((url) => !url.hash.includes('/login'), { timeout: 20_000 });
}

async function checkPage(page, item, mode) {
  await page.goto(`${origin}/#${item.route}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3500);
  const result = await page.evaluate(({ detail, title }) => {
    const visible = (element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return (
        rect.width > 0 &&
        rect.height > 0 &&
        style.visibility !== 'hidden' &&
        style.display !== 'none'
      );
    };
    const rect = (element) => {
      const r = element.getBoundingClientRect();
      return { top: r.top, bottom: r.bottom, height: r.height, width: r.width };
    };
    const candidates = [
      ...Array.from(document.querySelectorAll('*')),
      document.scrollingElement,
    ].filter(Boolean);
    const scrollHost =
      candidates
        .filter((element) => element.scrollHeight > element.clientHeight + 120)
        .sort((left, right) => right.scrollHeight - left.scrollHeight)[0] ||
      document.scrollingElement;
    const heightMismatches = Array.from(
      document.querySelectorAll(
        '.widget-frame[data-widget-height], .local-empty[data-widget-height]',
      ),
    )
      .map((element) => {
        const expected = Number(element.getAttribute('data-widget-height'));
        const actual = element.getBoundingClientRect().height;
        return { expected, actual, delta: Math.abs(actual - expected) };
      })
      .filter((entry) => entry.delta > 4);
    const iframeMismatches = Array.from(
      document.querySelectorAll('.widget-frame[data-widget-height]'),
    )
      .flatMap((host) => {
        const expected = Number(host.getAttribute('data-widget-height'));
        return Array.from(host.querySelectorAll('iframe')).map((iframe) => {
          const actual = iframe.getBoundingClientRect().height;
          return { expected, actual, delta: Math.abs(actual - expected) };
        });
      })
      .filter((entry) => entry.delta > 8);
    const flow = Array.from(document.querySelectorAll('.chart-section')).map((element) => ({
      text: (element.textContent || '').trim().slice(0, 40),
      ...rect(element),
    }));
    const largeGaps = [];
    for (let index = 1; index < flow.length; index += 1) {
      const gap = flow[index].top - flow[index - 1].bottom;
      if (gap > 200)
        largeGaps.push({ gap, previous: flow[index - 1].text, next: flow[index].text });
    }
    const section = document.querySelector(detail);
    const heading = section
      ? Array.from(section.querySelectorAll('h4, h5')).find((node) =>
          (node.textContent || '').includes(title),
        )
      : null;
    const tableShell = section?.querySelector('.market-terminal__table-shell');
    if (heading) heading.scrollIntoView({ block: 'start' });
    const shellRect = tableShell ? rect(tableShell) : null;
    return {
      scrollHost:
        scrollHost === document.scrollingElement
          ? 'document'
          : scrollHost.id || scrollHost.className || scrollHost.tagName,
      scrollHeight: scrollHost.scrollHeight,
      clientHeight: scrollHost.clientHeight,
      textIncludesTitle: Boolean(heading),
      tableVisible: Boolean(tableShell && visible(tableShell)),
      tableNearViewport: shellRect ? shellRect.top <= window.innerHeight * 2 : false,
      tableShellOverflowY: tableShell ? getComputedStyle(tableShell).overflowY : '',
      tableShellHasVerticalClip: tableShell
        ? tableShell.scrollHeight > tableShell.clientHeight + 2
        : false,
      embeddedMaxHeight: section ? getComputedStyle(section).maxHeight : '',
      heightMismatches,
      iframeMismatches,
      largeGaps,
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    };
  }, item);
  const failures = [];
  if (
    item.route === '/hedge-board/gold' &&
    result.scrollHeight <= result.clientHeight &&
    !result.textIncludesTitle &&
    !result.tableVisible
  )
    failures.push(`scroll host not expanded ${JSON.stringify(result)}`);
  if (!result.textIncludesTitle) failures.push('missing detail title');
  if (!result.tableVisible) failures.push('detail table is not visible');
  if (!result.tableNearViewport)
    failures.push('detail table is not in current or next viewport after title scroll');
  if (result.embeddedMaxHeight && result.embeddedMaxHeight !== 'none')
    failures.push(`embedded max-height remains ${result.embeddedMaxHeight}`);
  if (result.tableShellHasVerticalClip)
    failures.push(`table has vertical internal clipping ${result.tableShellOverflowY}`);
  if (result.heightMismatches.length)
    failures.push(`host height mismatch ${JSON.stringify(result.heightMismatches)}`);
  if (result.iframeMismatches.length)
    failures.push(`iframe height mismatch ${JSON.stringify(result.iframeMismatches)}`);
  if (result.largeGaps.length) failures.push(`large gaps ${JSON.stringify(result.largeGaps)}`);
  if (result.overflow) failures.push('horizontal overflow');
  if (failures.length) throw new Error(`${mode} ${item.route}: ${failures.join('; ')}`);
  console.log(
    `${mode} ${item.route} chart and detail flow checks passed, scrollHost=${result.scrollHost}, scrollHeight=${result.scrollHeight}`,
  );
}

async function captureGoldFull(page) {
  await page.goto(`${origin}/#/hedge-board/gold`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3500);
  await page.evaluate(() => {
    const candidates = [
      ...Array.from(document.querySelectorAll('*')),
      document.scrollingElement,
    ].filter(Boolean);
    const scrollHost = candidates
      .filter((element) => element.scrollHeight > element.clientHeight + 120)
      .sort((left, right) => right.scrollHeight - left.scrollHeight)[0];
    if (scrollHost && scrollHost !== document.scrollingElement) {
      scrollHost.setAttribute('data-expanded-for-full-screenshot', 'true');
      scrollHost.style.height = 'auto';
      scrollHost.style.maxHeight = 'none';
      scrollHost.style.overflow = 'visible';
      document.documentElement.style.height = 'auto';
      document.body.style.height = 'auto';
    }
  });
  await page.screenshot({ path: path.join(outDir, 'gold-real-full-scroll.png'), fullPage: true });
}

async function run(mode) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 }, locale: 'zh-CN' });
  if (mode === 'blocked') {
    await page.route('**/external-embedding/embed-widget-advanced-chart.js', (route) =>
      route.abort(),
    );
    await page.route('**/embed-widget/advanced-chart/**', (route) => route.abort());
  }
  await login(page);
  for (const item of pages) await checkPage(page, item, mode);
  if (mode === 'normal') await captureGoldFull(page);
  await browser.close();
}

(async () => {
  await run('normal');
  await run('blocked');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
