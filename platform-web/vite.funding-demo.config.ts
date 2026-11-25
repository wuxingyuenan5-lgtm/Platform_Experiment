import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { defineConfig } from 'vite';

const localRequire = createRequire(import.meta.url);
const configRequire = createRequire(localRequire.resolve('@vben/vite-config'));
const vue = configRequire('@vitejs/plugin-vue');

// The application's HTML plugin always serves its authenticated SPA entry.
// This standalone entry mounts the same demo component without that app shell.
export default defineConfig({
  plugins: [vue()],
  publicDir: false,
  cacheDir: 'node_modules/.vite-funding-demo',
  optimizeDeps: { entries: ['funding-analysis-demo.html'] },
  base: './',
  server: { host: '127.0.0.1', port: 4477, strictPort: true },
  build: {
    outDir: '../outputs/funding-analysis-demo',
    emptyOutDir: false,
    rollupOptions: { input: resolve(__dirname, 'funding-analysis-demo.html') },
  },
});
