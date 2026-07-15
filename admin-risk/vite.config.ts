import { defineApplicationConfig } from '@vben/vite-config';

const localAuthService = 'http://127.0.0.1:8080';
const localDataService = 'http://127.0.0.1:8082';

export default defineApplicationConfig({
  overrides: {
    build: {
      rollupOptions: {
        maxParallelFileOps: 1,
      },
    },
    optimizeDeps: {
      include: [
        'echarts/core',
        'echarts/charts',
        'echarts/components',
        'echarts/renderers',
        'qrcode',
        '@iconify/iconify',
        'ant-design-vue/es/locale/zh_CN',
        'ant-design-vue/es/locale/en_US',
      ],
    },
    server: {
      port: 4373,
      strictPort: true,
      watch: {
        usePolling: true,
      },
      proxy: {
        // Development and production use the same public API contract.
        '/api/auth': {
          target: localAuthService,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/auth/, ''),
        },
        '/api/data': {
          target: localDataService,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/data/, ''),
        },
        '/external-market/usd': {
          target: 'https://open.er-api.com',
          changeOrigin: true,
          rewrite: () => '/v6/latest/USD',
        },
        '/external-market/okx': {
          target: 'https://www.okx.com',
          changeOrigin: true,
          rewrite: (path) =>
            path.replace(new RegExp(`^/external-market/okx`), '/v3/c2c/tradingOrders/books'),
        },
        '/external-market/barker': {
          target: 'https://app.barker.money',
          changeOrigin: true,
          headers: {
            accept: 'application/json, text/plain, */*',
            origin: 'https://app.barker.money',
            referer: 'https://app.barker.money/campaigns',
            'user-agent': 'Mozilla/5.0',
          },
          rewrite: (path) => path.replace(new RegExp(`^/external-market/barker`), '/api'),
        },
      },
    },
  },
});
