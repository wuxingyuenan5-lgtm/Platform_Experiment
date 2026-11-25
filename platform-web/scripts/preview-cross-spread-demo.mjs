import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { build, preview } from 'vite';
import { createRequire } from 'node:module';

const requireConfig = createRequire(new URL('../internal/vite-config/package.json', import.meta.url));
const vue = requireConfig('@vitejs/plugin-vue');

const root = fileURLToPath(new URL('../', import.meta.url));
const config = {
  configFile: false,
  root,
  plugins: [vue()],
  resolve: { alias: { '@': resolve(root, 'src') } },
  build: {
    outDir: resolve(root, '../.codex/previews/cross-spread-market-demo/site'),
    emptyOutDir: false,
    rollupOptions: { input: resolve(root, 'cross-spread-demo.html') },
  },
  preview: { host: '127.0.0.1', port: 4375, strictPort: true, open: false },
};
await build(config);
await preview(config);
console.log('Cross-spread demo: http://127.0.0.1:4375/cross-spread-demo.html');
