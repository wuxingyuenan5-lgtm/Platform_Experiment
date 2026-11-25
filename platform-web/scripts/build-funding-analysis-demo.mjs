import { build } from 'vite';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

await build({ configFile: 'vite.funding-demo.config.ts' });
const directory = resolve('../outputs/funding-analysis-demo');
let html = await readFile(resolve(directory, 'funding-analysis-demo.html'), 'utf8');
const script = html.match(/<script[^>]+src="([^"]+)"[^>]*><\/script>/);
const style = html.match(/<link[^>]+href="([^"]+\.css)"[^>]*>/);
if (!script || !style) throw new Error('Expected a single demo entry and stylesheet');
const js = await readFile(resolve(directory, script[1]), 'utf8');
const css = await readFile(resolve(directory, style[1]), 'utf8');
html = html.replace(
  script[0],
  () => `<script type="module">${js.replace(/<\/script/gi, '<\\/script')}</script>`,
);
html = html.replace(style[0], () => `<style>${css}</style>`);
await writeFile(resolve(directory, '资费行情分析-demo.html'), html, 'utf8');
console.log(`Standalone offline demo: ${resolve(directory, '资费行情分析-demo.html')}`);
