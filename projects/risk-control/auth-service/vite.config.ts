import { defineApplicationConfig } from '@vben/vite-config';

export default defineApplicationConfig({
  overrides: {
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
      proxy: {
        '/futureApi': {
          // target: 'http://120.26.254.193:8003/',
          target: 'http://10.1.21.5:8000/',
          // target: 'http://future-test.rta-office.com',
          changeOrigin: true,
          rewrite: (path) => path.replace(new RegExp(`^/futureApi`), ''),
          // only https
          // secure: false
        },
        '/riskApi': {
          // target: 'http://0.0.0.0:8000/',
          target: 'http://10.1.21.2:8005/',
          // target: 'http://risk.rta-office.com/riskApi',
          // target: 'http://risk-test.rta-office.com',
          changeOrigin: true,
          rewrite: (path) => path.replace(new RegExp(`^/riskApi`), ''),
          // only https
          // secure: false
        },
        '/dataApi': {
          // target: 'http://10.1.21.5:8999',
          target: 'http://risk.rta-office.com/dataApi',
          // target: 'http://datacenter.rta-office.com',
          changeOrigin: true,
          rewrite: (path) => path.replace(new RegExp(`^/dataApi`), ''),
          // only https
          // secure: false
        },
        '/monitorApi': {
          target: 'https://monitor.rta.fund',
          changeOrigin: true,
          rewrite: (path) => path.replace(new RegExp(`^/monitorApi`), ''),
        },
        '/login': {
          target: 'http://127.0.0.1:8080',
          changeOrigin: true,
          rewrite: (path) => path,
        },
        '/register': {
          target: 'http://127.0.0.1:8080',
          changeOrigin: true,
          rewrite: (path) => path,
        },
        '/refresh': {
          target: 'http://127.0.0.1:8080',
          changeOrigin: true,
          rewrite: (path) => path,
        },
        '/me': {
          target: 'http://127.0.0.1:8080',
          changeOrigin: true,
          rewrite: (path) => path,
        },
        // Route notifications and risk endpoints to local backend during development
        '/notifications': {
          target: 'http://127.0.0.1:8080',
          changeOrigin: true,
          rewrite: (path) => path,
        },
        '/risk': {
          target: 'http://127.0.0.1:8080',
          changeOrigin: true,
          rewrite: (path) => path,
        },
      },
    },
  },
});
