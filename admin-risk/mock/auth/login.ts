import { MockMethod } from 'vite-plugin-mock';
import { resultSuccess, resultError } from '../_util';

const fakeUsers = [
  {
    userId: '1',
    username: 'vben',
    password: '123456',
    token: 'fakeToken1',
    realName: 'Vben Admin',
  },
];

export default [
  // Login
  {
    url: '/auth_system/api/v1/auth/login/',
    timeout: 200,
    method: 'post',
    response: ({ body }) => {
      const { username } = body || {};
      // Accept any credentials in mock and return a token
      const token = 'mockToken';
      return resultSuccess({ token, userId: '1', username: username || 'mock' });
    },
  },

  // Also support requests prefixed with /riskApi/... (when apiUrl has prefix)
  {
    url: '/riskApi/auth_system/api/v1/auth/login/',
    timeout: 200,
    method: 'post',
    response: ({ body }) => {
      const { username } = body || {};
      const token = 'mockToken';
      return resultSuccess({ token, userId: '1', username: username || 'mock' });
    },
  },

  // Get user info
  {
    url: '/auth_system/api/v1/auth/user-info/',
    timeout: 200,
    method: 'post',
    response: () => {
      // return plain user info object (backend-style) so front-end can read roles and data.path
      return {
        roles: [{ roleName: 'admin', value: 'admin' }],
        data: { path: [{ route: '/notification/index', sortOrder: 0 }] },
        userId: '1',
        username: 'mock',
        realName: 'Mock User',
        homePath: '/notification/index',
      };
    },
  },


  {
    url: '/riskApi/auth_system/api/v1/auth/user-info/',
    timeout: 200,
    method: 'post',
    response: () => {
      return {
        roles: [{ roleName: 'admin', value: 'admin' }],
        data: { path: [{ route: '/notification/index', sortOrder: 0 }] },
        userId: '1',
        username: 'mock',
        realName: 'Mock User',
        homePath: '/notification/index',
      };
    },
  },


] as MockMethod[];
