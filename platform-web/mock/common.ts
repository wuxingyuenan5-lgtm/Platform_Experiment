import { MockMethod } from 'vite-plugin-mock';
import { resultSuccess } from './_util';

export default [
  // Risk records list
  {
    url: '/risk/api/v1/risk-records/',
    method: 'get',
    timeout: 200,
    response: () => {
      return resultSuccess({
        items: [
          { id: 1, title: 'Mock risk record 1', isProcessed: false },
          { id: 2, title: 'Mock risk record 2', isProcessed: false }
        ], total: 2
      });
    },
  },

  // Notifications / messages
  {
    url: '/notifications/api/v1/messages/',
    method: 'get',
    timeout: 200,
    response: () => {
      return resultSuccess({
        items: [
          { id: 1, title: 'Welcome', content: 'Welcome to the mock app', isRead: false }
        ], total: 1
      });
    },
  },

  // Google auth (example)
  {
    url: '/auth_system/api/v1/auth/google-auth/',
    method: 'get',
    timeout: 200,
    response: () => {
      return resultSuccess({ qr: null, msg: 'ok' });
    },
  },

  // support riskApi prefixed variants
  {
    url: '/riskApi/risk/api/v1/risk-records/',
    method: 'get',
    timeout: 200,
    response: () => {
      return resultSuccess({ items: [], total: 0 });
    },
  },
  {
    url: '/riskApi/notifications/api/v1/messages/',
    method: 'get',
    timeout: 200,
    response: () => {
      return resultSuccess({ items: [], total: 0 });
    },
  },
] as MockMethod[];
