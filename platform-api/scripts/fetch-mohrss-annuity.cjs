// Use Chromium's normal page loading for the ministry's JavaScript-served pages.
const { chromium } = require('../../platform-web/node_modules/@playwright/test');

const DIRECTORY = new URL('https://www.mohrss.gov.cn/xxgk2020/fdzdgknr/shbx_4216/shbxjjjg/qynjjd/');
const isOfficial = (url) => new URL(url).origin === DIRECTORY.origin;

async function main() {
  const known = JSON.parse(process.argv[2]);
  const minYear = Number(process.argv[3]);
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  const browser = await chromium.launch(proxy ? { proxy: { server: proxy } } : {});
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    const targets = new Map();
    const errors = [];
    for (const part of ['', 'index_1.html', 'index_2.html']) {
      const url = new URL(part, DIRECTORY).href;
      try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 12000 });
        const links = page.locator('a[href]').filter({ hasText: /全国企业年金基金业务数据摘要|全国职业年金基金市场化投资运营情况/ });
        await links.first().waitFor({ state: 'attached', timeout: 8000 });
        for (const [title, link] of await links.evaluateAll((items) => items.map((a) => [a.textContent.trim(), a.href]))) {
          const year = Number(title.match(/^(20\d{2})年/)?.[1]);
          if (year >= minYear && isOfficial(link)) targets.set(link, title);
        }
      } catch (error) {
        errors.push({ url, error: error.message.split('\n')[0] });
      }
    }
    const checked = new Set();
    for (const [url, title] of targets) {
      const key = title.includes('职业年金') ? 'occupationalPension' : 'pension';
      const current = !checked.has(key);
      checked.add(key);
      if (known.includes(url) && !current) continue;
      try {
        const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 12000 });
        if (!response?.ok() || !isOfficial(page.url())) throw Error('Official article unavailable');
        let source = page.url();
        let body;
        if (key === 'pension') {
          const attachment = page.locator('[href*=".pdf"], [data-recurl*=".pdf"]').first();
          await attachment.waitFor({ state: 'attached', timeout: 8000 });
          const link = await attachment.evaluate((a) => a.getAttribute('data-recurl') || a.getAttribute('href'));
          const pdf = new URL(link, source);
          if (!isOfficial(pdf.href)) throw Error('Unexpected attachment origin');
          const document = await context.request.get(pdf.href, { headers: { referer: source }, timeout: 20000 });
          source = document.url();
          if (!document.ok() || !isOfficial(source)) throw Error('Official PDF unavailable');
          body = await document.body();
          if (body.subarray(0, 5).toString() !== '%PDF-') throw Error('Official response is not a PDF');
        } else {
          await page.getByText('投资运营规模', { exact: false }).last().waitFor({ state: 'attached', timeout: 8000 });
          body = Buffer.from(await page.content());
        }
        console.log(JSON.stringify({ key, url, source, title, body: body.toString('base64') }));
      } catch (error) {
        errors.push({ key, url, error: error.message.split('\n')[0] });
      }
    }
    console.log(JSON.stringify({ discovered: [...checked], errors }));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
