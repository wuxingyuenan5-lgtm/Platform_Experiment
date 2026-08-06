import type { AppRouteRecordRaw, AppRouteModule } from '@/router/types';

import { PAGE_NOT_FOUND_ROUTE, REDIRECT_ROUTE } from '@/router/routes/basic';

import { t } from '@/hooks/web/useI18n';
import { applyBrowserRouteCapabilities } from '@/access/browserRouteCapabilities';
import NotificationRoute from './modules/notification';
// // import { stream } from 'exceljs';

// import.meta.glob() 直接引入所有的模块 Vite 独有的功能
const modules = import.meta.glob('./modules/*.ts', { eager: true });
const routeModuleList: AppRouteModule[] = [];
// load all modules
Object.keys(modules).forEach((key) => {
  const mod = (modules as Recordable)[key].default || {};
  const modList = Array.isArray(mod) ? [...mod] : [mod];
  routeModuleList.push(...modList);
});

export const asyncRoutes = applyBrowserRouteCapabilities([
  PAGE_NOT_FOUND_ROUTE,
  ...routeModuleList,
]);

// 根路由
export const RootRoute: AppRouteRecordRaw = {
  path: '/',
  name: 'Root',
  component: () => import('@/views/landing/index.vue'),
  meta: {
    title: '全球变量金融平台',
    ignoreAuth: true,
  },
};

export const LoginRoute: AppRouteRecordRaw = {
  path: '/login',
  name: 'Login',
  component: () => import('@/views/sys/login/Login.vue'),
  meta: {
    title: t('routes.basic.login'),
  },
};

export const RegisterApplyRoute: AppRouteRecordRaw = {
  path: '/register-apply',
  name: 'RegisterApply',
  component: () => import('@/views/sys/register/index.vue'),
  meta: {
    title: '注册申请',
    ignoreAuth: true,
  },
};

export const ResetPasswordRoute: AppRouteRecordRaw = {
  path: '/reset-password',
  name: 'ResetPassword',
  component: () => import('@/views/sys/reset-password/index.vue'),
  meta: {
    title: '设置新密码',
    ignoreAuth: true,
  },
};

// Basic routing without permission
// 未经许可的基本路由
export const basicRoutes = [
  LoginRoute,
  RegisterApplyRoute,
  ResetPasswordRoute,
  RootRoute,
  NotificationRoute,
  REDIRECT_ROUTE,
  PAGE_NOT_FOUND_ROUTE,
];
