import { defHttp } from '@/utils/http/axios';
import {
  LoginParams,
  LoginResultModel,
  GetUserInfoModel,
  RegisterParams,
  RegistrationRequest,
} from './model/userModel';

import { ErrorMessageMode } from '#/axios';
import { PageEnum } from '@/enums/pageEnum';

const _baseVersion = '/auth_system/api/v1';
const DEV_BYPASS_AUTH =
  import.meta.env.DEV && String(import.meta.env.VITE_DEV_BYPASS_AUTH).toLowerCase() === 'true';
const DEV_BYPASS_TOKEN = 'dev-bypass-token';

enum Api {
  LOGIN_CHANGEEMAIL = _baseVersion + '/auth/change-email/',
  LOGIN_CHANGEPHONE = _baseVersion + '/auth/change-phone/',
  LOGIN_CHANGEPW = _baseVersion + '/auth/change-password/',
  LOGIN_QRCODE = _baseVersion + '/auth/google-auth/',
  Login = '/login',
  Register = '/register',
  Logout = '/logout',
  GetUserInfo = '/me',
  GetPermCode = '/getPermCode',
  RegistrationRequests = '/api/v1/users/registrations',
  TestRetry = '/testRetry',
}
export function postChangeEmail(data) {
  return defHttp.post({ url: Api.LOGIN_CHANGEEMAIL, data });
}
export function postChangePhone(data) {
  return defHttp.post({ url: Api.LOGIN_CHANGEPHONE, data });
}
export function loginChangepw(data) {
  return defHttp.post({ url: Api.LOGIN_CHANGEPW, data });
}
export function loginQrcode() {
  return defHttp.get({ url: Api.LOGIN_QRCODE });
}

export function postLoginQrcode(data) {
  return defHttp.post({ url: Api.LOGIN_QRCODE, data });
}
/**
 * @description: user login api
 */
export function loginApi(params: LoginParams, mode: ErrorMessageMode = 'modal') {
  if (DEV_BYPASS_AUTH) {
    return Promise.resolve({
      userId: params.username || params.name || 'admin',
      token: DEV_BYPASS_TOKEN,
      roles: [],
    } as LoginResultModel);
  }

  return defHttp
    .post<any>(
      {
        url: Api.Login,
        data: params,
      },
      {
        errorMessageMode: mode,
      },
    )
    .then((res) => {
      const data = res as any;
      return {
        userId: data.user_id || data.userId || '',
        token: data.access_token || data.token || '',
        roles: [],
      } as LoginResultModel;
    });
}

export function registerApi(params: RegisterParams) {
  return defHttp.post<any>({ url: Api.Register, data: params }, { errorMessageMode: 'none' });
}

export function getRegistrationRequests(params?: { status?: string }) {
  return defHttp
    .get<any>({ url: Api.RegistrationRequests, params }, { errorMessageMode: 'none' })
    .then((res) => {
      const data = res?.data ?? res?.result ?? res;
      if (Array.isArray(data)) return data as RegistrationRequest[];
      if (Array.isArray(data?.items)) return data.items as RegistrationRequest[];
      return [] as RegistrationRequest[];
    });
}

export function approveRegistration(id: number) {
  return defHttp.post<any>(
    { url: `${Api.RegistrationRequests}/${id}/approve` },
    { errorMessageMode: 'none' },
  );
}

export function rejectRegistration(id: number, reason?: string) {
  return defHttp.post<any>(
    { url: `${Api.RegistrationRequests}/${id}/reject`, data: { reason } },
    { errorMessageMode: 'none' },
  );
}

/**
 * @description: getUserInfo
 */
export async function getUserInfo() {
  if (DEV_BYPASS_AUTH) {
    return {
      roles: [{ roleName: 'admin', value: 'admin' }],
      userId: 'admin',
      username: 'admin',
      realName: 'admin',
      avatar: '',
      desc: 'Local development bypass user',
      role: 'admin',
      name: 'admin',
      homePath: PageEnum.BASE_HOME,
      data: {
        userInfo: {
          username: 'admin',
          role: 'admin',
        },
        path: [
          {
            route: '/home/index',
            sortOrder: 0,
          },
        ],
        product: [],
      },
    } as GetUserInfoModel & Record<string, any>;
  }

  // Route-mapping mode builds menus locally, so login only needs one backend request.
  const me = await defHttp.post<any>({ url: Api.GetUserInfo }, { errorMessageMode: 'none' });
  const data = me as any;
  const role = data.role || '';
  const roles = role ? [{ roleName: role, value: role }] : [];

  return Object.assign(
    {
      roles,
      userId: data.sub || data.userId || '',
      username: data.name || data.username || '',
      realName: data.name || data.username || '',
      avatar: '',
      desc: '',
    },
    data,
  );
}

export function getPermCode() {
  if (DEV_BYPASS_AUTH) {
    return Promise.resolve(['*']);
  }
  return defHttp.get<string[]>({ url: Api.GetPermCode });
}

export function doLogout() {
  if (DEV_BYPASS_AUTH) {
    return Promise.resolve(true);
  }
  return defHttp.get({ url: Api.Logout });
}

export function testRetry() {
  return defHttp.get(
    { url: Api.TestRetry },
    {
      retryRequest: {
        isOpenRetry: true,
        count: 5,
        waitTime: 1000,
      },
    },
  );
}
