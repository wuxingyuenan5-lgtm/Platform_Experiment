// axios閰嶇疆  鍙嚜琛屾牴鎹」鐩繘琛屾洿鏀癸紝鍙渶鏇存敼璇ユ枃浠跺嵆鍙紝鍏朵粬鏂囦欢鍙互涓嶅姩
// The axios configuration can be changed according to the project, just change the file, other files can be left unchanged

import type { AxiosInstance, AxiosResponse } from 'axios';
import { clone } from 'lodash-es';
import type { RequestOptions, Result } from '#/axios';
import type { AxiosTransform, CreateAxiosOptions } from './axiosTransform';
import { VAxios } from './Axios';
import { checkStatus } from './checkStatus';
import { useGlobSetting } from '@/hooks/setting';
import { useMessage } from '@/hooks/web/useMessage';
import { RequestEnum, ResultEnum, ContentTypeEnum } from '@/enums/httpEnum';
import { isString, isUndefined, isNull, isEmpty } from '@/utils/is';
import { getToken } from '@/utils/auth';
import { setObjToUrlParams, deepMerge } from '@/utils';
import { useErrorLogStoreWithOut } from '@/store/modules/errorLog';
import { useI18n } from '@/hooks/web/useI18n';
import { joinTimestamp, formatRequestDate } from './helper';
import { useUserStoreWithOut } from '@/store/modules/user';
import { AxiosRetry } from '@/utils/http/axios/axiosRetry';
import axios from 'axios';
import { getAppEnvConfig } from '@/utils/env';

const globSetting = useGlobSetting();
const urlPrefix = globSetting.urlPrefix;
const { createMessage, createErrorModal, createSuccessModal } = useMessage();
const appenvConfig = getAppEnvConfig();
/**
 * @description: 鏁版嵁澶勭悊锛屾柟渚垮尯鍒嗗绉嶅鐞嗘柟寮? */
const transform: AxiosTransform = {
  /**
   * @description: 澶勭悊鍝嶅簲鏁版嵁銆傚鏋滄暟鎹笉鏄鏈熸牸寮忥紝鍙洿鎺ユ姏鍑洪敊璇?   */
  transformResponseHook: (res: AxiosResponse<Result>, options: RequestOptions) => {
    const { t } = useI18n();
    const { isTransformResponse, isReturnNativeResponse } = options;
    // Return native Axios response when requested.
    if (isReturnNativeResponse) {
      return res;
    }
    // 涓嶈繘琛屼换浣曞鐞嗭紝鐩存帴杩斿洖
    // Return raw response data when transform is disabled.
    if (!isTransformResponse) {
      return res.data;
    }
    // 閿欒鐨勬椂鍊欒繑鍥?
    const { data } = res;
    if (!data) {
      // return '[HTTP] Request has no return value';
      throw new Error(t('sys.api.apiRequestFailed'));
    }
    //  杩欓噷 code锛宺esult锛宮essage涓?鍚庡彴缁熶竴鐨勫瓧娈碉紝闇€瑕佸湪
    //  types.ts 鍐呬慨鏀逛负椤圭洰鑷繁鐨勬帴鍙ｈ繑鍥炴牸寮?
    const { code, result, message } = data;

    // 杩欓噷閫昏緫鍙互鏍规嵁椤圭洰杩涜淇敼
    const hasSuccess = data && Reflect.has(data, 'code') && code === ResultEnum.SUCCESS;
    if (hasSuccess) {
      let successMsg = message;

      if (isNull(successMsg) || isUndefined(successMsg) || isEmpty(successMsg)) {
        successMsg = t(`sys.api.operationSuccess`);
      }

      if (options.successMessageMode === 'modal') {
        createSuccessModal({ title: t('sys.api.successTip'), content: successMsg });
      } else if (options.successMessageMode === 'message') {
        createMessage.success(successMsg);
      }
      return result;
    }

    // 鍦ㄦ澶勬牴鎹嚜宸遍」鐩殑瀹為檯鎯呭喌瀵逛笉鍚岀殑 code 鎵ц涓嶅悓鐨勬搷浣?
    // 濡傛灉涓嶅笇鏈涗腑鏂綋鍓嶈姹傦紝璇穜eturn 鏁版嵁锛屽惁鍒欑洿鎺ユ姏鍑哄紓甯稿嵆鍙?
    let timeoutMsg = '';
    switch (code) {
      case ResultEnum.TIMEOUT:
        timeoutMsg = t('sys.api.timeoutMessage');
        const userStore = useUserStoreWithOut();
        userStore.logout(true);
        break;
      default:
        if (message) {
          timeoutMsg = message;
        }
    }

    // errorMessageMode='modal'鐨勬椂鍊欎細鏄剧ずmodal閿欒寮圭獥锛岃€屼笉鏄秷鎭彁绀猴紝鐢ㄤ簬涓€浜涙瘮杈冮噸瑕佺殑閿欒
    // errorMessageMode='none' 涓€鑸槸璋冪敤鏃舵槑纭〃绀轰笉甯屾湜鑷姩寮瑰嚭閿欒鎻愮ず
    if (options.errorMessageMode === 'modal') {
      createErrorModal({ title: t('sys.api.errorTip'), content: timeoutMsg });
    } else if (options.errorMessageMode === 'message') {
      createMessage.error(timeoutMsg);
    }

    throw new Error(timeoutMsg || t('sys.api.apiRequestFailed'));
  },

  // 璇锋眰涔嬪墠澶勭悊config
  beforeRequestHook: (config, options) => {
    const { joinPrefix, joinParamsToUrl, formatDate, joinTime = true, requireApiUrl } = options;
    const apiUrl = normalizeApiBase(options.apiUrl);
    const urlPrefix = normalizeApiBase(options.urlPrefix);
    if (requireApiUrl && !apiUrl) {
      throw new Error('Required service URL is not configured');
    }

    if (joinPrefix) {
      config.url = joinApiBase(urlPrefix, config.url);
    }

    if (apiUrl && isString(apiUrl)) {
      config.url = joinApiBase(apiUrl, config.url);
    }
    const params = config.params || {};
    const data = config.data || false;
    formatDate && data && !isString(data) && formatRequestDate(data);
    if (config.method?.toUpperCase() === RequestEnum.GET) {
      if (!isString(params)) {
        // 缁?get 璇锋眰鍔犱笂鏃堕棿鎴冲弬鏁帮紝閬垮厤浠庣紦瀛樹腑鎷挎暟鎹€?        config.params = Object.assign(params || {}, joinTimestamp(joinTime, false));
      } else {
        // 鍏煎restful椋庢牸
        config.url = config.url + params + `${joinTimestamp(joinTime, true)}`;
        config.params = undefined;
      }
    } else {
      if (!isString(params)) {
        formatDate && formatRequestDate(params);
        if (
          Reflect.has(config, 'data') &&
          config.data &&
          (Object.keys(config.data).length > 0 || config.data instanceof FormData)
        ) {
          config.data = data;
          config.params = params;
        } else {
          // 闈濭ET璇锋眰濡傛灉娌℃湁鎻愪緵data锛屽垯灏唒arams瑙嗕负data
          config.data = params;
          config.params = undefined;
        }
        if (joinParamsToUrl) {
          config.url = setObjToUrlParams(
            config.url as string,
            Object.assign({}, config.params, config.data),
          );
        }
      } else {
        // 鍏煎restful椋庢牸
        config.url = config.url + params;
        config.params = undefined;
      }
    }
    return config;
  },

  /**
   * @description: 璇锋眰鎷︽埅鍣ㄥ鐞?   */
  requestInterceptors: (config) => {
    // 璇锋眰涔嬪墠澶勭悊config
    const token = getToken();

    if (token && (config as Recordable)?.requestOptions?.withToken !== false) {
      // jwt token
      (config as Recordable).headers.Authorization = `Bearer ${token}`;
      (config as Recordable).headers.token = token;
    }
    return config;
  },

  /**
   * @description: 鍝嶅簲鎷︽埅鍣ㄥ鐞?   */
  responseInterceptors: (res: AxiosResponse<any>) => {
    return res;
  },

  /**
   * @description: 鍝嶅簲閿欒澶勭悊
   */
  responseInterceptorsCatch: (axiosInstance: AxiosInstance, error: any) => {
    const { t } = useI18n();
    const errorLogStore = useErrorLogStoreWithOut();
    errorLogStore.addAjaxErrorInfo(error);
    const { response, code, message, config } = error || {};
    const errorMessageMode = config?.requestOptions?.errorMessageMode || 'none';
    const msg: string = response?.data?.retMsg ?? '';
    const err: string = error?.toString?.() ?? '';
    let errMessage = '';

    if (axios.isCancel(error)) {
      return Promise.reject(error);
    }

    try {
      if (code === 'ECONNABORTED' && message.indexOf('timeout') !== -1) {
        errMessage = t('sys.api.apiTimeoutMessage');
      }
      if (err?.includes('Network Error')) {
        errMessage = t('sys.api.networkExceptionMsg');
      }

      if (errMessage) {
        if (errorMessageMode === 'modal') {
          createErrorModal({ title: t('sys.api.errorTip'), content: errMessage });
        } else if (errorMessageMode === 'message') {
          createMessage.error(errMessage);
        }
        return Promise.reject(error);
      }
    } catch (error) {
      throw new Error(error as unknown as string);
    }
    checkStatus(error?.response?.status, msg, errorMessageMode);

    // 娣诲姞鑷姩閲嶈瘯鏈哄埗 淇濋櫓璧疯 鍙拡瀵笹ET璇锋眰
    const retryRequest = new AxiosRetry();
    const { isOpenRetry } = config.requestOptions.retryRequest;
    config.method?.toUpperCase() === RequestEnum.GET &&
      isOpenRetry &&
      // @ts-ignore
      retryRequest.retry(axiosInstance, error);
    return Promise.reject(error);
  },
};

function createAxios(opt?: Partial<CreateAxiosOptions>) {
  return new VAxios(
    // 娣卞害鍚堝苟
    deepMerge(
      {
        // See https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication#authentication_schemes
        // authentication schemes锛宔.g: Bearer
        // authenticationScheme: 'Bearer',
        authenticationScheme: '',
        timeout: 15 * 1000,
        // 鍩虹鎺ュ彛鍦板潃
        // baseURL: globSetting.apiUrl,

        headers: { 'Content-Type': ContentTypeEnum.JSON },
        // 濡傛灉鏄痜orm-data鏍煎紡
        // headers: { 'Content-Type': ContentTypeEnum.FORM_URLENCODED },
        // 鏁版嵁澶勭悊鏂瑰紡
        transform: clone(transform),
        // 閰嶇疆椤癸紝涓嬮潰鐨勯€夐」閮藉彲浠ュ湪鐙珛鐨勬帴鍙ｈ姹備腑瑕嗙洊
        requestOptions: {
          // 榛樿灏唒refix 娣诲姞鍒皍rl
          joinPrefix: true,
          // 鏄惁杩斿洖鍘熺敓鍝嶅簲澶?姣斿锛氶渶瑕佽幏鍙栧搷搴斿ご鏃朵娇鐢ㄨ灞炴€?          isReturnNativeResponse: false,
          // 闇€瑕佸杩斿洖鏁版嵁杩涜澶勭悊
          isTransformResponse: true,
          // post璇锋眰鐨勬椂鍊欐坊鍔犲弬鏁板埌url
          joinParamsToUrl: false,
          // 鏍煎紡鍖栨彁浜ゅ弬鏁版椂闂?          formatDate: true,
          // 娑堟伅鎻愮ず绫诲瀷
          errorMessageMode: 'message',
          // 鎺ュ彛鍦板潃
          apiUrl: globSetting.apiUrl,
          // 鎺ュ彛鎷兼帴鍦板潃
          urlPrefix: urlPrefix,
          //  鏄惁鍔犲叆鏃堕棿鎴?          joinTime: true,
          // 蹇界暐閲嶅璇锋眰
          ignoreCancelToken: false,
          // 鏄惁鎼哄甫token
          withToken: true,
          retryRequest: {
            isOpenRetry: true,
            count: 5,
            waitTime: 100,
          },
        },
      },
      opt || {},
    ),
  );
}

export function normalizeApiBase(value: unknown) {
  if (typeof value !== 'string') return '';
  const trimmed = value.trim();
  return trimmed && trimmed !== 'undefined' && trimmed !== 'null' ? trimmed : '';
}

export function joinApiBase(base: string, requestUrl: unknown) {
  const url = isString(requestUrl) ? requestUrl : '';
  if (!base) return url;
  if (!url) return base;
  if (/^[a-z][a-z\d+\-.]*:\/\//i.test(url)) return url;
  if (base === '/') return url.startsWith('/') ? url : `/${url}`;
  return `${base.replace(/\/+$/, '')}/${url.replace(/^\/+/, '')}`;
}

export function resolveApiBase(
  candidates: unknown[],
  label: string,
  options: { required?: boolean } = {},
) {
  for (const candidate of candidates) {
    const normalized = normalizeApiBase(candidate);
    if (normalized) return normalized;
  }
  if (options.required) {
    throw new Error(`${label} is not configured`);
  }
  return '';
}

const defaultApiUrl = resolveApiBase(
  [appenvConfig.VITE_GLOB_API_URL_PLOY, globSetting.apiUrl],
  '骞冲彴涓氬姟 API',
  { required: true },
);
const monitorApiUrl = resolveApiBase(
  [appenvConfig.VITE_GLOB_API_URL_MONITOR, defaultApiUrl],
  '鐩戞帶鏈嶅姟',
);
const futureApiUrl = resolveApiBase(
  [appenvConfig.VITE_GLOB_API_URL_FUTURE, defaultApiUrl],
  '鏈熻揣鏈嶅姟',
);
const dataApiUrl = resolveApiBase(
  [appenvConfig.VITE_GLOB_API_URL_DATA, defaultApiUrl],
  '鏁版嵁鏈嶅姟',
);

export const defHttp = createAxios({
  requestOptions: {
    apiUrl: defaultApiUrl,
    isTransformResponse: false,
  },
});

export const monitorHttp = createAxios({
  requestOptions: {
    apiUrl: monitorApiUrl,
    requireApiUrl: true,
    isTransformResponse: false,
  },
});
// export const monitor2Http = createAxios({
//   requestOptions: {
//     apiUrl: appenvConfig.VITE_GLOB_API_URL_MONITOR2,
//     isTransformResponse: false,
//   },
// });
// export const accHttp = createAxios({
//   requestOptions: {
//     apiUrl: appenvConfig.VITE_GLOB_API_URL_ACC,
//     isTransformResponse: false,
//   },
// });

// export const fmonitorHttp = createAxios({
//   requestOptions: {
//     apiUrl: appenvConfig.VITE_GLOB_API_URL_FMONITOR,
//     isTransformResponse: false,
//   },
// });

// export const mt5Http = createAxios({
//   requestOptions: {
//     apiUrl: appenvConfig.VITE_GLOB_API_URL_MT5,
//     isTransformResponse: false,
//   },
// });

export const futureHttp = createAxios({
  requestOptions: {
    apiUrl: futureApiUrl,
    requireApiUrl: true,
    // apiUrl: '/futureApi',
    isTransformResponse: false,
  },
});

export const dataHttp = createAxios({
  requestOptions: {
    apiUrl: dataApiUrl,
    requireApiUrl: true,
    isTransformResponse: false,
  },
});
